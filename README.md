# UX570 Importer

Import tool for Sony ICD-UX570 Digital Voice Recorder recordings.

## Features

- Configurable source path (username, SD card mount name)
- Scans recording folders, excluding RADIO01
- Copy or move files
- Organizes recordings by month/day based on filename timestamps
- Interactive folder selection

## Setup

```bash
# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install pyyaml
```

## Configuration

Edit `config.yaml`:

```yaml
username: daniel
sd_card_name: DVR_SD
default_output_dir: ~/DVR-Recordings
default_mode: copy
```

## Usage

```bash
# List available files
./dvr-import.py --list

# Interactive import
./dvr-import.py

# Specify output directory
./dvr-import.py -o ~/my-recordings

# Move files instead of copying
./dvr-import.py --move

# Import all folders without prompting
./dvr-import.py --all
```

## File Organization

Files are organized by month and day based on the filename timestamp:

```
Input:  260203_1536.mp3  (2026-02-03 at 15:36)
Output: 02-February/03/260203_1536.mp3
```

## Device Info

- **Model**: Sony ICD-UX570
- **Vendor ID**: `054c`
- **Product ID**: `0cf7`

See `notes/device-info.md` for udev rules and mount configuration.
