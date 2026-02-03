"""Utility functions for UX570 Importer."""

import getpass
import os
from pathlib import Path

import yaml

DEFAULT_CONFIG = {
    "username": "",
    "sd_card_name": "DVR_SD",
    "default_output_dir": "~/DVR-Recordings",
    "default_mode": "move",
    "gui": {
        "checksum_enabled": True,
        "window_geometry": None,
        "last_output_dir": None,
        "first_run_completed": False,
    },
}


def detect_username() -> str:
    """Detect the current Linux username."""
    try:
        return os.getlogin()
    except OSError:
        return getpass.getuser()


def detect_sd_cards(username: str | None = None) -> list[dict]:
    """
    Scan /media/{username}/ for mounted volumes.

    Returns:
        List of dicts with 'name' and 'path' keys
    """
    if username is None:
        username = detect_username()

    media_path = Path(f"/media/{username}")
    if not media_path.exists():
        return []

    cards = []
    for item in sorted(media_path.iterdir()):
        if item.is_dir():
            cards.append({
                "name": item.name,
                "path": str(item),
                "is_dvr": is_sony_dvr(item),
            })

    return cards


def is_sony_dvr(mount_path: Path) -> bool:
    """
    Check if a mounted volume is a Sony DVR.

    Looks for the characteristic folder structure:
    PRIVATE/SONY/REC_FILE
    """
    rec_file_path = mount_path / "PRIVATE" / "SONY" / "REC_FILE"
    return rec_file_path.exists() and rec_file_path.is_dir()


def detect_sony_dvr(username: str | None = None) -> dict | None:
    """
    Look for a mounted Sony DVR.

    Returns:
        Dict with SD card info if found, None otherwise
    """
    cards = detect_sd_cards(username)
    for card in cards:
        if card.get("is_dvr"):
            return card
    return None


def get_config_path() -> Path:
    """Get the path to the config file."""
    # Check user config first (for user customizations)
    user_config = Path.home() / ".config" / "ux570-importer" / "config.yaml"
    if user_config.exists():
        return user_config

    # Check system config
    system_config = Path("/etc/ux570-importer/config.yaml")
    if system_config.exists():
        return system_config

    # Check for config in the package directory (development mode)
    pkg_config = Path(__file__).parent.parent.parent.parent / "config.yaml"
    if pkg_config.exists():
        return pkg_config

    # Fall back to user config directory (will be created when saving)
    return user_config


def load_settings(config_path: Path | None = None) -> dict:
    """
    Load settings from config file.

    Returns merged settings with defaults for any missing values.
    """
    if config_path is None:
        config_path = get_config_path()

    settings = DEFAULT_CONFIG.copy()
    settings["gui"] = DEFAULT_CONFIG["gui"].copy()

    if config_path.exists():
        with open(config_path) as f:
            loaded = yaml.safe_load(f) or {}

        # Merge top-level settings
        for key in ["username", "sd_card_name", "default_output_dir", "default_mode"]:
            if key in loaded:
                settings[key] = loaded[key]

        # Merge GUI settings
        if "gui" in loaded and isinstance(loaded["gui"], dict):
            for key, value in loaded["gui"].items():
                settings["gui"][key] = value

    # Auto-detect username if not set
    if not settings["username"]:
        settings["username"] = detect_username()

    return settings


def save_settings(settings: dict, config_path: Path | None = None) -> None:
    """Save settings to config file."""
    if config_path is None:
        config_path = get_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with nice formatting
    content = f"""# DVR Import Configuration
username: {settings.get('username', '')}
sd_card_name: {settings.get('sd_card_name', 'DVR_SD')}

# Default output directory (can be overridden at runtime)
default_output_dir: {settings.get('default_output_dir', '~/DVR-Recordings')}

# Operation mode: "copy" or "move"
default_mode: {settings.get('default_mode', 'copy')}

# GUI settings
gui:
  checksum_enabled: {str(settings.get('gui', {}).get('checksum_enabled', True)).lower()}
  first_run_completed: {str(settings.get('gui', {}).get('first_run_completed', False)).lower()}
"""

    # Add optional GUI settings if present
    gui = settings.get("gui", {})
    if gui.get("window_geometry"):
        content += f"  window_geometry: {gui['window_geometry']}\n"
    if gui.get("last_output_dir"):
        content += f"  last_output_dir: {gui['last_output_dir']}\n"

    config_path.write_text(content)


def expand_path(path: str | Path) -> Path:
    """Expand ~ and environment variables in a path."""
    return Path(os.path.expandvars(os.path.expanduser(str(path))))


def get_file_size_str(size_bytes: int) -> str:
    """Convert file size in bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
