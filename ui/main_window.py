"""Main Window for RunCoach AI"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QStackedWidget, QMessageBox)
from PySide6.QtCore import Qt
from ui.welcome_screen import WelcomeScreen
from ui.calendar_view import CalendarView
from ui.settings_dialog import SettingsDialog  # NEW


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_plan = None

        self.setWindowTitle("🏃 RunCoach AI")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header = self.create_header()
        main_layout.addWidget(header)

        self.stack = QStackedWidget()

        self.welcome_screen = WelcomeScreen()
        self.calendar_view = CalendarView(self.db_manager)

        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.calendar_view)

        main_layout.addWidget(self.stack)

        # If you later wire Import Plan:
        # self.welcome_screen.import_plan_requested.connect(self.show_import_dialog)

        central_widget.setLayout(main_layout)

        self.check_for_plans()
        self._apply_planner_config_from_db()  # load settings on startup

    def create_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(70)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("🏃 RunCoach AI")
        title.setObjectName("title")

        layout.addWidget(title)
        layout.addStretch()

        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("headerButton")
        settings_btn.clicked.connect(self.show_settings)

        layout.addWidget(settings_btn)

        header.setLayout(layout)
        return header

    def check_for_plans(self):
        current_plan_id = self.db_manager.get_current_plan_id()
        if not current_plan_id:
            self.stack.setCurrentWidget(self.welcome_screen)
            return

        plan = self.db_manager.get_plan_by_id(current_plan_id)
        if not plan:
            self.stack.setCurrentWidget(self.welcome_screen)
            return

        self.calendar_view.set_current_plan(plan)
        self.stack.setCurrentWidget(self.calendar_view)

    def show_plan_wizard(self):
        """Show the plan creation wizard"""
        from ui.plan_wizard import PlanWizard
        wizard = PlanWizard(self)
        wizard.plan_created.connect(self.on_plan_created)
        wizard.exec()

    def on_plan_created(self, plan_data: dict):
        plan_id = self.db_manager.create_plan(plan_data)

        # Optional baseline
        if plan_data.get("baseline_distance") and plan_data.get("baseline_time"):
            baseline = {
                "plan_id": plan_id,
                "date": plan_data["start_date"],
                "distance": plan_data["baseline_distance"],
                "time_seconds": plan_data["baseline_time"],
                "rpe": plan_data.get("baseline_rpe"),
                "avg_hr": None, "elevation_gain": None, "notes": None,
            }
            self.db_manager.create_baseline_run(baseline)

        # Seed a week so calendar shows something
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(plan_data["start_date"])
        for i in range(7):
            self.db_manager.create_workout({
                "plan_id": plan_id,
                "date": (start_dt + timedelta(days=i)).strftime("%Y-%m-%d"),
                "workout_type": "easy" if i % 2 == 0 else "tempo",
                "planned_distance": 5.0,
                "planned_intensity": None,
                "description": f"Day {i + 1} (initial seed)",
                "notes": None,
                "modified_by": "initial_gen",
            })

        self.db_manager.set_current_plan_id(plan_id)
        self.check_for_plans()

    # --- Settings ---

    def _apply_planner_config_from_db(self):
        """Read DB settings and push to CalendarView/AI planner."""
        mode = (self.db_manager.get_setting("planner_mode") or "heuristic").lower()
        key = self.db_manager.get_setting("openai_api_key")
        use_openai = (mode == "openai" and bool(key))
        self.calendar_view.configure_planner(use_openai=use_openai, api_key=key)

    def show_settings(self):
        dlg = SettingsDialog(self, db_manager=self.db_manager)
        if dlg.exec():
            # When saved, re-read and apply
            self._apply_planner_config_from_db()
            QMessageBox.information(self, "Settings", "Settings saved.")

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f7fa; }
            QWidget#header { background-color: #2c3e50; }
            QLabel#title { color: white; font-size: 24px; font-weight: bold; }
            QPushButton { background-color: #3498db; color: white; border: none; border-radius: 6px;
                          padding: 10px 20px; font-size: 14px; font-weight: 500; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
            QPushButton#headerButton { background-color: white; color: #2c3e50; border: 1px solid rgba(255,255,255,0.3); }
            QPushButton#headerButton:hover { background-color: #ecf0f1; }
        """)
