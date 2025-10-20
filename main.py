"""
RunCoach AI - Desktop Application
AI-powered running training calendar
"""

import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox

from database.db_manager import DatabaseManager
from ui.main_window import MainWindow


def main():
    """Main entry point for the application"""
    app = QApplication(sys.argv)
    app.setApplicationName("RunCoach AI")
    app.setOrganizationName("RunCoach")

    try:
        # Initialize database
        db_manager = DatabaseManager()

        # Create and show main window
        window = MainWindow(db_manager)
        window.show()

    except Exception as e:
        # Show a friendly crash dialog with the traceback
        tb = traceback.format_exc()
        QMessageBox.critical(
            None,
            "RunCoach AI – Startup Error",
            f"An error occurred while starting the app:\n\n{e}\n\n{tb}"
        )
        # Exit with non-zero status
        sys.exit(1)

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
