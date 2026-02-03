"""Core import logic for UX570 Importer."""

import shutil
from pathlib import Path
from typing import Callable

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
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".wma"}


def get_source_path(username: str, sd_card_name: str) -> Path:
    """Build the source path from username and SD card name."""
    return Path(f"/media/{username}/{sd_card_name}/PRIVATE/SONY/REC_FILE")


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


def get_full_date_from_filename(filename: str) -> str | None:
    """
    Extract full date string from Sony DVR filename format: YYMMDD_HHMM.mp3
    Returns "20YY-MM-DD HH:MM" or None if parsing fails.
    """
    stem = Path(filename).stem
    if len(stem) < 11 or "_" not in stem:
        return None

    try:
        parts = stem.split("_")
        if len(parts) < 2:
            return None

        date_part = parts[0]
        time_part = parts[1][:4]  # Take first 4 chars for HHMM

        if len(date_part) != 6 or len(time_part) != 4:
            return None

        year = f"20{date_part[:2]}"
        month = date_part[2:4]
        day = date_part[4:6]
        hour = time_part[:2]
        minute = time_part[2:4]

        return f"{year}-{month}-{day} {hour}:{minute}"
    except (ValueError, IndexError):
        return None


def discover_folders(source_path: Path) -> list[Path]:
    """Find all recording folders, excluding RADIO01."""
    if not source_path.exists():
        return []

    folders = []
    for item in sorted(source_path.iterdir()):
        if item.is_dir() and item.name not in EXCLUDED_FOLDERS:
            folders.append(item)

    return folders


def discover_files(folder: Path) -> list[Path]:
    """Find all audio files in a folder."""
    files = []
    for item in sorted(folder.iterdir()):
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
            files.append(item)
    return files


def discover_all_files(source_path: Path) -> list[Path]:
    """Find all audio files across all folders."""
    all_files = []
    for folder in discover_folders(source_path):
        all_files.extend(discover_files(folder))
    return all_files


def get_dest_path(filename: str, dest_base: Path) -> Path | None:
    """Calculate destination path for a file based on its date."""
    parsed = parse_filename(filename)
    if not parsed:
        return None

    month, day = parsed
    month_folder = MONTHS[month]
    return dest_base / month_folder / day / filename


def import_file(
    src: Path,
    dest_base: Path,
    mode: str = "copy",
    checksum_enabled: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[bool, str]:
    """
    Import a single file to the organized destination.

    Args:
        src: Source file path
        dest_base: Base destination directory
        mode: "copy" or "move"
        checksum_enabled: Whether to generate SHA256 checksums
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (success, message)
    """
    from . import checksum as checksum_module

    parsed = parse_filename(src.name)
    if not parsed:
        return False, f"Could not parse date from {src.name}"

    month, day = parsed
    month_folder = MONTHS[month]

    dest_dir = dest_base / month_folder / day
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / src.name

    if dest_file.exists():
        return False, f"File already exists: {src.name}"

    try:
        if mode == "move":
            shutil.move(src, dest_file)
            action = "Moved"
        else:
            shutil.copy2(src, dest_file)
            action = "Copied"

        message = f"{action}: {src.name} -> {month_folder}/{day}/"

        if checksum_enabled:
            hash_value = checksum_module.calculate_sha256(dest_file)
            checksum_module.write_sidecar(dest_file, hash_value)
            checksum_module.append_to_manifest(dest_base / "checksums.txt", dest_file, hash_value)
            message += " [checksum generated]"

        if progress_callback:
            progress_callback(message)

        return True, message

    except OSError as e:
        return False, f"Error importing {src.name}: {e}"


def import_files(
    files: list[Path],
    dest_base: Path,
    mode: str = "copy",
    checksum_enabled: bool = False,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[int, int, list[str]]:
    """
    Import multiple files.

    Args:
        files: List of source file paths
        dest_base: Base destination directory
        mode: "copy" or "move"
        checksum_enabled: Whether to generate SHA256 checksums
        progress_callback: Optional callback (current, total, message)

    Returns:
        Tuple of (success_count, skip_count, error_messages)
    """
    success_count = 0
    skip_count = 0
    errors = []

    for i, f in enumerate(files):
        success, message = import_file(f, dest_base, mode, checksum_enabled)

        if success:
            success_count += 1
        else:
            skip_count += 1
            if "already exists" not in message:
                errors.append(message)

        if progress_callback:
            progress_callback(i + 1, len(files), message)

    return success_count, skip_count, errors
