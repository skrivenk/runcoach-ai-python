"""Calendar View Widget"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QGridLayout, QFrame)
from PySide6.QtCore import Qt, QDate

class CalendarView(QWidget):
    def __init__(self):
        super().__init__()
        self.current_date = QDate.currentDate()
        self.init_ui()

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
        self.grid = self.create_calendar_grid()
        calendar_layout.addWidget(self.grid)

        calendar_container.setLayout(calendar_layout)
        layout.addWidget(calendar_container)

        # Status window placeholder
        status = self.create_status_window()
        layout.addWidget(status)

        self.setLayout(layout)
        self.apply_styles()

    def create_header(self) -> QWidget:
        """Create calendar header with navigation"""
        header = QWidget()
        layout = QHBoxLayout()

        # Previous month button
        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("navButton")
        prev_btn.clicked.connect(self.previous_month)

        # Month/Year label
        self.month_label = QLabel()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_month_label()

        # Next month button
        next_btn = QPushButton("▶")
        next_btn.setObjectName("navButton")
        next_btn.clicked.connect(self.next_month)

        # Recalculate button
        recalc_btn = QPushButton("Recalculate ▼")
        recalc_btn.setObjectName("actionButton")

        layout.addWidget(prev_btn)
        layout.addWidget(self.month_label, 1)
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

    def create_calendar_grid(self) -> QWidget:
        """Create the calendar grid"""
        container = QWidget()
        grid = QGridLayout()
        grid.setSpacing(8)

        # Create 6 rows × 7 columns for calendar days
        for row in range(6):
            for col in range(7):
                day_cell = self.create_day_cell(row * 7 + col + 1)
                grid.addWidget(day_cell, row, col)

        container.setLayout(grid)
        return container

    def create_day_cell(self, day: int) -> QFrame:
        """Create a single day cell"""
        cell = QFrame()
        cell.setObjectName("dayCell")
        cell.setMinimumSize(120, 100)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Day number
        day_label = QLabel(str(day))
        day_label.setObjectName("dayNumber")

        # Workout info (placeholder)
        workout_label = QLabel("5 mi\nEASY")
        workout_label.setObjectName("workoutInfo")
        workout_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(day_label)
        layout.addWidget(workout_label)

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

    def next_month(self):
        """Go to next month"""
        self.current_date = self.current_date.addMonths(1)
        self.update_month_label()

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
            
            QLabel#dayNumber {
                font-size: 16px;
                color: #2c3e50;
                font-weight: 600;
            }
            
            QLabel#workoutInfo {
                font-size: 12px;
                color: #7f8c8d;
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