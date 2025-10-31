# ui/main_window.py
from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QMessageBox, QStatusBar
)
from PySide6.QtGui import QAction

from database.db_manager import DatabaseManager
from ui.calendar_view import CalendarView
from ui.settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, db_manager: Optional[DatabaseManager] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("RunCoach AI")
        self.resize(1200, 800)

        # DB
        self.db = db_manager or DatabaseManager()

        # Status bar
        self.statusbar = QStatusBar(self)
        self.setStatusBar(self.statusbar)

        # Central UI (Calendar)
        self.calendar_view = CalendarView(db_manager=self.db)
        central = QWidget(self)
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.calendar_view)
        self.setCentralWidget(central)

        # Menus & Settings wiring
        self._build_menus()
        self._apply_ai_config_to_calendar()

        # Ensure a plan is loaded so Add/Edit works and status shows data
        self._ensure_plan_loaded()

    # ---------------- Menus ----------------

    def _build_menus(self):
        menubar = self.menuBar()

        # App
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

        # File (placeholders for future import/export)
        file_menu = menubar.addMenu("&File")
        file_menu.addAction(QAction("Export…", self, enabled=False))
        file_menu.addAction(QAction("Import…", self, enabled=False))

        # Help
        help_menu = menubar.addMenu("&Help")
        act_about = QAction("About", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

        act_ai_diag = QAction("AI Diagnostics…", self)
        act_ai_diag.triggered.connect(self._run_ai_diagnostics)
        help_menu.addAction(act_ai_diag)

    # ------------- Settings / AI config -------------

    def _open_settings(self):
        dlg = SettingsDialog(self, self.db)
        if dlg.exec():  # user pressed Save
            self._apply_ai_config_to_calendar()
            # Optionally refresh status immediately after saving settings
            self.calendar_view.refresh_status()
            self.statusBar().showMessage("Settings saved.", 2500)

    def _apply_ai_config_to_calendar(self):
        """
        Pull OpenAI settings from DB and configure the Calendar's planner.
        """
        cfg = self.db.get_openai_settings()

        # Preferred path: CalendarView exposes configure_planner()
        try:
            self.calendar_view.configure_planner(
                use_openai=cfg["use_openai"],
                api_key=cfg["api_key"],
            )
        except Exception:
            pass

        # If AIPlanner supports model in set_config, apply it too
        try:
            self.calendar_view._planner.set_config(
                use_openai=cfg["use_openai"],
                api_key=cfg["api_key"],
                model=cfg["model"],
            )
        except Exception:
            pass

    # ------------- Plan bootstrap -------------

    def _ensure_plan_loaded(self):
        """
        On first launch (or if settings were reset), ensure a plan is active:
        - Try last-used plan (current_plan_id)
        - Else pick the first plan, if any
        - Else create a simple default plan and select it
        """
        pid = self.db.get_current_plan_id()
        plan = None
        if pid is not None:
            plan = self.db.get_plan_by_id(pid)

        if not plan:
            plans = self.db.get_all_plans()
            if plans:
                plan = plans[0]
                self.db.set_current_plan_id(plan["id"])
            else:
                # Create a quick default plan
                today = QDate.currentDate().toString("yyyy-MM-dd")
                plan_id = self.db.create_plan({
                    "name": "My First Plan",
                    "goal_type": "general",
                    "start_date": today,
                    "race_date": None,
                    "duration_weeks": 12,
                    "max_days_per_week": 5,
                    "long_run_day": "Sunday",
                    "weekly_increase_cap": 0.10,
                    "long_run_cap": 0.30,
                    "guardrails_enabled": True,
                })
                self.db.set_current_plan_id(plan_id)
                plan = self.db.get_plan_by_id(plan_id)

        if plan:
            self.calendar_view.set_plan(plan, self.db)
            # Ensure the status panel shows something right away
            self.calendar_view.refresh_status()

    # ---------------- Diagnostics / About ----------------

    def _run_ai_diagnostics(self):
        try:
            ok, message, usage = self.calendar_view._planner.ping()
            details = []
            if usage:
                if usage.get("model"):
                    details.append(f"Model: {usage['model']}")
                if usage.get("prompt_tokens") is not None:
                    details.append(f"Prompt tokens: {usage['prompt_tokens']}")
                if usage.get("completion_tokens") is not None:
                    details.append(f"Completion tokens: {usage['completion_tokens']}")
                if usage.get("total_tokens") is not None:
                    details.append(f"Total tokens: {usage['total_tokens']}")
            extra = ("\n\n" + "\n".join(details)) if details else ""
            if ok:
                QMessageBox.information(self, "AI Diagnostics", f"✅ Success!\n{message}{extra}")
            else:
                QMessageBox.warning(self, "AI Diagnostics", f"⚠️ Check failed.\n{message}{extra}")
            # Nudge the status dashboard so API totals appear immediately
            self.calendar_view.refresh_status()
        except Exception as e:
            QMessageBox.critical(self, "AI Diagnostics", f"Unexpected error: {e}")

    def _about(self):
        QMessageBox.information(
            self,
            "About RunCoach AI",
            "RunCoach AI\n• Calendar-based planning\n• Optional OpenAI-powered weekly suggestions\n"
            "• Local SQLite database in your user directory",
        )


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
