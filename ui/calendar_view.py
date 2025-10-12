"""Calendar View Widget"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QGridLayout, QFrame)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QCursor
from datetime import datetime, timedelta


class CalendarView(QWidget):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_date = QDate.currentDate()
        self.current_plan = None
        self.workouts = {}
        self.init_ui()

    def set_plan(self, plan, db_manager):
        """Set the current plan and load workouts"""
        self.current_plan = plan
        self.db_manager = db_manager
        self.load_workouts()
        self.refresh_calendar()

    def load_workouts(self):
        """Load workouts from database for current month"""
        if not self.db_manager or not self.current_plan:
            return

        # Get all workouts for the plan
        all_workouts = self.db_manager.get_workouts_by_plan(self.current_plan['id'])

        # Store in dict with date as key
        self.workouts = {}
        for workout in all_workouts:
            self.workouts[workout['date']] = workout

    def init_ui(self):
        """Initialize the calendar view UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(24, 24, 24, 24)

        # Calendar container
        calendar_container = QFrame()
        calendar_container.setObjectName("calendarContainer")
        calendar_layout = QVBoxLayout()

        # Header with month navigation
        header = self.create_header()
        calendar_layout.addWidget(header)

        # Weekday headers
        weekdays = self.create_weekday_headers()
        calendar_layout.addWidget(weekdays)

        # Calendar grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        self.grid_container.setLayout(self.grid_layout)
        calendar_layout.addWidget(self.grid_container)

        calendar_container.setLayout(calendar_layout)
        layout.addWidget(calendar_container)

        # Status window placeholder
        status = self.create_status_window()
        layout.addWidget(status)

        self.setLayout(layout)
        self.apply_styles()

        # Initial calendar render
        self.refresh_calendar()

    def create_header(self) -> QWidget:
        """Create calendar header with navigation"""
        header = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(0)

        # Previous month button
        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("navButton")
        prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        prev_btn.clicked.connect(self.previous_month)

        # Month/Year label (centered, fixed width)
        self.month_label = QLabel()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_label.setFixedWidth(250)  # Fixed width so arrows don't move
        self.update_month_label()

        # Next month button
        next_btn = QPushButton("▶")
        next_btn.setObjectName("navButton")
        next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        next_btn.clicked.connect(self.next_month)

        # Recalculate button with emoji refresh icon
        recalc_btn = QPushButton("🔄 Recalculate")
        recalc_btn.setObjectName("actionButton")
        recalc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Layout: stretch, prev, spacing, month (fixed width), spacing, next, stretch, recalculate
        layout.addStretch()
        layout.addWidget(prev_btn)
        layout.addSpacing(12)
        layout.addWidget(self.month_label)
        layout.addSpacing(12)
        layout.addWidget(next_btn)
        layout.addStretch()
        layout.addWidget(recalc_btn)

        header.setLayout(layout)
        return header

    def create_weekday_headers(self) -> QWidget:
        """Create weekday header row"""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)

        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for day in weekdays:
            label = QLabel(day)
            label.setObjectName("weekdayHeader")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        container.setLayout(layout)
        return container

    def refresh_calendar(self):
        """Refresh the calendar grid with current month's days"""
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get first day of month and number of days
        year = self.current_date.year()
        month = self.current_date.month()

        first_day = QDate(year, month, 1)
        days_in_month = first_day.daysInMonth()
        start_day_of_week = first_day.dayOfWeek() % 7  # 0 = Sunday, 6 = Saturday

        # Calculate total cells needed (6 rows)
        total_cells = 42

        # Create calendar grid
        row = 0
        col = 0

        for cell_num in range(total_cells):
            if cell_num < start_day_of_week or cell_num >= start_day_of_week + days_in_month:
                # Empty cell (before month starts or after month ends)
                empty_cell = QFrame()
                empty_cell.setObjectName("emptyCell")
                self.grid_layout.addWidget(empty_cell, row, col)
            else:
                # Day cell
                day_number = cell_num - start_day_of_week + 1
                date = QDate(year, month, day_number)
                day_cell = self.create_day_cell(date)
                self.grid_layout.addWidget(day_cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

    def create_day_cell(self, date: QDate) -> QFrame:
        """Create a single day cell with workout data"""
        cell = QFrame()
        cell.setObjectName("dayCell")
        cell.setMinimumSize(120, 100)
        cell.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(8, 8, 8, 8)

        # Day number
        day_label = QLabel(str(date.day()))
        day_label.setObjectName("dayNumber")
        layout.addWidget(day_label)

        # Get workout for this date
        date_str = date.toString("yyyy-MM-dd")
        workout = self.workouts.get(date_str)

        if workout:
            # Workout type
            workout_type = workout['workout_type'].upper()
            type_label = QLabel(workout_type)
            type_label.setObjectName("workoutType")
            layout.addWidget(type_label)

            # Distance
            if workout['planned_distance']:
                distance_label = QLabel(f"{workout['planned_distance']:.1f} mi")
                distance_label.setObjectName("workoutDistance")
                layout.addWidget(distance_label)

            # Completed indicator
            if workout['completed']:
                completed_label = QLabel("✓ Completed")
                completed_label.setObjectName("completedLabel")
                layout.addWidget(completed_label)
        else:
            # No workout
            no_workout = QLabel("—")
            no_workout.setObjectName("noWorkout")
            no_workout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_workout)

        cell.setLayout(layout)
        return cell

    def create_status_window(self) -> QWidget:
        """Create status window"""
        container = QFrame()
        container.setObjectName("statusWindow")
        container.setMaximumHeight(200)

        layout = QVBoxLayout()

        # Header
        header = QHBoxLayout()
        title = QLabel("STATUS DASHBOARD")
        title.setObjectName("statusTitle")

        expand_btn = QPushButton("▲")
        expand_btn.setObjectName("expandButton")
        expand_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        header.addWidget(title)
        header.addStretch()
        header.addWidget(expand_btn)

        layout.addLayout(header)

        # Status content
        status_content = QLabel("🟢 Goal Attainability: 87% (On Track)\nWeek Progress: 18/32 miles (56%)\nNext Key Workout: Saturday 10mi Long Run")
        status_content.setObjectName("statusContent")

        layout.addWidget(status_content)

        container.setLayout(layout)
        return container

    def update_month_label(self):
        """Update the month/year label"""
        month_name = self.current_date.toString("MMMM yyyy")
        self.month_label.setText(month_name)

    def previous_month(self):
        """Go to previous month"""
        self.current_date = self.current_date.addMonths(-1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    def next_month(self):
        """Go to next month"""
        self.current_date = self.current_date.addMonths(1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    def apply_styles(self):
        """Apply custom styles"""
        self.setStyleSheet("""
            QFrame#calendarContainer {
                background-color: white;
                border-radius: 12px;
                padding: 24px;
            }
            
            QLabel#monthLabel {
                font-size: 24px;
                color: #2c3e50;
                font-weight: bold;
            }
            
            QPushButton#navButton {
                background-color: transparent;
                color: #2c3e50;
                border: 1px solid rgba(44, 62, 80, 0.3);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 16px;
            }
            
            QPushButton#navButton:hover {
                background-color: rgba(44, 62, 80, 0.1);
            }
            
            QPushButton#actionButton {
                background-color: white;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 6px;
                padding: 8px 16px;
            }
            
            QPushButton#actionButton:hover {
                background-color: #ecf0f1;
            }
            
            QLabel#weekdayHeader {
                font-size: 14px;
                font-weight: 600;
                color: #7f8c8d;
                text-transform: uppercase;
                padding: 12px;
            }
            
            QFrame#dayCell {
                background-color: #f8f9fa;
                border: 1px solid #ecf0f1;
                border-radius: 8px;
                padding: 8px;
            }
            
            QFrame#dayCell:hover {
                background-color: #e8f4f8;
                border-color: #3498db;
            }
            
            QFrame#emptyCell {
                background-color: transparent;
                border: none;
            }
            
            QLabel#dayNumber {
                font-size: 16px;
                color: #2c3e50;
                font-weight: 600;
            }
            
            QLabel#workoutType {
                font-size: 11px;
                color: #3498db;
                font-weight: 600;
                margin-top: 4px;
            }
            
            QLabel#workoutDistance {
                font-size: 13px;
                color: #555;
                margin-top: 2px;
            }
            
            QLabel#completedLabel {
                font-size: 10px;
                color: #27ae60;
                margin-top: 4px;
            }
            
            QLabel#noWorkout {
                font-size: 20px;
                color: #bdc3c7;
                margin-top: 8px;
            }
            
            QFrame#statusWindow {
                background-color: white;
                border-top: 3px solid #3498db;
                padding: 16px 24px;
            }
            
            QLabel#statusTitle {
                font-size: 14px;
                font-weight: 600;
                color: #2c3e50;
                letter-spacing: 0.5px;
            }
            
            QLabel#statusContent {
                font-size: 14px;
                color: #555;
                line-height: 1.6;
            }
            
            QPushButton#expandButton {
                background-color: transparent;
                border: none;
                font-size: 14px;
                color: #7f8c8d;
                padding: 4px;
            }
        """)