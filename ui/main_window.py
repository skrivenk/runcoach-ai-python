"""Main Window for RunCoach AI"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QStackedWidget, QMessageBox)
from PySide6.QtCore import Qt
from ui.welcome_screen import WelcomeScreen
from ui.calendar_view import CalendarView


class MainWindow(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db_manager = db_manager
        self.current_plan = None

        self.setWindowTitle("🏃 RunCoach AI")
        self.setMinimumSize(1200, 800)
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
        self.calendar_view = CalendarView()

        # Add views to stack
        self.stack.addWidget(self.welcome_screen)
        self.stack.addWidget(self.calendar_view)

        main_layout.addWidget(self.stack)

        # Connect signals
        self.welcome_screen.create_plan_clicked.connect(self.show_plan_wizard)

        # Set layout
        central_widget.setLayout(main_layout)

        # Show welcome screen by default
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
        """Check if any plans exist"""
        plans = self.db_manager.get_all_plans()

        if plans:
            self.current_plan = plans[0]
            self.stack.setCurrentWidget(self.calendar_view)
        else:
            self.stack.setCurrentWidget(self.welcome_screen)

    def show_plan_wizard(self):
        """Show the plan creation wizard"""

        # For now, just show a message
        # We'll implement the full wizard next
        msg = QMessageBox()
        msg.setWindowTitle("Plan Creation")
        msg.setText("Plan creation wizard coming soon!\n\nFor now, here's a test plan being created...")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()

        # Create a test plan
        self.create_test_plan()

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

    def show_settings(self):
        """Show settings dialog"""
        msg = QMessageBox()
        msg.setWindowTitle("Settings")
        msg.setText("Settings dialog coming soon!")
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