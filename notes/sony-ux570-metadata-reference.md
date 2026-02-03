# Sony ICD-UX570F DVR Metadata Reference

This document describes all metadata fields embedded in MP3 files recorded by the Sony ICD-UX570F digital voice recorder.

## ID3v2 Tags

The Sony UX570 writes ID3v2 tags with the following fields:

### Standard ID3v2 Frames

| Frame | Name | Description | Example Value |
|-------|------|-------------|---------------|
| `TIT2` | Title | Filename-derived timestamp in `YYMMDD_HHMM` format | `260203_1536` |
| `TPE1` | Artist | Default recording label set on device | `My Recording` |
| `TENC` | Encoded By | Device model and firmware version | `SONY IC RECORDER 11.4.0` |

### GEOB Frame (IcdRInfo)

The Sony DVR embeds a proprietary binary blob in a **GEOB** (General Encapsulated Object) frame with the description `IcdRInfo`. This 108-byte structure contains device-specific metadata.

#### GEOB Frame Properties

| Property | Value |
|----------|-------|
| Description | `IcdRInfo` |
| MIME Type | (empty) |
| Filename | (empty) |
| Data Length | 108 bytes |

#### IcdRInfo Binary Structure

```
Offset  Length  Field                    Example Value
------  ------  ----------------------   -------------
0x00    4       Header/length marker     00 00 00 6c (108 bytes)
0x04    2       Unknown prefix           69 49 ("iI")
0x06    12      Device Model (null-padded) "CD-UX570F"
0x12    6       Padding/unknown          00 00 00 00 00 00
0x18    6       Version/config bytes     01 02 01 0b 09 01
0x1E    18      Reserved/padding         00 bytes
0x30    4       Unknown flags            01 06 00 00
0x34    4       Unknown flags            00 00 01 00
0x38    13      Reserved/padding         00 bytes
0x45    3       Unknown flags            02 01 ff
0x48    1       Unknown                  c3
0x49    7       Reserved                 00 bytes
0x50    19      ISO 8601 Timestamp       "2026-02-03T15:36:10"
0x63    9       Trailing data            00 bytes + 01 00
```

#### Key Extracted Fields

| Field | Offset | Format | Description |
|-------|--------|--------|-------------|
| Device Model | 0x06 | ASCII, null-padded | Full model identifier (ICD-UX570F) |
| Recording Timestamp | 0x50 | ISO 8601 | Full date/time: `YYYY-MM-DDTHH:MM:SS` |

### Timestamp Formats

The DVR records the timestamp in two places:

1. **TIT2 (Title)**: Condensed format `YYMMDD_HHMM` (e.g., `260203_1536`)
   - YY = Year (26 = 2026)
   - MM = Month (02 = February)
   - DD = Day (03)
   - HHMM = Time in 24h format (1536 = 15:36)

2. **GEOB IcdRInfo**: Full ISO 8601 format `YYYY-MM-DDTHH:MM:SS` (e.g., `2026-02-03T15:36:10`)
   - Includes seconds precision
   - Local timezone (no offset specified)

## Audio Stream Properties

| Property | Typical Value |
|----------|---------------|
| Codec | MP3 (MPEG audio layer 3) |
| Sample Rate | 44100 Hz |
| Channels | 2 (Stereo) |
| Bitrate | 192 kbps |
| Bit Depth | Floating point (fltp) |

## Parsing the GEOB IcdRInfo

Python example using mutagen:

```python
from mutagen.mp3 import MP3
import re

def extract_sony_metadata(filepath):
    audio = MP3(filepath)
    metadata = {
        'title': str(audio.tags.get('TIT2', '')),
        'artist': str(audio.tags.get('TPE1', '')),
        'encoder': str(audio.tags.get('TENC', '')),
        'duration': audio.info.length,
        'bitrate': audio.info.bitrate,
        'sample_rate': audio.info.sample_rate,
    }

    # Extract GEOB IcdRInfo
    for key, value in audio.tags.items():
        if 'GEOB' in key and value.desc == 'IcdRInfo':
            data = value.data
            # Device model at offset 0x06 (12 bytes, null-padded)
            model_bytes = data[6:18]
            metadata['device_model'] = model_bytes.decode('ascii').rstrip('\x00')

            # Full timestamp at offset 0x50 (19 bytes)
            timestamp_bytes = data[0x50:0x50+19]
            metadata['recording_timestamp'] = timestamp_bytes.decode('ascii')

    return metadata
```

## Notes

- The `IcdRInfo` structure appears to be consistent across Sony IC Recorder models
- The firmware version in `TENC` (11.4.0) may affect the exact binary layout
- The device stores recordings with local time (no timezone info in the ISO timestamp)
- Unknown bytes in the GEOB structure may contain:
  - Recording settings (mic sensitivity, scene mode)
  - File sequence numbers
  - Battery/device state at recording time
