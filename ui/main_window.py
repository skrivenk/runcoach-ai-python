# main_window.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog,
    QStatusBar, QToolBar  # <-- add these
)
from PySide6.QtGui import QAction, QIcon, QKeySequence

from database.db_manager import DatabaseManager
from ui.calendar_view import CalendarView
from ui.settings_dialog import SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("RunCoach AI")
        self.resize(1200, 800)

        self.db = db_manager or DatabaseManager()
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Central UI
        self.calendar_view = CalendarView(db_manager=self.db)

        central = QWidget(self)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.calendar_view)
        self.setCentralWidget(central)

        # Menus / actions
        self._build_menus()

        # Apply AI config from DB to Calendar
        self._apply_ai_config_to_calendar()

        # If you keep the "current plan id" in settings, you can select it here:
        # pid = self.db.get_current_plan_id()
        # if pid:
        #     plan = self.db.get_plan_by_id(pid)
        #     if plan:
        #         self.calendar_view.set_current_plan(plan)

    # ---------------- Menus ----------------

    def _build_menus(self):
        menubar = self.menuBar()

        # App menu
        app_menu = menubar.addMenu("&App")

        act_settings = QAction("Settings…", self)
        act_settings.setStatusTip("Configure OpenAI and application preferences")
        act_settings.triggered.connect(self._open_settings)
        app_menu.addAction(act_settings)

        app_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)
        app_menu.addAction(act_quit)

        # File menu (optional placeholders for future import/export)
        file_menu = menubar.addMenu("&File")

        act_export = QAction("Export…", self)
        act_export.setEnabled(False)  # wire this up later
        file_menu.addAction(act_export)

        act_import = QAction("Import…", self)
        act_import.setEnabled(False)  # wire this up later
        file_menu.addAction(act_import)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

    # ------------- Settings / AI config -------------

    def _open_settings(self):
        dlg = SettingsDialog(self, self.db)
        if dlg.exec():  # user pressed Save
            self._apply_ai_config_to_calendar()
            self.statusBar().showMessage("Settings saved.", 2500)

    def _apply_ai_config_to_calendar(self):
        """
        Pulls OpenAI settings from DB and configures the Calendar's planner.
        Keeps compatibility if the planner doesn't support model parameter.
        """
        cfg = self.db.get_openai_settings()
        # Preferred path: the CalendarView exposes configure_planner()
        try:
            self.calendar_view.configure_planner(
                use_openai=cfg["use_openai"],
                api_key=cfg["api_key"],
            )
        except Exception:
            pass

        # If your AIPlanner supports model in set_config, apply it, too
        try:
            self.calendar_view._planner.set_config(
                use_openai=cfg["use_openai"],
                api_key=cfg["api_key"],
                model=cfg["model"],
            )
        except Exception:
            pass

    # ---------------- Misc ----------------

    def _about(self):
        QMessageBox.information(
            self,
            "About RunCoach AI",
            "RunCoach AI\n• Calendar-based planning\n• Optional OpenAI-powered weekly suggestions\n"
            "• Local SQLite database in your user directory"
        )


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
