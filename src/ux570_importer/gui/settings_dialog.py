"""Settings dialog for UX570 Importer GUI."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from .. import utils


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.settings["gui"] = settings.get("gui", {}).copy()

        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)

        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Device settings
        device_group = QGroupBox("Device Settings")
        device_layout = QFormLayout(device_group)

        # Username
        username_layout = QHBoxLayout()
        self.username_edit = QLineEdit()
        username_layout.addWidget(self.username_edit)

        detect_user_btn = QPushButton("Detect")
        detect_user_btn.clicked.connect(self._detect_username)
        username_layout.addWidget(detect_user_btn)

        device_layout.addRow("Username:", username_layout)

        # SD card name
        sd_layout = QHBoxLayout()
        self.sd_card_combo = QComboBox()
        self.sd_card_combo.setEditable(True)
        sd_layout.addWidget(self.sd_card_combo)

        scan_btn = QPushButton("Scan")
        scan_btn.clicked.connect(self._scan_sd_cards)
        sd_layout.addWidget(scan_btn)

        device_layout.addRow("SD Card Name:", sd_layout)

        layout.addWidget(device_group)

        # Output settings
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout(output_group)

        # Default output directory
        output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        output_dir_layout.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        output_dir_layout.addWidget(browse_btn)

        output_layout.addRow("Default Output:", output_dir_layout)

        # Default mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Copy", "copy")
        self.mode_combo.addItem("Move", "move")
        output_layout.addRow("Default Mode:", self.mode_combo)

        layout.addWidget(output_group)

        # GUI settings
        gui_group = QGroupBox("Import Options")
        gui_layout = QFormLayout(gui_group)

        self.checksum_check = QCheckBox("Enable SHA256 checksums by default")
        gui_layout.addRow(self.checksum_check)

        layout.addWidget(gui_group)

        # Info label
        info_label = QLabel(
            "<i>Settings are saved to config.yaml in the application directory.</i>"
        )
        layout.addWidget(info_label)

        layout.addStretch()

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _load_settings(self):
        """Load current settings into UI."""
        self.username_edit.setText(self.settings.get("username", ""))
        self.sd_card_combo.setCurrentText(self.settings.get("sd_card_name", "DVR_SD"))
        self.output_dir_edit.setText(
            self.settings.get("default_output_dir", "~/DVR-Recordings")
        )

        mode = self.settings.get("default_mode", "copy")
        index = self.mode_combo.findData(mode)
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)

        gui = self.settings.get("gui", {})
        self.checksum_check.setChecked(gui.get("checksum_enabled", True))

        # Scan for SD cards
        self._scan_sd_cards()

    def _detect_username(self):
        """Auto-detect the current username."""
        self.username_edit.setText(utils.detect_username())

    def _scan_sd_cards(self):
        """Scan for mounted SD cards."""
        username = self.username_edit.text() or utils.detect_username()
        current = self.sd_card_combo.currentText()

        self.sd_card_combo.clear()

        cards = utils.detect_sd_cards(username)
        for card in cards:
            label = card["name"]
            if card.get("is_dvr"):
                label += " (Sony DVR detected)"
            self.sd_card_combo.addItem(label, card["name"])

        # Restore previous selection or set to detected DVR
        if current:
            # Try to find the previous selection
            for i in range(self.sd_card_combo.count()):
                if self.sd_card_combo.itemData(i) == current:
                    self.sd_card_combo.setCurrentIndex(i)
                    return
            self.sd_card_combo.setCurrentText(current)
        else:
            # Select DVR if found
            for card in cards:
                if card.get("is_dvr"):
                    for i in range(self.sd_card_combo.count()):
                        if self.sd_card_combo.itemData(i) == card["name"]:
                            self.sd_card_combo.setCurrentIndex(i)
                            return

    def _browse_output(self):
        """Open folder browser for default output directory."""
        current = str(utils.expand_path(self.output_dir_edit.text()))
        folder = QFileDialog.getExistingDirectory(
            self, "Select Default Output Folder", current
        )
        if folder:
            self.output_dir_edit.setText(folder)

    def get_settings(self) -> dict:
        """Get the updated settings."""
        # Get SD card name from combo (data if available, otherwise text)
        sd_card_name = self.sd_card_combo.currentData()
        if not sd_card_name:
            sd_card_name = self.sd_card_combo.currentText()
            # Strip any suffix like " (Sony DVR detected)"
            if " (" in sd_card_name:
                sd_card_name = sd_card_name.split(" (")[0]

        self.settings["username"] = self.username_edit.text()
        self.settings["sd_card_name"] = sd_card_name
        self.settings["default_output_dir"] = self.output_dir_edit.text()
        self.settings["default_mode"] = self.mode_combo.currentData()

        if "gui" not in self.settings:
            self.settings["gui"] = {}
        self.settings["gui"]["checksum_enabled"] = self.checksum_check.isChecked()

        return self.settings
