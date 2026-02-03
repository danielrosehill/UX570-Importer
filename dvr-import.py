#!/usr/bin/env python3
"""
Sony ICD-UX570 Import Script

Imports recordings from a Sony ICD-UX570 Digital Voice Recorder,
organizing them by month/day.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

import yaml

CONFIG_FILE = Path(__file__).parent / "config.yaml"

MONTHS = {
    "01": "01-January",
    "02": "02-February",
    "03": "03-March",
    "04": "04-April",
    "05": "05-May",
    "06": "06-June",
    "07": "07-July",
    "08": "08-August",
    "09": "09-September",
    "10": "10-October",
    "11": "11-November",
    "12": "12-December",
}

EXCLUDED_FOLDERS = {"RADIO01"}


def load_config() -> dict:
    """Load configuration from YAML file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def get_source_path(config: dict) -> Path:
    """Build the source path from config."""
    return Path(f"/media/{config['username']}/{config['sd_card_name']}/PRIVATE/SONY/REC_FILE")


def parse_filename(filename: str) -> tuple[str, str] | None:
    """
    Parse Sony DVR filename format: YYMMDD_HHMM.mp3
    Returns (month, day) or None if parsing fails.
    """
    stem = Path(filename).stem
    if len(stem) < 6 or "_" not in stem:
        return None

    try:
        date_part = stem.split("_")[0]
        if len(date_part) != 6:
            return None

        # YYMMDD format
        month = date_part[2:4]
        day = date_part[4:6]

        if month not in MONTHS:
            return None
        if not (1 <= int(day) <= 31):
            return None

        return month, day
    except (ValueError, IndexError):
        return None


def discover_folders(source_path: Path) -> list[Path]:
    """Find all recording folders, excluding RADIO01."""
    if not source_path.exists():
        print(f"Error: Source path not found: {source_path}")
        print("Is the DVR connected and mounted?")
        sys.exit(1)

    folders = []
    for item in sorted(source_path.iterdir()):
        if item.is_dir() and item.name not in EXCLUDED_FOLDERS:
            folders.append(item)

    return folders


def discover_files(folder: Path) -> list[Path]:
    """Find all audio files in a folder."""
    extensions = {".mp3", ".wav", ".m4a", ".wma"}
    files = []
    for item in sorted(folder.iterdir()):
        if item.is_file() and item.suffix.lower() in extensions:
            files.append(item)
    return files


def import_file(src: Path, dest_base: Path, mode: str) -> bool:
    """Import a single file to the organized destination."""
    parsed = parse_filename(src.name)
    if not parsed:
        print(f"  Warning: Could not parse date from {src.name}, skipping")
        return False

    month, day = parsed
    month_folder = MONTHS[month]

    dest_dir = dest_base / month_folder / day
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / src.name

    if dest_file.exists():
        print(f"  Skipping (exists): {src.name}")
        return False

    if mode == "move":
        shutil.move(src, dest_file)
        print(f"  Moved: {src.name} -> {dest_dir.relative_to(dest_base)}/")
    else:
        shutil.copy2(src, dest_file)
        print(f"  Copied: {src.name} -> {dest_dir.relative_to(dest_base)}/")

    return True


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
        """
    )
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--move", action="store_true", help="Move files instead of copying")
    parser.add_argument("--copy", action="store_true", help="Copy files (default)")
    parser.add_argument("--list", action="store_true", help="List files without importing")
    parser.add_argument("--all", action="store_true", help="Import all folders without prompting")

    args = parser.parse_args()

    config = load_config()
    source_path = get_source_path(config)

    print(f"Source: {source_path}")

    # Discover folders
    folders = discover_folders(source_path)
    if not folders:
        print("No recording folders found.")
        sys.exit(0)

    print(f"Found {len(folders)} folder(s):\n")

    # List mode
    if args.list:
        for folder in folders:
            files = discover_files(folder)
            print(f"  {folder.name}/  ({len(files)} files)")
            for f in files:
                parsed = parse_filename(f.name)
                if parsed:
                    month, day = parsed
                    print(f"    {f.name}  -> {MONTHS[month]}/{day}/")
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

    print(f"Mode: {mode}\n")

    # Process each folder
    total_imported = 0
    for folder in folders:
        files = discover_files(folder)
        if not files:
            continue

        print(f"{folder.name}/ ({len(files)} files)")

        if not args.all:
            if not prompt_yes_no(f"  Import this folder?"):
                print("  Skipped.\n")
                continue

        for f in files:
            if import_file(f, output_dir, mode):
                total_imported += 1
        print()

    print(f"Done. Imported {total_imported} file(s) to {output_dir}")


if __name__ == "__main__":
    main()
