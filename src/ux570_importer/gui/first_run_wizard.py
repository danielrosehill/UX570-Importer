"""First-run setup wizard for UX570 Importer GUI."""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWizard,
    QWizardPage,
)

from .. import utils


class WelcomePage(QWizardPage):
    """Welcome page of the wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Welcome to UX570 Importer")
        self.setSubTitle(
            "This wizard will help you set up the application for importing "
            "recordings from your Sony ICD-UX570 Digital Voice Recorder."
        )

        layout = QVBoxLayout(self)

        info = QLabel(
            "The wizard will:\n\n"
            "1. Detect your username\n"
            "2. Find your mounted SD card\n"
            "3. Set up your default output folder\n\n"
            "Click Next to begin."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()


class UsernamePage(QWizardPage):
    """Username detection page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Username Detection")
        self.setSubTitle(
            "Your Linux username is used to find mounted devices in /media/username/"
        )

        layout = QVBoxLayout(self)

        # Detected username
        self.detected_username = utils.detect_username()

        info = QLabel(f"Detected username: <b>{self.detected_username}</b>")
        layout.addWidget(info)

        layout.addSpacing(20)

        # Username input
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Username:"))

        self.username_edit = QLineEdit()
        self.username_edit.textChanged.connect(self.completeChanged)
        input_layout.addWidget(self.username_edit)

        layout.addLayout(input_layout)

        note = QLabel(
            "<i>If the detected username is incorrect, you can edit it above.</i>"
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()

    def initializePage(self):
        """Initialize the page with detected username."""
        self.username_edit.setText(self.detected_username)

    def isComplete(self) -> bool:
        """Check if the page is complete."""
        return bool(self.username_edit.text().strip())

    def get_username(self) -> str:
        """Get the entered username."""
        return self.username_edit.text().strip()


class SDCardPage(QWizardPage):
    """SD card detection page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("SD Card Detection")
        self.setSubTitle(
            "Select the SD card that contains your Sony DVR recordings."
        )

        layout = QVBoxLayout(self)

        # SD card combo
        self.sd_combo = QComboBox()
        self.sd_combo.setMinimumWidth(300)
        layout.addWidget(self.sd_combo)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Scan button
        scan_btn = QPushButton("Rescan")
        scan_btn.clicked.connect(self._scan_devices)
        layout.addWidget(scan_btn)

        # Manual entry
        layout.addSpacing(20)
        manual_label = QLabel("Or enter SD card name manually:")
        layout.addWidget(manual_label)

        self.manual_edit = QLineEdit()
        self.manual_edit.setPlaceholderText("e.g., DVR_SD")
        layout.addWidget(self.manual_edit)

        layout.addStretch()

    def initializePage(self):
        """Called when the page is shown."""
        self._scan_devices()

    def _scan_devices(self):
        """Scan for mounted SD cards."""
        wizard = self.wizard()
        username = wizard.username_page.get_username() if wizard else utils.detect_username()
        self.sd_combo.clear()

        cards = utils.detect_sd_cards(username)

        if not cards:
            self.status_label.setText(
                "No mounted devices found in /media/{}/\n\n"
                "Make sure your SD card is inserted and mounted.".format(username)
            )
            return

        dvr_found = False
        for card in cards:
            label = card["name"]
            if card.get("is_dvr"):
                label += " [Sony DVR detected]"
                dvr_found = True
            self.sd_combo.addItem(label, card["name"])

        if dvr_found:
            self.status_label.setText(
                "Sony DVR detected! The correct SD card has been selected."
            )
            # Select the DVR
            for i in range(self.sd_combo.count()):
                if "[Sony DVR detected]" in self.sd_combo.itemText(i):
                    self.sd_combo.setCurrentIndex(i)
                    break
        else:
            self.status_label.setText(
                "No Sony DVR folder structure detected.\n"
                "Please select the correct SD card or enter the name manually."
            )

    def validatePage(self):
        """Validate that an SD card is selected or entered."""
        # Check manual entry first
        if self.manual_edit.text().strip():
            return True

        # Check combo selection
        return self.sd_combo.currentData() is not None

    def get_sd_card_name(self) -> str:
        """Get the selected SD card name."""
        if self.manual_edit.text().strip():
            return self.manual_edit.text().strip()
        return self.sd_combo.currentData() or self.sd_combo.currentText()


class OutputFolderPage(QWizardPage):
    """Output folder selection page."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Output Folder")
        self.setSubTitle(
            "Choose where your imported recordings will be saved."
        )

        layout = QVBoxLayout(self)

        info = QLabel(
            "Recordings will be organized into folders by month and day:\n"
            "  output_folder/\n"
            "    01-January/\n"
            "      01/\n"
            "      02/\n"
            "    02-February/\n"
            "      ..."
        )
        info.setStyleSheet("font-family: monospace;")
        layout.addWidget(info)

        layout.addSpacing(20)

        # Folder selection
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Output folder:"))

        self.folder_edit = QLineEdit()
        self.folder_edit.textChanged.connect(self.completeChanged)
        folder_layout.addWidget(self.folder_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse)
        folder_layout.addWidget(browse_btn)

        layout.addLayout(folder_layout)
        layout.addStretch()

    def initializePage(self):
        """Initialize with default path."""
        if not self.folder_edit.text():
            default = str(Path.home() / "DVR-Recordings")
            self.folder_edit.setText(default)

    def isComplete(self) -> bool:
        """Check if the page is complete."""
        return bool(self.folder_edit.text().strip())

    def get_output_folder(self) -> str:
        """Get the output folder path."""
        return self.folder_edit.text().strip()

    def _browse(self):
        """Open folder browser."""
        current = self.folder_edit.text()
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", current
        )
        if folder:
            self.folder_edit.setText(folder)


