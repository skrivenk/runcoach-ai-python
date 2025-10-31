# ui/calendar_view.py
"""Calendar View Widget (badges + tooltips + AI Recalculate + Status Dashboard)
Header is outside the scroll area to avoid right-edge clipping.
Now includes Manage Day and Move/Copy actions and status expand/collapse.
"""

from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QScrollArea, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QFrame, QMenu, QMessageBox, QToolButton, QApplication, QStyle
)
from PySide6.QtCore import Qt, QDate, QLocale, QEvent, QTimer
from PySide6.QtGui import QCursor, QFontMetrics

from ui.workout_dialogs import AddEditWorkoutDialog, CompleteWorkoutDialog
from ui.ai_recalc_dialog import AIRecalcDialog
from ui.day_workouts_dialog import DayWorkoutsDialog
from ui.move_copy_dialog import MoveCopyDialog
from services.ai_planner import AIPlanner, PlanContext, WorkoutSuggestion


def _fmt_secs(secs: Optional[int]) -> str:
    if secs is None or secs <= 0:
        return "—"
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:d}:{s:02d}"


class CalendarView(QWidget):
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.current_date = QDate.currentDate()
        self.current_plan = None

        # Track status expand/collapse
        self._status_expanded = True
        self.expand_btn: Optional[QToolButton] = None

        # Map 'YYYY-MM-DD' -> list[workout dict]
        self.workouts: Dict[str, List[Dict]] = {}

        # UI refs
        self.scroll: Optional[QScrollArea] = None
        self.grid_container: Optional[QWidget] = None
        self.grid_layout: Optional[QGridLayout] = None
        self.month_label: Optional[QLabel] = None
        self.recalc_btn: Optional[QPushButton] = None
        self.status_content: Optional[QLabel] = None

        # AI planner
        self._planner = AIPlanner(use_openai=False, api_key=None)

        self.init_ui()

    # --- Planner config from outside (MainWindow) ---

    def configure_planner(self, use_openai: bool, api_key: Optional[str]):
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
        page = QVBoxLayout()
        page.setContentsMargins(16, 16, 16, 16)
        page.setSpacing(12)

        header = self.create_header()
        page.addWidget(header)

        scroller = QScrollArea()
        scroller.setObjectName("calendarScroll")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll = scroller

        scroll_content = QFrame()
        scroll_content.setObjectName("calendarContainer")
        scroll_content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        scroll_v = QVBoxLayout(scroll_content)
        scroll_v.setContentsMargins(12, 0, 12, 0)
        scroll_v.setSpacing(8)

        weekdays = self.create_weekday_headers()
        scroll_v.addWidget(weekdays)

        self.grid_container = QWidget()
        self.grid_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(6)
        for i in range(7):
            self.grid_layout.setColumnStretch(i, 1)
        self.grid_container.setLayout(self.grid_layout)
        scroll_v.addWidget(self.grid_container)

        scroller.setWidget(scroll_content)
        page.addWidget(scroller)

        status = self.create_status_window()
        page.addWidget(status)

        self.setLayout(page)
        self.apply_styles()
        self.refresh_calendar()

    def _compute_month_label_width(self) -> int:
        fm: QFontMetrics = self.fontMetrics()
        locale = QLocale()
        month_names = [locale.monthName(i, QLocale.FormatType.LongFormat) for i in range(1, 13)]
        samples = [f"{mn} 2088" for mn in month_names]
        max_text = max(samples, key=lambda s: fm.horizontalAdvance(s))
        width = fm.horizontalAdvance(max_text) + 24
        return max(240, width)

    def create_header(self) -> QWidget:
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)

        nav_group = QWidget()
        nav_layout = QHBoxLayout(nav_group)
        nav_layout.setSpacing(8)
        nav_layout.setContentsMargins(0, 0, 0, 0)

        prev_btn = QPushButton("◀")
        prev_btn.setObjectName("navButton")
        prev_btn.setCursor(QCursor(Qt.PointingHandCursor))
        prev_btn.clicked.connect(self.previous_month)

        self.month_label = QLabel()
        self.month_label.setObjectName("monthLabel")
        self.month_label.setAlignment(Qt.AlignCenter)
        self.month_label.setFixedWidth(self._compute_month_label_width())
        self.update_month_label()

        next_btn = QPushButton("▶")
        next_btn.setObjectName("navButton")
        next_btn.setCursor(QCursor(Qt.PointingHandCursor))
        next_btn.clicked.connect(self.next_month)

        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(self.month_label)
        nav_layout.addWidget(next_btn)
        nav_group.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        self.recalc_btn = QPushButton("🔄 Recalculate")
        self.recalc_btn.setObjectName("actionButton")
        self.recalc_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.recalc_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.recalc_btn.clicked.connect(self.recalculate_week)

        header_layout.addStretch()
        header_layout.addWidget(nav_group, 0, Qt.AlignCenter)
        header_layout.addStretch()
        header_layout.addWidget(self.recalc_btn, 0, Qt.AlignRight)

        return header

    def create_weekday_headers(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        for day in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
            lbl = QLabel(day)
            lbl.setObjectName("weekdayHeader")
            lbl.setAlignment(Qt.AlignCenter)
            layout.addWidget(lbl)
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
        start_day_of_week = first_day.dayOfWeek() % 7  # Sunday=0

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

    def showEvent(self, event):
        super().showEvent(event)
        # Defer one tick so the viewport reports a stable width
        QTimer.singleShot(0, self._apply_cell_sizes)

    def _viewport_width(self) -> int:
        if self.scroll and self.scroll.viewport():
            vp = self.scroll.viewport()
            w = vp.width()
            # If a vertical scrollbar appears, the reported viewport width is already reduced,
            # but on some platforms/layouts we can still be conservative and subtract a few px.
            sb_w = QApplication.style().pixelMetric(QStyle.PM_ScrollBarExtent)
            # Subtract a tiny cushion to avoid rounding overflow in cell width calc
            return max(600, w - 2)
        return max(600, self.width() - 40)

    def _apply_cell_sizes(self):
        if not self.grid_layout:
            return
        avail_w = self._viewport_width()
        spacing = self.grid_layout.horizontalSpacing() or 0
        cols = 7
        cell_w = max(90, int((avail_w - (spacing * (cols - 1)) - 2) / cols))
        cell_h = max(88, int(cell_w * 0.78))

        for i in range(self.grid_layout.count()):
            w = self.grid_layout.itemAt(i).widget()
            if not w or w.objectName() not in ("dayCell", "emptyCell"):
                continue
            w.setMinimumSize(0, 0)
            w.setMaximumSize(16777215, 16777215)
            w.setFixedSize(cell_w, cell_h)

        self.grid_container.setMinimumWidth(max(avail_w - 2, 0))

    def _compact_header_if_needed(self):
        try:
            vw = self.width()
            if self.recalc_btn:
                if vw < 900 and self.recalc_btn.text() != "🔄":
                    self.recalc_btn.setText("🔄")
                elif vw >= 900 and self.recalc_btn.text() != "🔄 Recalculate":
                    self.recalc_btn.setText("🔄 Recalculate")
        except Exception:
            pass

    # --- Day cells / badges / tooltips ---

    def _build_tooltip_html(self, date_str: str, workouts_for_day: List[Dict]) -> str:
        if not workouts_for_day:
            return f"<b>{date_str}</b><br><i>No workouts</i>"
        rows = []
        for w in workouts_for_day:
            wt = (w.get("workout_type") or "").upper()
            pd = w.get("planned_distance")
            pd_txt = f"{float(pd):.1f} mi" if pd is not None else "—"
            comp = "✓" if w.get("completed") else "—"
            ad = w.get("actual_distance")
            at = w.get("actual_time_seconds")
            ad_txt = f"{float(ad):.1f} mi" if ad is not None else "—"
            at_txt = _fmt_secs(at)
            desc = w.get("description") or ""
            rows.append(
                f"<tr>"
                f"<td style='padding-right:6px;'>{comp}</td>"
                f"<td style='padding-right:10px;'><b>{wt}</b></td>"
                f"<td style='padding-right:10px;'>Planned: {pd_txt}</td>"
                f"<td style='padding-right:10px;'>Actual: {ad_txt} / {at_txt}</td>"
                f"<td style='color:#666'>{desc}</td>"
                f"</tr>"
            )
        table = "<table cellspacing='0' cellpadding='0'>" + "".join(rows) + "</table>"
        return f"<b>{date_str}</b><br>{table}"

    def _make_chip(self, text: str, chip_class: str) -> QLabel:
        chip = QLabel(text)
        chip.setObjectName(chip_class)
        chip.setAlignment(Qt.AlignCenter)
        return chip

    def create_day_cell(self, date: QDate) -> QFrame:
        cell = QFrame()
        cell.setObjectName("dayCell")
        cell.setCursor(QCursor(Qt.PointingHandCursor))
        cell.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        outer = QVBoxLayout()
        outer.setAlignment(Qt.AlignTop)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        day_label = QLabel(str(date.day()))
        day_label.setObjectName("dayNumber")
        top_row.addWidget(day_label)
        top_row.addStretch()

        date_str = date.toString("yyyy-MM-dd")
        workouts_for_day = self.workouts.get(date_str, [])

        any_completed = any(w.get("completed") for w in workouts_for_day)
        if any_completed:
            top_row.addWidget(self._make_chip("✓", "chipDone"))

        if len(workouts_for_day) > 1:
            top_row.addWidget(self._make_chip(f"+{len(workouts_for_day)-1}", "chipMore"))

        outer.addLayout(top_row)

        chips_row = QHBoxLayout()
        chips_row.setSpacing(4)
        if workouts_for_day:
            seen = set()
            for w in workouts_for_day:
                wt = (w.get("workout_type") or "").lower()
                if wt in seen:
                    continue
                seen.add(wt)
                if wt == "easy":
                    chips_row.addWidget(self._make_chip("easy", "chipEasy"))
                elif wt == "tempo":
                    chips_row.addWidget(self._make_chip("tempo", "chipTempo"))
                elif wt == "intervals":
                    chips_row.addWidget(self._make_chip("ints", "chipIntervals"))
                elif wt == "long":
                    chips_row.addWidget(self._make_chip("long", "chipLong"))
                elif wt == "rest":
                    chips_row.addWidget(self._make_chip("rest", "chipRest"))
                if len(seen) >= 2:
                    break
        outer.addLayout(chips_row)

        if workouts_for_day and workouts_for_day[0].get("planned_distance") is not None:
            dist = QLabel(f"{float(workouts_for_day[0]['planned_distance']):.1f} mi")
            dist.setObjectName("workoutDistance")
            outer.addWidget(dist)
        else:
            no_workout = QLabel("—")
            no_workout.setObjectName("noWorkout")
            no_workout.setAlignment(Qt.AlignCenter)
            outer.addWidget(no_workout)

        cell.setLayout(outer)
        cell.setToolTip(self._build_tooltip_html(date_str, workouts_for_day))

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
        act_manage = None
        act_move_copy = None
        if workouts_for_day:
            act_manage = menu.addAction("Manage day…")
            act_move_copy = menu.addAction("Move/Copy…")
            menu.addSeparator()
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

        if act_manage and chosen == act_manage:
            self._open_manage_day(date_str)
            return
        if act_move_copy and chosen == act_move_copy:
            self._move_or_copy_workout(date_str, workouts_for_day[0])
            return

        if chosen == act_add:
            self.add_workout(date_str)
        elif act_edit and chosen == act_edit:
            self.edit_workout(date_str, workouts_for_day[0])
        elif act_complete and chosen == act_complete:
            self.complete_workout_dialog(date_str, workouts_for_day[0])
        elif act_delete and chosen == act_delete:
            self.delete_workout(workouts_for_day[0]["id"])

    def _open_manage_day(self, date_str: str):
        if not (self.db_manager and self.current_plan):
            return
        dlg = DayWorkoutsDialog(self, date_str=date_str, db_manager=self.db_manager, plan_id=self.current_plan["id"])
        dlg.data_changed.connect(lambda: (self.load_workouts(), self.refresh_calendar()))
        dlg.exec()

    def _move_or_copy_workout(self, date_str: str, workout: dict):
        if not (self.db_manager and self.current_plan and workout):
            return
        dlg = MoveCopyDialog(self, current_date_str=date_str)
        if not dlg.exec():
            return
        result = dlg.result_value()
        if not result:
            return
        new_date = result["date"]
        mode = result["mode"]  # 'move' | 'copy'

        if mode == "move":
            self.db_manager.update_workout(workout["id"], {"date": new_date, "modified_by": "reschedule"})
        else:
            payload = {
                "plan_id": self.current_plan["id"],
                "date": new_date,
                "workout_type": workout.get("workout_type"),
                "planned_distance": workout.get("planned_distance"),
                "planned_intensity": workout.get("planned_intensity"),
                "description": workout.get("description"),
                "notes": workout.get("notes"),
                "modified_by": "reschedule-copy",
            }
            self.db_manager.create_workout(payload)

        self.load_workouts()
        self.refresh_calendar()

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

        # Call planner (list) OR (list, usage)
        result = self._planner.plan_week(ctx, week_dates, recent)
        usage = None
        if isinstance(result, tuple) and len(result) == 2:
            suggestions, usage = result
        else:
            suggestions = result  # heuristic path

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

            # Optional: log API usage/cost if available
            if usage and self.db_manager:
                toks = (usage.get("prompt_tokens") or 0) + (usage.get("completion_tokens") or 0)
                self.db_manager.log_api_call(
                    call_type="plan_week",
                    plan_id=self.current_plan["id"],
                    tokens_used=int(toks),
                    cost_usd=usage.get("estimated_cost_usd"),
                )

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

    def refresh_status(self):
        """Public call to refresh the status dashboard; safe to call anytime."""
        self.update_status_dashboard()

    def update_status_dashboard(self):
        if not self.status_content:
            return

        # --- Always show API totals ---
        api_line = ""
        if self.db_manager:
            try:
                totals = self.db_manager.get_api_totals()
                calls = totals.get("calls", 0)
                tokens = totals.get("tokens", 0)
                cost = totals.get("cost", 0.0)
                api_line = f"\nAPI Usage: {calls} calls, ~{tokens} tokens, ~${cost:.4f}"
            except Exception:
                api_line = ""

        # If plan isn't ready yet, still show API usage and a neutral message
        if not (self.db_manager and self.current_plan):
            self.status_content.setText(f"Status: No plan selected.{api_line}")
            return

        # --- Weekly status with plan ---
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
            key_when = key.get("date");
            key_type = (key.get("workout_type") or "").upper()
            key_dist = key.get("planned_distance")
            key_line = f"Next Key Workout: {key_when} {key_type}" + (
                f" {float(key_dist):.1f} mi" if key_dist is not None else "")
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
            f"{key_line}{api_line}"
        )
        self.status_content.setText(status)

    # --- Status window (UI) ---

    def create_status_window(self) -> QWidget:
        container = QFrame()
        container.setObjectName("statusWindow")
        container.setMaximumHeight(200)

        layout = QVBoxLayout(container)
        header = QHBoxLayout()
        title = QLabel("STATUS DASHBOARD")
        title.setObjectName("statusTitle")

        self.expand_btn = QToolButton()
        self.expand_btn.setObjectName("expandButton")
        self.expand_btn.setArrowType(Qt.UpArrow)
        self.expand_btn.setAutoRaise(True)
        self.expand_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.expand_btn.clicked.connect(self._toggle_status_panel)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.expand_btn)
        layout.addLayout(header)

        self.status_content = QLabel("Loading…")
        self.status_content.setObjectName("statusContent")
        self.status_content.setVisible(self._status_expanded)
        layout.addWidget(self.status_content)

        return container

    def _toggle_status_panel(self):
        self._status_expanded = not self._status_expanded
        if self.status_content:
            self.status_content.setVisible(self._status_expanded)
        if self.expand_btn:
            # When collapsed, show Up (click will expand); when expanded, show Down (click will collapse)
            self.expand_btn.setArrowType(Qt.DownArrow if self._status_expanded else Qt.UpArrow)

    # --- Navigation ---

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
            QPushButton#navButton { background-color: transparent; color: #2c3e50; border: 1px solid rgba(44,62,80,.3);
                                    border-radius: 6px; padding: 8px 12px; font-size: 16px; }
            QPushButton#navButton:hover { background-color: rgba(44,62,80,.1); }
            QPushButton#actionButton { background-color: white; color: #2c3e50; border: 1px solid #bdc3c7; border-radius: 6px; padding: 8px 16px; }
            QPushButton#actionButton:hover { background-color: #ecf0f1; }

            QLabel#weekdayHeader { font-size: 14px; font-weight: 600; color: #7f8c8d; text-transform: uppercase; padding: 10px; }

            QToolButton#expandButton { border: none; padding: 2px; margin: 0; }
            QToolButton#expandButton:hover { background: rgba(0,0,0,0.05); border-radius: 6px; }

            QFrame#dayCell { background-color: #f8f9fa; border: 1px solid #ecf0f1; border-radius: 8px; padding: 6px; }
            QFrame#dayCell:hover { background-color: #e8f4f8; border-color: #3498db; }
            QFrame#emptyCell { background-color: transparent; border: none; }

            QLabel#dayNumber { font-size: 16px; color: #2c3e50; font-weight: 600; }
            QLabel#workoutDistance { font-size: 13px; color: #555; margin-top: 2px; }
            QLabel#completedLabel { font-size: 10px; color: #27ae60; margin-top: 4px; }
            QLabel#noWorkout { font-size: 20px; color: #bdc3c7; margin-top: 8px; }

            QLabel#chipDone, QLabel#chipMore, QLabel#chipEasy, QLabel#chipTempo, QLabel#chipIntervals, QLabel#chipLong, QLabel#chipRest {
                border-radius: 10px; padding: 2px 6px; font-size: 11px; font-weight: 600; min-width: 16px;
            }
            QLabel#chipDone { background: #eafaf1; color: #1e824c; border: 1px solid #bfe8cf; }
            QLabel#chipMore { background: #eef2f7; color: #2c3e50; border: 1px solid #d6dde6; }

            QLabel#chipEasy { background: #e8f7ff; color: #0b70b8; border: 1px solid #c5e6ff; }
            QLabel#chipTempo { background: #fff3e6; color: #b45f06; border: 1px solid #ffe0bf; }
            QLabel#chipIntervals { background: #f3e8ff; color: #6a1cb2; border: 1px solid #e3ccff; }
            QLabel#chipLong { background: #eafaf1; color: #1e824c; border: 1px solid #bfe8cf; }
            QLabel#chipRest { background: #f2f2f2; color: #777; border: 1px solid #e0e0e0; }
        """)
