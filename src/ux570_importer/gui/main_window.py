"""Main window for UX570 Importer GUI."""

from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import core, utils
from .settings_dialog import SettingsDialog


class ImportWorker(QThread):
    """Worker thread for file import operations."""

    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int, list)  # success, skipped, errors

    def __init__(
        self,
        files: list[Path],
        dest_base: Path,
        mode: str,
        checksum_enabled: bool,
    ):
        super().__init__()
        self.files = files
        self.dest_base = dest_base
        self.mode = mode
        self.checksum_enabled = checksum_enabled
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        success_count = 0
        skip_count = 0
        errors = []

        for i, f in enumerate(self.files):
            if self._cancelled:
                break

            success, message = core.import_file(
                f, self.dest_base, self.mode, self.checksum_enabled
            )

            if success:
                success_count += 1
            else:
                skip_count += 1
                if "already exists" not in message:
                    errors.append(message)

            self.progress.emit(i + 1, len(self.files), message)

        self.finished.emit(success_count, skip_count, errors)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.discovered_files: list[Path] = []
        self.import_worker: ImportWorker | None = None

        self.setWindowTitle("UX570 Importer")
        self.setMinimumSize(700, 500)

        self._setup_ui()
        self._load_settings()
        self._refresh_source()

    def _setup_ui(self):
        """Set up the main UI layout."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Source section
        source_group = QGroupBox("Source Device")
        source_layout = QHBoxLayout(source_group)

        self.source_label = QLabel("Not detected")
        source_layout.addWidget(self.source_label, 1)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_source)
        source_layout.addWidget(self.refresh_btn)

        layout.addWidget(source_group)

        # Output section
        output_group = QGroupBox("Output Folder")
        output_layout = QHBoxLayout(output_group)

        self.output_edit = QLineEdit()
        output_layout.addWidget(self.output_edit, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(browse_btn)

        layout.addWidget(output_group)

        # Files table
        files_group = QGroupBox("Discovered Files")
        files_layout = QVBoxLayout(files_group)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(
            ["", "Filename", "Date/Time", "Folder", "Size"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        files_layout.addWidget(self.files_table)

        # Select all / none buttons
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        select_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none)
        select_layout.addWidget(select_none_btn)

        select_layout.addStretch()

        self.file_count_label = QLabel("0 files")
        select_layout.addWidget(self.file_count_label)

        files_layout.addLayout(select_layout)
        layout.addWidget(files_group, 1)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QHBoxLayout(options_group)

        # Mode selection
        mode_label = QLabel("Mode:")
        options_layout.addWidget(mode_label)

        self.copy_radio = QRadioButton("Copy")
        self.move_radio = QRadioButton("Move")
        options_layout.addWidget(self.copy_radio)
        options_layout.addWidget(self.move_radio)

        options_layout.addSpacing(20)

        # Checksum option
        self.checksum_check = QCheckBox("Generate SHA256 checksums")
        options_layout.addWidget(self.checksum_check)

        options_layout.addStretch()

        # Settings button
        settings_btn = QPushButton("Settings...")
        settings_btn.clicked.connect(self._open_settings)
        options_layout.addWidget(settings_btn)

        layout.addWidget(options_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # Import button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.import_btn = QPushButton("Import Selected")
        self.import_btn.setMinimumWidth(150)
        self.import_btn.clicked.connect(self._start_import)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _load_settings(self):
        """Load settings into UI."""
        # Output directory
        output_dir = self.settings.get("gui", {}).get("last_output_dir")
        if not output_dir:
            output_dir = self.settings.get("default_output_dir", "~/DVR-Recordings")
        self.output_edit.setText(str(utils.expand_path(output_dir)))

        # Mode
        mode = self.settings.get("default_mode", "copy")
        if mode == "move":
            self.move_radio.setChecked(True)
        else:
            self.copy_radio.setChecked(True)

        # Checksum
        checksum = self.settings.get("gui", {}).get("checksum_enabled", True)
        self.checksum_check.setChecked(checksum)

    def _refresh_source(self):
        """Refresh source device detection and file discovery."""
        username = self.settings.get("username") or utils.detect_username()
        sd_card_name = self.settings.get("sd_card_name", "DVR_SD")

        source_path = core.get_source_path(username, sd_card_name)

        if source_path.exists():
            self.source_label.setText(str(source_path))
            self.discovered_files = core.discover_all_files(source_path)
            self._populate_files_table()
            self.status_bar.showMessage(
                f"Found {len(self.discovered_files)} file(s)", 5000
            )
        else:
            # Try auto-detection
            dvr = utils.detect_sony_dvr(username)
            if dvr:
                self.settings["sd_card_name"] = dvr["name"]
                source_path = Path(dvr["path"]) / "PRIVATE" / "SONY" / "REC_FILE"
                self.source_label.setText(str(source_path))
                self.discovered_files = core.discover_all_files(source_path)
                self._populate_files_table()
                self.status_bar.showMessage(
                    f"Auto-detected DVR. Found {len(self.discovered_files)} file(s)",
                    5000,
                )
            else:
                self.source_label.setText(
                    f"Not found: {source_path}\n(Is the DVR connected?)"
                )
                self.discovered_files = []
                self._populate_files_table()
                self.status_bar.showMessage("DVR not detected", 5000)

    def _populate_files_table(self):
        """Populate the files table with discovered files."""
        self.files_table.setRowCount(len(self.discovered_files))

        for row, file_path in enumerate(self.discovered_files):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.files_table.setCellWidget(row, 0, checkbox_widget)

            # Filename
            self.files_table.setItem(row, 1, QTableWidgetItem(file_path.name))

            # Date/Time
            date_str = core.get_full_date_from_filename(file_path.name) or "Unknown"
            self.files_table.setItem(row, 2, QTableWidgetItem(date_str))

            # Folder
            self.files_table.setItem(row, 3, QTableWidgetItem(file_path.parent.name))

            # Size
            try:
                size = file_path.stat().st_size
                size_str = utils.get_file_size_str(size)
            except OSError:
                size_str = "?"
            self.files_table.setItem(row, 4, QTableWidgetItem(size_str))

        self.files_table.resizeColumnsToContents()
        self.files_table.setColumnWidth(0, 40)
        self._update_file_count()

    def _get_checkbox(self, row: int) -> QCheckBox | None:
        """Get the checkbox widget for a row."""
        widget = self.files_table.cellWidget(row, 0)
        if widget:
            return widget.findChild(QCheckBox)
        return None

    def _select_all(self):
        """Select all files."""
        for row in range(self.files_table.rowCount()):
            checkbox = self._get_checkbox(row)
            if checkbox:
                checkbox.setChecked(True)
        self._update_file_count()

    def _select_none(self):
        """Deselect all files."""
        for row in range(self.files_table.rowCount()):
            checkbox = self._get_checkbox(row)
            if checkbox:
                checkbox.setChecked(False)
        self._update_file_count()

    def _update_file_count(self):
        """Update the selected file count label."""
        selected = sum(
            1
            for row in range(self.files_table.rowCount())
            if (cb := self._get_checkbox(row)) and cb.isChecked()
        )
        total = self.files_table.rowCount()
        self.file_count_label.setText(f"{selected} of {total} selected")

    def _browse_output(self):
        """Open folder browser for output directory."""
        current = self.output_edit.text()
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", current
        )
        if folder:
            self.output_edit.setText(folder)

    def _open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.get_settings()
            utils.save_settings(self.settings)
            self._load_settings()
            self._refresh_source()

    def _get_selected_files(self) -> list[Path]:
        """Get list of selected files."""
        selected = []
        for row in range(self.files_table.rowCount()):
            checkbox = self._get_checkbox(row)
            if checkbox and checkbox.isChecked():
                selected.append(self.discovered_files[row])
        return selected

    def _start_import(self):
        """Start the import process."""
        selected_files = self._get_selected_files()
        if not selected_files:
            QMessageBox.warning(self, "No Files", "Please select files to import.")
            return

        output_dir = Path(self.output_edit.text())
        if not output_dir.parent.exists():
            QMessageBox.warning(
                self,
                "Invalid Path",
                f"Parent directory does not exist: {output_dir.parent}",
            )
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        mode = "move" if self.move_radio.isChecked() else "copy"
        checksum_enabled = self.checksum_check.isChecked()

        # Confirm move operation
        if mode == "move":
            reply = QMessageBox.question(
                self,
                "Confirm Move",
                f"This will DELETE {len(selected_files)} file(s) from the DVR after copying.\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Update UI for import
        self.import_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_files))
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)

        # Start worker thread
        self.import_worker = ImportWorker(
            selected_files, output_dir, mode, checksum_enabled
        )
        self.import_worker.progress.connect(self._on_import_progress)
        self.import_worker.finished.connect(self._on_import_finished)
        self.import_worker.start()

    def _on_import_progress(self, current: int, total: int, message: str):
        """Handle import progress updates."""
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        self.status_bar.showMessage(f"Importing {current}/{total}...")

    def _on_import_finished(self, success: int, skipped: int, errors: list):
        """Handle import completion."""
        self.import_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # Save last output directory
        self.settings.setdefault("gui", {})["last_output_dir"] = self.output_edit.text()
        utils.save_settings(self.settings)

        # Show result
        message = f"Import complete!\n\nImported: {success}\nSkipped: {skipped}"
        if errors:
            message += f"\n\nErrors:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                message += f"\n... and {len(errors) - 5} more"

        QMessageBox.information(self, "Import Complete", message)
        self.status_bar.showMessage(f"Imported {success} file(s)", 5000)

        # Refresh if we moved files
        if self.move_radio.isChecked():
            self._refresh_source()

    def closeEvent(self, event):
        """Handle window close."""
        if self.import_worker and self.import_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Import in Progress",
                "An import is in progress. Cancel and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.import_worker.cancel()
                self.import_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
