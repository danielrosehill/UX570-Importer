#!/usr/bin/env python3
"""
Sony ICD-UX570 Import Script

Imports recordings from a Sony ICD-UX570 Digital Voice Recorder,
organizing them by month/day.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

import yaml

from ux570_importer import core

CONFIG_FILE = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    """Load configuration from YAML file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt user for yes/no response."""
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = input(prompt + suffix).strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def main():
    parser = argparse.ArgumentParser(
        description="Import recordings from Sony DVR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  dvr-import.py                     # Interactive mode
  dvr-import.py -o ~/recordings     # Specify output directory
  dvr-import.py --move              # Move instead of copy
  dvr-import.py --list              # List available files without importing
  dvr-import.py --checksum          # Generate SHA256 checksums
        """
    )
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--move", action="store_true", help="Move files instead of copying")
    parser.add_argument("--copy", action="store_true", help="Copy files (default)")
    parser.add_argument("--list", action="store_true", help="List files without importing")
    parser.add_argument("--all", action="store_true", help="Import all folders without prompting")
    parser.add_argument("--checksum", action="store_true", help="Generate SHA256 checksums")

    args = parser.parse_args()

    config = load_config()
    source_path = core.get_source_path(config["username"], config["sd_card_name"])

    print(f"Source: {source_path}")

    # Discover folders
    folders = core.discover_folders(source_path)
    if not folders:
        if not source_path.exists():
            print(f"Error: Source path not found: {source_path}")
            print("Is the DVR connected and mounted?")
            sys.exit(1)
        print("No recording folders found.")
        sys.exit(0)

    print(f"Found {len(folders)} folder(s):\n")

    # List mode
    if args.list:
        for folder in folders:
            files = core.discover_files(folder)
            print(f"  {folder.name}/  ({len(files)} files)")
            for f in files:
                parsed = core.parse_filename(f.name)
                if parsed:
                    month, day = parsed
                    print(f"    {f.name}  -> {core.MONTHS[month]}/{day}/")
                else:
                    print(f"    {f.name}  (unparseable)")
        sys.exit(0)

    # Determine output directory
    if args.output:
        output_dir = Path(args.output).expanduser()
    else:
        default = Path(config.get("default_output_dir", "~/DVR-Recordings")).expanduser()
        response = input(f"Output directory [{default}]: ").strip()
        output_dir = Path(response).expanduser() if response else default

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {output_dir}\n")

    # Determine mode
    if args.move:
        mode = "move"
    elif args.copy:
        mode = "copy"
    else:
        default_mode = config.get("default_mode", "copy")
        if default_mode == "move":
            mode = "move" if prompt_yes_no("Move files (delete from DVR)?", default=True) else "copy"
        else:
            mode = "move" if prompt_yes_no("Move files (delete from DVR)?", default=False) else "copy"

    print(f"Mode: {mode}")
    if args.checksum:
        print("Checksums: enabled")
    print()

    # Process each folder
    total_imported = 0
    for folder in folders:
        files = core.discover_files(folder)
        if not files:
            continue

        print(f"{folder.name}/ ({len(files)} files)")

        if not args.all:
            if not prompt_yes_no(f"  Import this folder?"):
                print("  Skipped.\n")
                continue

        for f in files:
            success, message = core.import_file(f, output_dir, mode, args.checksum)
            print(f"  {message}")
            if success:
                total_imported += 1
        print()

    print(f"Done. Imported {total_imported} file(s) to {output_dir}")


if __name__ == "__main__":
    main()
