# Sony ICD-UX570 Device Information

## USB Identification

| Property | Value |
|----------|-------|
| Device | Sony ICD-UX570 Digital Voice Recorder |
| Vendor ID | `054c` (Sony) |
| Product ID | `0cf7` |
| USB Model String | IC RECORDER |

## Storage Units

The device exposes two SCSI LUNs:

| LUN | Purpose | ID_INSTANCE | Default Mount | udev Symlink |
|-----|---------|-------------|---------------|--------------|
| 0 | Internal Storage | `0:0` | `/media/daniel/IC RECORDER` | `/dev/sony-dvr-internal` |
| 1 | SD Card Slot | `0:1` | `/media/daniel/DVR_SD` | `/dev/sony-dvr-sd` |

## Folder Structure

Recordings path: `PRIVATE/SONY/REC_FILE/FOLDER01/`

Full path when mounted: `/media/daniel/DVR_SD/PRIVATE/SONY/REC_FILE/FOLDER01/`

## udev Rule

Located at: `/etc/udev/rules.d/99-sony-dvr.rules`

```bash
# Sony IC Recorder (UX570 / similar models)
# Vendor ID: 054c, Product ID: 0cf7

# SD Card slot (SCSI LUN 1) - set friendly name for udisks2 automount
SUBSYSTEM=="block", ENV{ID_USB_VENDOR_ID}=="054c", ENV{ID_USB_MODEL_ID}=="0cf7", ENV{ID_INSTANCE}=="0:1", ENV{UDISKS_NAME}="DVR_SD"

# Create symlinks for easy access
SUBSYSTEM=="block", ENV{ID_USB_VENDOR_ID}=="054c", ENV{ID_USB_MODEL_ID}=="0cf7", ENV{ID_INSTANCE}=="0:1", SYMLINK+="sony-dvr-sd"
SUBSYSTEM=="block", ENV{ID_USB_VENDOR_ID}=="054c", ENV{ID_USB_MODEL_ID}=="0cf7", ENV{ID_INSTANCE}=="0:0", SYMLINK+="sony-dvr-internal"
```

## Filesystem Label

The SD card's FAT filesystem label was set to `DVR_SD` using:
```bash
sudo fatlabel /dev/sdg1 DVR_SD
```
This ensures the mount point uses a friendly name instead of the volume serial.

## Usage

After plugging in the device:
- SD card will mount to `/media/daniel/DVR_SD`
- Access recordings at `/media/daniel/DVR_SD/PRIVATE/SONY/REC_FILE/FOLDER01/`
- Symlink available at `/dev/sony-dvr-sd` (and `/dev/sony-dvr-sd1` for partition)
