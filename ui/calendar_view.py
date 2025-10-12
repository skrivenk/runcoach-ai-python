"""Calendar View Widget"""

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QCursor, QFontMetrics


class AddWorkoutDialog(QDialog):
    """Minimal dialog to add a workout for a specific date."""
    def __init__(self, parent=None, date_str=None):
        super().__init__(parent)
        self.setWindowTitle(f"Add Workout – {date_str}")
        self.date_str = date_str

        layout = QFormLayout(self)

        self.type_box = QComboBox()
        self.type_box.addItems(["easy", "tempo", "intervals", "long", "rest"])

        self.dist_box = QDoubleSpinBox()
        self.dist_box.setRange(0, 100)
        self.dist_box.setDecimals(1)
        self.dist_box.setSingleStep(0.5)

        layout.addRow("Type", self.type_box)
        layout.addRow("Planned distance (mi)", self.dist_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def value(self):
        return {
            "workout_type": self.type_box.currentText(),
            "planned_distance": float(self.dist_box.value()),
        }


class CalendarView(QWidget):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_date = QDate.currentDate()
        self.current_plan = None

        # Map 'YYYY-MM-DD' -> list[workout dict]
        self.workouts = {}

        # set in init_ui()
        self.scroll = None
        self.grid_container = None
        self.grid_layout = None
        self.month_label = None
        self.recalc_btn = None

        self.init_ui()

    # --- Public API for MainWindow ---

    def set_plan(self, plan, db_manager):
        """(Legacy) Set the current plan and DB, then load."""
        self.current_plan = plan
        self.db_manager = db_manager
        self.load_workouts()
        self.refresh_calendar()

    def set_current_plan(self, plan: dict):
        """Preferred: MainWindow calls this to show a specific plan."""
        self.current_plan = plan
        self.load_workouts()
        self.refresh_calendar()

    # --- Data loading ---

    def load_workouts(self):
        """Load workouts from database for the current plan."""
        if not self.db_manager or not self.current_plan:
            self.workouts = {}
            return

        all_workouts = self.db_manager.get_workouts_by_plan(self.current_plan['id'])
        by_date = {}
        for w in all_workouts:
            d = w['date']
            by_date.setdefault(d, []).append(w)
        self.workouts = by_date

    # --- UI construction ---

    def init_ui(self):
        """Initialize the calendar view UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)

        # Calendar container (header + weekdays + grid)
        calendar_container = QFrame()
        calendar_container.setObjectName("calendarContainer")
        calendar_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        calendar_layout = QVBoxLayout()
        calendar_layout.setContentsMargins(12, 0, 12, 0)  # give L/R padding inside the panel

        # Header with month navigation (responsive + compact)
        header = self.create_header()
        calendar_layout.addWidget(header)

        # Weekday headers
        weekdays = self.create_weekday_headers()
        calendar_layout.addWidget(weekdays)

        # Calendar grid
        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(6)
        for i in range(7):
            self.grid_layout.setColumnStretch(i, 1)
        self.grid_container.setLayout(self.grid_layout)
        calendar_layout.addWidget(self.grid_container)

        calendar_container.setLayout(calendar_layout)

        # Wrap calendar in a scroll area (vertical only)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("calendarScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # IMPORTANT: give the viewport a right margin so content never hides under the vertical scrollbar
        self.scroll.setViewportMargins(0, 0, 18, 0)  # right gutter (~scrollbar width)

        self.scroll.setWidget(calendar_container)
        layout.addWidget(self.scroll)

        # Status window placeholder
        status = self.create_status_window()
        layout.addWidget(status)

        self.setLayout(layout)
        self.apply_styles()

        # Initial calendar render
        self.refresh_calendar()

    def _compute_month_label_width(self) -> int:
        """Compute a fixed width large enough for the longest month label with year, using current font."""
        fm: QFontMetrics = self.fontMetrics()
        # Use a wide year to be safe; 2088 is a nice 'wide' pattern
        max_text = max(
            (f"{QDate.longMonthName(i)} 2088" for i in range(1, 13)),
            key=lambda s: fm.horizontalAdvance(s)
        )
        width = fm.horizontalAdvance(max_text) + 24  # padding
        return max(200, width)  # ensure a sensible floor

    def create_header(self) -> QWidget:
        """Create calendar header with navigation."""
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Center "nav group": [prev] [Month YYYY] [next]
        nav_group = QWidget()
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(8)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("navButton")
        prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        prev_btn.clicked.connect(self.previous_month)

        self.month_label = QLabel()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # FIXED width large enough for the longest month label → keeps arrows close & consistent
        self.month_label.setFixedWidth(self._compute_month_label_width())
        self.update_month_label()

        next_btn = QPushButton("▶")
        next_btn.setObjectName("navButton")
        next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        next_btn.clicked.connect(self.next_month)

        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(next_btn)

        nav_group.setLayout(nav_layout)
        nav_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)  # compact center cluster

        # Recalculate – FIXED at the far right
        self.recalc_btn = QPushButton("🔄 Recalculate")
        self.recalc_btn.setObjectName("actionButton")
        self.recalc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.recalc_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # TODO: connect to AI recompute when ready

        # Layout: [stretch] [nav_group centered] [stretch] [recalc right, with a tiny gutter]
        header_layout.addStretch()
        header_layout.addWidget(nav_group, 0, Qt.AlignmentFlag.AlignCenter)
        header_layout.addStretch()
        header_layout.addWidget(self.recalc_btn, 0, Qt.AlignmentFlag.AlignRight)

        header.setLayout(header_layout)
        return header

    def create_weekday_headers(self) -> QWidget:
        """Create weekday header row."""
        container = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        weekdays = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        for day in weekdays:
            label = QLabel(day)
            label.setObjectName("weekdayHeader")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)

        container.setLayout(layout)
        return container

    # --- Calendar rendering ---

    def refresh_calendar(self):
        """Refresh the calendar grid with current month's days."""
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
        start_day_of_week = first_day.dayOfWeek() % 7  # Sunday becomes 0

        total_cells = 42  # 6 weeks * 7 days
        row = 0
        col = 0

        for cell_num in range(total_cells):
            in_month = (start_day_of_week <= cell_num < start_day_of_week + days_in_month)
            if not in_month:
                empty_cell = QFrame()
                empty_cell.setObjectName("emptyCell")
                self.grid_layout.addWidget(empty_cell, row, col)
            else:
                day_number = cell_num - start_day_of_week + 1
                date = QDate(year, month, day_number)
                day_cell = self.create_day_cell(date)
                self.grid_layout.addWidget(day_cell, row, col)

            col += 1
            if col > 6:
                col = 0
                row += 1

        self._apply_cell_sizes()
        self._compact_header_if_needed()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_cell_sizes()
        self._compact_header_if_needed()

    def _viewport_width(self) -> int:
        if self.scroll and self.scroll.viewport():
            return self.scroll.viewport().width()
        return max(600, self.width() - 40)

    def _apply_cell_sizes(self):
        """Compute cell sizes from the viewport and fix them to prevent drift."""
        if not self.grid_layout:
            return

        avail_w = self._viewport_width()
        spacing = self.grid_layout.horizontalSpacing() or 0
        cols = 7

        # Subtract inter-column gaps (6) and a tiny fudge to avoid wrap due to rounding
        cell_w = max(90, int((avail_w - (spacing * (cols - 1)) - 2) / cols))
        cell_h = max(72, int(cell_w * 0.75))  # gentle aspect

        for i in range(self.grid_layout.count()):
            w = self.grid_layout.itemAt(i).widget()
            if not w or w.objectName() not in ("dayCell", "emptyCell"):
                continue
            w.setMinimumSize(0, 0)
            w.setMaximumSize(16777215, 16777215)
            w.setFixedSize(cell_w, cell_h)

        self.grid_container.setMinimumWidth(avail_w)

    def _compact_header_if_needed(self):
        """Toggle the Recalculate button label based on available width."""
        try:
            vw = self.scroll.viewport().width() if self.scroll and self.scroll.viewport() else self.width()
            if self.recalc_btn:
                if vw < 900 and self.recalc_btn.text() != "🔄":
                    self.recalc_btn.setText("🔄")
                elif vw >= 900 and self.recalc_btn.text() != "🔄 Recalculate":
                    self.recalc_btn.setText("🔄 Recalculate")
        except Exception:
            pass

    def create_day_cell(self, date: QDate) -> QFrame:
        """Create a single day cell with workout data and click handler."""
        cell = QFrame()
        cell.setObjectName("dayCell")
        cell.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(8, 8, 8, 8)

        # Day number
        day_label = QLabel(str(date.day()))
        day_label.setObjectName("dayNumber")
        layout.addWidget(day_label)

        # Workouts for this date
        date_str = date.toString("yyyy-MM-dd")
        workouts_for_day = self.workouts.get(date_str, [])

        if workouts_for_day:
            first = workouts_for_day[0]
            type_label = QLabel(first['workout_type'].upper())
            type_label.setObjectName("workoutType")
            layout.addWidget(type_label)

            if first.get('planned_distance') is not None:
                distance_label = QLabel(f"{float(first['planned_distance']):.1f} mi")
                distance_label.setObjectName("workoutDistance")
                layout.addWidget(distance_label)

            if first.get('completed'):
                completed_label = QLabel("✓ Completed")
                completed_label.setObjectName("completedLabel")
                layout.addWidget(completed_label)

            if len(workouts_for_day) > 1:
                extra = QLabel(f"+{len(workouts_for_day) - 1} more")
                extra.setObjectName("workoutDistance")
                layout.addWidget(extra)
        else:
            no_workout = QLabel("—")
            no_workout.setObjectName("noWorkout")
            no_workout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_workout)

        cell.setLayout(layout)

        # Click handler → open AddWorkoutDialog
        def _click_event(_mouse_event):
            self.add_workout(date_str)

        cell.mousePressEvent = _click_event
        return cell

    # --- Actions ---

    def add_workout(self, date_str: str):
        """Open the add workout dialog and insert into DB on OK."""
        if not self.db_manager or not self.current_plan:
            return

        dlg = AddWorkoutDialog(self, date_str)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.value()
            self.db_manager.create_workout({
                "plan_id": self.current_plan["id"],
                "date": date_str,
                "workout_type": data["workout_type"],
                "planned_distance": data["planned_distance"],
                "planned_intensity": None,
                "description": None,
                "notes": None,
                "modified_by": "user",
            })
            self.load_workouts()
            self.refresh_calendar()

    def create_status_window(self) -> QWidget:
        """Create status window."""
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

        # Status content (placeholder)
        status_content = QLabel(
            "🟢 Goal Attainability: 87% (On Track)\n"
            "Week Progress: 18/32 miles (56%)\n"
            "Next Key Workout: Saturday 10mi Long Run"
        )
        status_content.setObjectName("statusContent")

        layout.addWidget(status_content)

        container.setLayout(layout)
        return container

    # --- Navigation / helpers ---

    def update_month_label(self):
        """Update the month/year label."""
        month_name = self.current_date.toString("MMMM yyyy")
        self.month_label.setText(month_name)

    def previous_month(self):
        """Go to previous month."""
        self.current_date = self.current_date.addMonths(-1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    def next_month(self):
        """Go to next month."""
        self.current_date = self.current_date.addMonths(1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    # --- Styles ---

    def apply_styles(self):
        """Apply custom styles."""
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
                padding: 10px;
            }

            QFrame#dayCell {
                background-color: #f8f9fa;
                border: 1px solid #ecf0f1;
                border-radius: 8px;
                padding: 6px;
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
