"""
RunCoach AI - Desktop Application
AI-powered running training calendar
"""

import sys
from PySide6.QtWidgets import QApplication
from database.db_manager import DatabaseManager
from ui.main_window import MainWindow


def main():
    """Main entry point for the application"""

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("RunCoach AI")
    app.setOrganizationName("RunCoach")

    # Initialize database
    db_manager = DatabaseManager()

    # Create and show main window
    window = MainWindow(db_manager)
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()