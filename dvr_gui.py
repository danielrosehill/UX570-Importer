#!/usr/bin/env python3
"""
UX570 Importer GUI

PyQt6 GUI application for importing recordings from a Sony ICD-UX570 DVR.
"""

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from PyQt6.QtWidgets import QApplication

from ux570_importer import utils
from ux570_importer.gui.first_run_wizard import FirstRunWizard
from ux570_importer.gui.main_window import MainWindow


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("UX570 Importer")
    app.setOrganizationName("Daniel Rosehill")

    # Load settings
    settings = utils.load_settings()

    # Check if first run
    if not settings.get("gui", {}).get("first_run_completed", False):
        wizard = FirstRunWizard(settings)
        if wizard.exec():
            settings = wizard.get_settings()
            utils.save_settings(settings)
        else:
            # User cancelled wizard
            sys.exit(0)

    # Show main window
    window = MainWindow(settings)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