class SummaryPage(QWizardPage):
    """Summary page showing final configuration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTitle("Setup Complete")
        self.setSubTitle("Review your settings below.")

        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        layout.addStretch()

        note = QLabel(
            "<i>You can change these settings later from the Settings menu.</i>"
        )
        layout.addWidget(note)

    def initializePage(self):
        """Update summary when page is shown."""
        wizard = self.wizard()
        if not isinstance(wizard, FirstRunWizard):
            return

        username = wizard.username_page.get_username()
        sd_card = wizard.sd_card_page.get_sd_card_name()
        output = wizard.output_page.get_output_folder()

        self.summary_label.setText(
            f"<b>Configuration Summary:</b><br><br>"
            f"<b>Username:</b> {username}<br>"
            f"<b>SD Card:</b> {sd_card}<br>"
            f"<b>Output Folder:</b> {output}<br><br>"
            f"Source path will be:<br>"
            f"<code>/media/{username}/{sd_card}/PRIVATE/SONY/REC_FILE</code>"
        )


class FirstRunWizard(QWizard):
    """First-run setup wizard."""

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings

        self.setWindowTitle("UX570 Importer Setup")
        self.setMinimumSize(500, 400)

        # Add pages
        self.addPage(WelcomePage())
        self.username_page = UsernamePage()
        self.addPage(self.username_page)
        self.sd_card_page = SDCardPage()
        self.addPage(self.sd_card_page)
        self.output_page = OutputFolderPage()
        self.addPage(self.output_page)
        self.addPage(SummaryPage())

    def get_settings(self) -> dict:
        """Get the configured settings."""
        self.settings["username"] = self.username_page.get_username()
        self.settings["sd_card_name"] = self.sd_card_page.get_sd_card_name()
        self.settings["default_output_dir"] = self.output_page.get_output_folder()
        self.settings["default_mode"] = "copy"

        if "gui" not in self.settings:
            self.settings["gui"] = {}
        self.settings["gui"]["first_run_completed"] = True
        self.settings["gui"]["checksum_enabled"] = True

        return self.settings
