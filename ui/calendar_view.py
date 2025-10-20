"""Calendar View Widget (with AI Recalculate + Status Dashboard)"""

from typing import List, Dict, Optional
from PySide6.QtCore import QEvent  # add this near the top of the file
from PySide6.QtWidgets import (
    QWidget, QScrollArea, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, QDate, QLocale
from PySide6.QtGui import QCursor, QFontMetrics

from ui.workout_dialogs import AddEditWorkoutDialog, CompleteWorkoutDialog
from ui.ai_recalc_dialog import AIRecalcDialog
from services.ai_planner import AIPlanner, PlanContext, WorkoutSuggestion


class CalendarView(QWidget):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_date = QDate.currentDate()
        self.current_plan = None

        # Map 'YYYY-MM-DD' -> list[workout dict]
        self.workouts: Dict[str, List[Dict]] = {}

        # UI refs set in init_ui()
        self.scroll: Optional[QScrollArea] = None
        self.grid_container: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None
        self.month_label: Optional[QLabel] = None
        self.recalc_btn: Optional[QPushButton] = None
        self.status_content: Optional[QLabel] = None

        # AI planner facade (configurable at runtime)
        self._planner = AIPlanner(use_openai=False, api_key=None)

        self.init_ui()

    # --- Planner config from outside (MainWindow) ---

    def configure_planner(self, use_openai: bool, api_key: Optional[str]):
        """Called by MainWindow after Settings are saved."""
        self._planner.set_config(use_openai=use_openai, api_key=api_key)

    # --- Public API for MainWindow ---

    def set_plan(self, plan, db_manager):
        self.current_plan = plan
        self.db_manager = db_manager
        self.load_workouts()
        self.refresh_calendar()

    def set_current_plan(self, plan: dict):
        self.current_plan = plan
        self.load_workouts()
        self.refresh_calendar()

    # --- Data loading ---

    def load_workouts(self):
        if not self.db_manager or not self.current_plan:
            self.workouts = {}
            return
        all_workouts = self.db_manager.get_workouts_by_plan(self.current_plan['id'])
        by_date: Dict[str, List[Dict]] = {}
        for w in all_workouts:
            d = w['date']
            by_date.setdefault(d, []).append(w)
        self.workouts = by_date

    # --- UI construction ---

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)

        calendar_container = QFrame()
        calendar_container.setObjectName("calendarContainer")
        calendar_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        calendar_layout = QVBoxLayout()
        calendar_layout.setContentsMargins(12, 0, 12, 0)

        header = self.create_header()
        calendar_layout.addWidget(header)

        weekdays = self.create_weekday_headers()
        calendar_layout.addWidget(weekdays)

        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(6)
        for i in range(7):
            self.grid_layout.setColumnStretch(i, 1)
        self.grid_container.setLayout(self.grid_layout)
        calendar_layout.addWidget(self.grid_container)

        calendar_container.setLayout(calendar_layout)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("calendarScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setViewportMargins(0, 0, 18, 0)
        self.scroll.setWidget(calendar_container)
        layout.addWidget(self.scroll)

        status = self.create_status_window()
        layout.addWidget(status)

        self.setLayout(layout)
        self.apply_styles()
        self.refresh_calendar()

    def _compute_month_label_width(self) -> int:
        fm: QFontMetrics = self.fontMetrics()
        locale = QLocale()
        month_names = [locale.monthName(i, QLocale.FormatType.LongFormat) for i in range(1, 13)]
        samples = [f"{mn} 2088" for mn in month_names]
        max_text = max(samples, key=lambda s: fm.horizontalAdvance(s))
        width = fm.horizontalAdvance(max_text) + 24
        return max(200, width)

    def create_header(self) -> QWidget:
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)

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
        nav_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.recalc_btn = QPushButton("🔄 Recalculate")
        self.recalc_btn.setObjectName("actionButton")
        self.recalc_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.recalc_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.recalc_btn.clicked.connect(self.recalculate_week)

        header_layout.addStretch()
        header_layout.addWidget(nav_group, 0, Qt.AlignmentFlag.AlignCenter)
        header_layout.addStretch()
        header_layout.addWidget(self.recalc_btn, 0, Qt.AlignmentFlag.AlignRight)

        header.setLayout(header_layout)
        return header

    def create_weekday_headers(self) -> QWidget:
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
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        year = self.current_date.year()
        month = self.current_date.month()
        first_day = QDate(year, month, 1)
        days_in_month = first_day.daysInMonth()
        start_day_of_week = first_day.dayOfWeek() % 7

        total_cells = 42
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
        self.update_status_dashboard()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_cell_sizes()
        self._compact_header_if_needed()

    def _viewport_width(self) -> int:
        if self.scroll and self.scroll.viewport():
            return self.scroll.viewport().width()
        return max(600, self.width() - 40)

    def _apply_cell_sizes(self):
        if not self.grid_layout:
            return
        avail_w = self._viewport_width()
        spacing = self.grid_layout.horizontalSpacing() or 0
        cols = 7
        cell_w = max(90, int((avail_w - (spacing * (cols - 1)) - 2) / cols))
        cell_h = max(72, int(cell_w * 0.75))

        for i in range(self.grid_layout.count()):
            w = self.grid_layout.itemAt(i).widget()
            if not w or w.objectName() not in ("dayCell", "emptyCell"):
                continue
            w.setMinimumSize(0, 0)
            w.setMaximumSize(16777215, 16777215)
            w.setFixedSize(cell_w, cell_h)

        self.grid_container.setMinimumWidth(avail_w)

    def _compact_header_if_needed(self):
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
        cell = QFrame()
        cell.setObjectName("dayCell")
        cell.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(8, 8, 8, 8)

        day_label = QLabel(str(date.day()))
        day_label.setObjectName("dayNumber")
        layout.addWidget(day_label)

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

        def _mouse_press(ev):
            if ev.button() == Qt.RightButton:
                self._open_context_menu(date_str, workouts_for_day, cell.mapToGlobal(ev.pos()))
                return
            if ev.button() == Qt.LeftButton and ev.type() == QEvent.MouseButtonPress:
                return

        def _mouse_double_click(ev):
            if ev.button() == Qt.LeftButton:
                if workouts_for_day:
                    self.edit_workout(date_str, workouts_for_day[0])
                else:
                    self.add_workout(date_str)

        cell.mousePressEvent = _mouse_press
        cell.mouseDoubleClickEvent = _mouse_double_click
        return cell

    # --- Context menu actions ---

    def _open_context_menu(self, date_str: str, workouts_for_day: List[Dict], global_pos):
        menu = QMenu(self)
        if workouts_for_day:
            act_edit = menu.addAction("Edit workout…")
            act_complete = menu.addAction("Mark completed…")
            act_delete = menu.addAction("Delete workout")
            menu.addSeparator()
            act_add = menu.addAction("Add another workout…")
        else:
            act_add = menu.addAction("Add workout…")
            act_edit = act_complete = act_delete = None

        chosen = menu.exec(global_pos)
        if not chosen:
            return

        if chosen == act_add:
            self.add_workout(date_str)
        elif act_edit and chosen == act_edit:
            self.edit_workout(date_str, workouts_for_day[0])
        elif act_complete and chosen == act_complete:
            self.complete_workout_dialog(date_str, workouts_for_day[0])
        elif act_delete and chosen == act_delete:
            self.delete_workout(workouts_for_day[0]["id"])

    # --- Actions (CRUD) ---

    def add_workout(self, date_str: str):
        if not self.db_manager or not self.current_plan:
            return
        dlg = AddEditWorkoutDialog(self, date_str=date_str, workout=None)
        if dlg.exec():
            data = dlg.value()
            self.db_manager.create_workout({
                "plan_id": self.current_plan["id"],
                "date": date_str,
                "workout_type": data["workout_type"],
                "planned_distance": data["planned_distance"],
                "planned_intensity": data["planned_intensity"],
                "description": data["description"],
                "notes": data["notes"],
                "modified_by": "user",
            })
            self.load_workouts()
            self.refresh_calendar()

    def edit_workout(self, date_str: str, workout: dict):
        if not self.db_manager or not self.current_plan:
            return
        dlg = AddEditWorkoutDialog(self, date_str=date_str, workout=workout)
        if dlg.exec():
            data = dlg.value()
            payload = {**data, "modified_by": "user"}
            self.db_manager.update_workout(workout["id"], payload)
            self.load_workouts()
            self.refresh_calendar()

    def delete_workout(self, workout_id: int):
        if not self.db_manager:
            return
        self.db_manager.delete_workout(workout_id)
        self.load_workouts()
        self.refresh_calendar()

    def complete_workout_dialog(self, date_str: str, workout: dict):
        if not self.db_manager:
            return
        dlg = CompleteWorkoutDialog(self, date_str=date_str, workout=workout)
        if dlg.exec():
            data = dlg.value()
            self.db_manager.update_workout_completion(workout["id"], data)
            self.load_workouts()
            self.refresh_calendar()

    # --- AI Recalculate Week ---

    def recalculate_week(self):
        if not (self.db_manager and self.current_plan):
            QMessageBox.information(self, "Recalculate", "No plan selected.")
            return

        week_start, week_end = self._current_week_range()
        week_dates = self._dates_in_range(week_start, week_end)

        p = self.current_plan
        ctx = PlanContext(
            id=p["id"],
            name=p.get("name", "Plan"),
            goal_type=(p.get("goal_type") or "general").lower(),
            start_date=p.get("start_date"),
            race_date=p.get("race_date"),
            duration_weeks=int(p.get("duration_weeks") or 12),
            max_days_per_week=int(p.get("max_days_per_week") or 5),
            long_run_day=p.get("long_run_day") or "Sunday",
            weekly_increase_cap=float(p.get("weekly_increase_cap") or 0.10),
            long_run_cap=float(p.get("long_run_cap") or 0.30),
            guardrails_enabled=bool(p.get("guardrails_enabled", True)),
        )

        recent = self._recent_completed_workouts(weeks=3)
        suggestions: List[WorkoutSuggestion] = self._planner.plan_week(ctx, week_dates, recent)

        preview_rows = [{
            "date": s.date,
            "workout_type": s.workout_type,
            "planned_distance": s.planned_distance,
            "description": s.description or "",
        } for s in suggestions]

        dlg = AIRecalcDialog(self, week_dates=week_dates, suggestions=preview_rows)
        if dlg.exec():
            self._apply_week_suggestions(week_dates, suggestions)
            self.load_workouts()
            self.refresh_calendar()

    def _apply_week_suggestions(self, week_dates: List[str], suggestions: List[WorkoutSuggestion]):
        pid = self.current_plan["id"]
        for d in week_dates:
            existing = self.db_manager.get_workouts_on_date(pid, d)
            for w in existing:
                self.db_manager.delete_workout(w["id"])
        for s in suggestions:
            if s.workout_type.lower() == "rest":
                continue
            self.db_manager.create_workout({
                "plan_id": pid,
                "date": s.date,
                "workout_type": s.workout_type,
                "planned_distance": s.planned_distance,
                "planned_intensity": s.planned_intensity,
                "description": s.description,
                "notes": None,
                "modified_by": "ai_recalc",
            })

    def _recent_completed_workouts(self, weeks: int = 3) -> List[Dict]:
        if not (self.db_manager and self.current_plan):
            return []
        today = QDate.currentDate()
        start = today.addDays(-7 * weeks).toString("yyyy-MM-dd")
        end = today.toString("yyyy-MM-dd")
        items = self.db_manager.get_workouts_between_dates(self.current_plan["id"], start, end, current_only=True)
        return [w for w in items if w.get("completed")]

    # --- Status Dashboard ---

    def _current_week_range(self) -> tuple[str, str]:
        d = self.current_date
        idx = d.dayOfWeek() % 7
        start = d.addDays(-idx)
        end = start.addDays(6)
        return start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd")

    def _dates_in_range(self, start_str: str, end_str: str) -> List[str]:
        s = QDate.fromString(start_str, "yyyy-MM-dd")
        e = QDate.fromString(end_str, "yyyy-MM-dd")
        out = []
        cur = s
        while cur <= e:
            out.append(cur.toString("yyyy-MM-dd"))
            cur = cur.addDays(1)
        return out

    def update_status_dashboard(self):
        if not (self.db_manager and self.current_plan and self.status_content):
            return
        week_start, week_end = self._current_week_range()
        workouts = self.db_manager.get_workouts_between_dates(
            self.current_plan["id"], week_start, week_end, current_only=True
        )
        planned = 0.0
        actual = 0.0
        completed_count = 0
        total_count = len(workouts)
        for w in workouts:
            pd = w.get("planned_distance")
            if pd is not None:
                try:
                    planned += float(pd)
                except Exception:
                    pass
            if w.get("completed"):
                completed_count += 1
                ad = w.get("actual_distance")
                use_dist = ad if ad is not None else pd
                if use_dist is not None:
                    try:
                        actual += float(use_dist)
                    except Exception:
                        pass
        pct = (actual / planned * 100.0) if planned > 0 else 0.0
        today_str = QDate.currentDate().toString("yyyy-MM-dd")
        key = self.db_manager.get_next_key_workout(self.current_plan["id"], today_str)
        if key:
            key_when = key.get("date"); key_type = (key.get("workout_type") or "").upper()
            key_dist = key.get("planned_distance")
            key_line = f"Next Key Workout: {key_when} {key_type}" + (f" {float(key_dist):.1f} mi" if key_dist is not None else "")
        else:
            key_line = "Next Key Workout: —"
        if pct >= 85:
            status_emoji, status_text = "🟢", "On Track"
        elif pct >= 60:
            status_emoji, status_text = "🟡", "Getting There"
        else:
            status_emoji, status_text = "🟠", "Needs Attention"
        status = (
            f"{status_emoji} Goal Attainability: {pct:.0f}% ({status_text})\n"
            f"Week Progress ({week_start}…{week_end}): {actual:.1f}/{planned:.1f} miles "
            f"({completed_count}/{total_count} workouts completed)\n"
            f"{key_line}"
        )
        self.status_content.setText(status)

    # --- Status window (UI) ---

    def create_status_window(self) -> QWidget:
        container = QFrame()
        container.setObjectName("statusWindow")
        container.setMaximumHeight(200)

        layout = QVBoxLayout()

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

        self.status_content = QLabel("Loading…")
        self.status_content.setObjectName("statusContent")
        layout.addWidget(self.status_content)

        container.setLayout(layout)
        return container

    # --- Navigation / helpers ---

    def update_month_label(self):
        self.month_label.setText(self.current_date.toString("MMMM yyyy"))

    def previous_month(self):
        self.current_date = self.current_date.addMonths(-1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    def next_month(self):
        self.current_date = self.current_date.addMonths(1)
        self.update_month_label()
        self.load_workouts()
        self.refresh_calendar()

    # --- Styles ---

    def apply_styles(self):
        self.setStyleSheet("""
            QFrame#calendarContainer { background-color: white; border-radius: 12px; padding: 24px; }
            QLabel#monthLabel { font-size: 24px; color: #2c3e50; font-weight: bold; }
            QPushButton#navButton { background-color: transparent; color: #2c3e50; border: 1px solid rgba(44, 62, 80, 0.3);
                                    border-radius: 6px; padding: 8px 12px; font-size: 16px; }
            QPushButton#navButton:hover { background-color: rgba(44, 62, 80, 0.1); }
            QPushButton#actionButton { background-color: white; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 6px; padding: 8px 16px; }
            QPushButton#actionButton:hover { background-color: #ecf0f1; }
            QLabel#weekdayHeader { font-size: 14px; font-weight: 600; color: #7f8c8d; text-transform: uppercase; padding: 10px; }
            QFrame#dayCell { background-color: #f8f9fa; border: 1px solid #ecf0f1; border-radius: 8px; padding: 6px; }
            QFrame#dayCell:hover { background-color: #e8f4f8; border-color: #3498db; }
            QFrame#emptyCell { background-color: transparent; border: none; }
            QLabel#dayNumber { font-size: 16px; color: #2c3e50; font-weight: 600; }
            QLabel#workoutType { font-size: 11px; color: #3498db; font-weight: 600; margin-top: 4px; }
            QLabel#workoutDistance { font-size: 13px; color: #555; margin-top: 2px; }
            QLabel#completedLabel { font-size: 10px; color: #27ae60; margin-top: 4px; }
            QLabel#noWorkout { font-size: 20px; color: #bdc3c7; margin-top: 8px; }
            QFrame#statusWindow { background-color: white; border-top: 3px solid #3498db; padding: 16px 24px; }
            QLabel#statusTitle { font-size: 14px; font-weight: 600; color: #2c3e50; letter-spacing: 0.5px; }
            QLabel#statusContent { font-size: 14px; color: #555; line-height: 1.6; }
            QPushButton#expandButton { background-color: transparent; border: none; font-size: 14px; color: #7f8c8d; padding: 4px; }
        """)
