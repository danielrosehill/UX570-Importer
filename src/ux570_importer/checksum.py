"""Checksum functionality for UX570 Importer."""

import hashlib
from datetime import datetime
from pathlib import Path


def calculate_sha256(filepath: Path, chunk_size: int = 8192) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        filepath: Path to the file
        chunk_size: Size of chunks to read (default 8KB)

    Returns:
        Hexadecimal hash string
    """
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def write_sidecar(filepath: Path, hash_value: str) -> Path:
    """
    Write a .sha256 sidecar file alongside the original file.

    Args:
        filepath: Path to the original file
        hash_value: SHA256 hash to write

    Returns:
        Path to the sidecar file
    """
    sidecar_path = filepath.with_suffix(filepath.suffix + ".sha256")
    # Format: hash *filename (BSD-style, compatible with sha256sum -c)
    sidecar_path.write_text(f"{hash_value} *{filepath.name}\n")
    return sidecar_path


def append_to_manifest(manifest_path: Path, filepath: Path, hash_value: str) -> None:
    """
    Append a file entry to the manifest file.

    Args:
        manifest_path: Path to the checksums.txt manifest
        filepath: Path to the file that was checksummed
        hash_value: SHA256 hash of the file
    """
    # Get relative path from manifest's parent directory
    try:
        rel_path = filepath.relative_to(manifest_path.parent)
    except ValueError:
        rel_path = filepath

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"{hash_value}  {rel_path}  # imported {timestamp}\n"

    with open(manifest_path, "a") as f:
        f.write(entry)


def verify_checksum(filepath: Path, expected_hash: str) -> bool:
    """
    Verify a file's checksum against an expected value.

    Args:
        filepath: Path to the file to verify
        expected_hash: Expected SHA256 hash

    Returns:
        True if checksum matches, False otherwise
    """
    actual_hash = calculate_sha256(filepath)
    return actual_hash.lower() == expected_hash.lower()


def verify_sidecar(filepath: Path) -> bool | None:
    """
    Verify a file against its sidecar checksum file.

    Args:
        filepath: Path to the file to verify

    Returns:
        True if valid, False if invalid, None if no sidecar exists
    """
    sidecar_path = filepath.with_suffix(filepath.suffix + ".sha256")
    if not sidecar_path.exists():
        return None

    content = sidecar_path.read_text().strip()
    # Parse BSD-style format: hash *filename
    if " *" in content:
        expected_hash = content.split(" *")[0]
    else:
        expected_hash = content.split()[0]

    return verify_checksum(filepath, expected_hash)
