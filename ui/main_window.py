"""Main Window for RunCoach AI"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QMessageBox
)
from PySide6.QtCore import Qt

# IMPORTANT: main_window.py is inside the ui/ package, so use RELATIVE imports
from .welcome_screen import WelcomeScreen
from .calendar_view import CalendarView


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_plan = None

        self.setWindowTitle("🏃 RunCoach AI")
        self.setMinimumSize(900, 600)
        self.resize(1200, 800)

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        """Initialize the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Stacked widget for different views
        self.stack = QStackedWidget()

        # Create views
        self.welcome_screen = WelcomeScreen()
        self.calendar_view = CalendarView(self.db_manager)

        # Add views to stack
        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.calendar_view)

        main_layout.addWidget(self.stack)

        # Connect signals (make sure names match WelcomeScreen)
        self.welcome_screen.create_plan_requested.connect(self.show_plan_wizard)
        self.welcome_screen.import_plan_requested.connect(self.show_import_dialog)

        # Set layout
        central_widget.setLayout(main_layout)

        # Decide which screen to show
        self.check_for_plans()

    def create_header(self) -> QWidget:
        """Create the header bar"""
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(70)

        layout = QHBoxLayout()
        layout.setContentsMargins(24, 0, 24, 0)

        # Title
        title = QLabel("🏃 RunCoach AI")
        title.setObjectName("title")

        layout.addWidget(title)
        layout.addStretch()

        # Settings button
        settings_btn = QPushButton("Settings")
        settings_btn.setObjectName("headerButton")
        settings_btn.clicked.connect(self.show_settings)

        layout.addWidget(settings_btn)

        header.setLayout(layout)
        return header

    def check_for_plans(self):
        """Decide which screen to show and bind the current plan to the calendar."""
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
        # Relative import because this file is inside ui/
        from .plan_wizard import PlanWizard
        wizard = PlanWizard(self)
        wizard.plan_created.connect(self.on_plan_created)
        wizard.exec()

    def on_plan_created(self, plan_data: dict):
        """Persist the plan + baseline + seed workouts; then show the calendar."""
        # 1) plan
        plan_id = self.db_manager.create_plan(plan_data)

        # 2) baseline (optional but recommended)
        baseline = {
            "plan_id": plan_id,
            "date": plan_data["start_date"],
            "distance": plan_data["baseline_distance"],
            "time_seconds": plan_data["baseline_time"],
            "rpe": plan_data.get("baseline_rpe"),
            "avg_hr": None,
            "elevation_gain": None,
            "notes": None,
        }
        self.db_manager.create_baseline_run(baseline)

        # 3) seed a week so calendar shows something
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(plan_data["start_date"])
        for i in range(7):
            self.db_manager.create_workout({
                "plan_id": plan_id,
                "date": (start_dt + timedelta(days=i)).strftime("%Y-%m-%d"),
                "workout_type": "easy" if i % 2 == 0 else "tempo",
                "planned_distance": 5.0,
                "planned_intensity": None,
                "description": f"Day {i + 1} (AI generation soon)",
                "notes": None,
                "modified_by": "initial_gen",
            })

        # 4) remember + show calendar
        self.db_manager.set_current_plan_id(plan_id)
        self.check_for_plans()

    def create_test_plan(self):
        """Create a test plan for demonstration"""
        from datetime import date, timedelta

        plan_data = {
            'name': 'Marathon Training - Test',
            'goal_type': 'marathon',
            'start_date': date.today().isoformat(),
            'race_date': (date.today() + timedelta(weeks=12)).isoformat(),
            'duration_weeks': 12,
            'max_days_per_week': 5,
            'long_run_day': 'Sunday',
            'weekly_increase_cap': 0.10,
            'long_run_cap': 0.30,
            'guardrails_enabled': True
        }

        plan_id = self.db_manager.create_plan(plan_data)

        # Create some test workouts
        start_date = date.today()
        for i in range(7):
            workout_data = {
                'plan_id': plan_id,
                'date': (start_date + timedelta(days=i)).isoformat(),
                'workout_type': 'easy' if i % 2 == 0 else 'tempo',
                'planned_distance': 5.0,
                'description': f'Day {i + 1} workout',
                'modified_by': 'initial_gen'
            }
            self.db_manager.create_workout(workout_data)

        # Reload plans and show calendar
        self.check_for_plans()

    def show_import_dialog(self):
        """Placeholder for importing an existing plan (prevents crashes for now)."""
        QMessageBox.information(
            self,
            "Import Plan",
            "Importing an existing plan is coming soon.\n\n"
            "For now, use 'Create Your First Training Plan' to get started."
        )

    def show_settings(self):
        """Show settings dialog"""
        msg = QMessageBox()
        msg.setWindowTitle("Settings")
        msg.setText("Settings dialog coming soon! Be patient 🙂")
        msg.exec()

    def apply_styles(self):
        """Apply custom styles"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f7fa;
            }

            QWidget#header {
                background-color: #2c3e50;
            }

            QLabel#title {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }

            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #21618c;
            }

            QPushButton#headerButton {
                background-color: white;
                color: #2c3e50;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }

            QPushButton#headerButton:hover {
                background-color: #ecf0f1;
            }
        """)
