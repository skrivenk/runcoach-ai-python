# ui/plan_wizard.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QDialogButtonBox, QMessageBox, QTimeEdit
)
from PySide6.QtGui import QIntValidator


@dataclass
class GoalPreset:
    duration_weeks: int
    max_days_per_week: int
    long_run_day: str


GOAL_PRESETS = {
    "general":  GoalPreset(duration_weeks=8,  max_days_per_week=4, long_run_day="Sunday"),
    "5k":       GoalPreset(duration_weeks=8,  max_days_per_week=4, long_run_day="Sunday"),
    "10k":      GoalPreset(duration_weeks=10, max_days_per_week=4, long_run_day="Sunday"),
    "half":     GoalPreset(duration_weeks=12, max_days_per_week=5, long_run_day="Sunday"),
    "marathon": GoalPreset(duration_weeks=16, max_days_per_week=5, long_run_day="Sunday"),
}


class PlanWizard(QDialog):
    """
    Simple 3-tab wizard:
      - Basics (name, goal, dates, duration)
      - Constraints (days/week, long run day, caps, guardrails)
      - Baseline (optional seed run)
    Emits: plan_created(dict)
    """
    plan_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Training Plan")
        self.setModal(True)
        self.resize(600, 520)

        self.tabs = QTabWidget(self)
        self._build_basics_tab()
        self._build_constraints_tab()
        self._build_baseline_tab()

        # Dialog buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self._on_accept)

        # Layout
        root = QVBoxLayout(self)
        root.addWidget(self.tabs)
        root.addWidget(self.buttons)

        # Initial validation
        self._apply_goal_preset()
        self._validate_all()

    # ---------- Tabs ----------

    def _build_basics_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Fall Half Marathon 2025")
        self.name_edit.textChanged.connect(self._validate_all)

        # Goal
        self.goal_combo = QComboBox()
        self.goal_combo.addItems(["general", "5k", "10k", "half", "marathon"])
        self.goal_combo.currentIndexChanged.connect(self._apply_goal_preset)

        # Start date
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        self.start_date.dateChanged.connect(self._sync_dates_and_validate)

        # Race date (optional)
        self.race_date = QDateEdit()
        self.race_date.setCalendarPopup(True)
        self.race_date.setSpecialValueText("—")
        self.race_date.setDate(QDate.currentDate().addDays(7))
        self.race_date.dateChanged.connect(self._sync_dates_and_validate)

        # Duration (weeks)
        self.duration_weeks = QSpinBox()
        self.duration_weeks.setRange(1, 52)
        self.duration_weeks.valueChanged.connect(self._validate_all)

        form.addRow("Plan name", self.name_edit)
        form.addRow("Goal type", self.goal_combo)
        form.addRow("Start date", self.start_date)
        form.addRow("Race date (optional)", self.race_date)
        form.addRow("Duration (weeks)", self.duration_weeks)

        self.tabs.addTab(w, "Basics")

    def _build_constraints_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Max days/week
        self.max_days = QSpinBox()
        self.max_days.setRange(1, 7)
        self.max_days.valueChanged.connect(self._validate_all)

        # Long run day
        self.long_day = QComboBox()
        self.long_day.addItems(["Sunday", "Saturday", "Friday", "Thursday", "Wednesday", "Tuesday", "Monday"])

        # Caps
        self.weekly_cap = QDoubleSpinBox()
        self.weekly_cap.setRange(0.00, 1.00)       # 0%..100% (as decimal)
        self.weekly_cap.setDecimals(2)
        self.weekly_cap.setSingleStep(0.05)
        self.weekly_cap.setValue(0.10)

        self.long_cap = QDoubleSpinBox()
        self.long_cap.setRange(0.00, 1.00)
        self.long_cap.setDecimals(2)
        self.long_cap.setSingleStep(0.05)
        self.long_cap.setValue(0.30)

        # Guardrails
        self.guardrails = QCheckBox("Enable guardrails (safety caps & sensible progress) ")
        self.guardrails.setChecked(True)

        form.addRow("Max days per week", self.max_days)
        form.addRow("Long run day", self.long_day)
        form.addRow("Weekly increase cap (0.10 = 10%)", self.weekly_cap)
        form.addRow("Long run cap (0.30 = 30%)", self.long_cap)
        form.addRow("", self.guardrails)

        self.tabs.addTab(w, "Constraints")

    def _build_baseline_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.has_baseline = QCheckBox("I have a recent baseline run")
        self.has_baseline.toggled.connect(self._toggle_baseline_fields)

        self.baseline_distance = QDoubleSpinBox()
        self.baseline_distance.setRange(0, 1000)
        self.baseline_distance.setDecimals(2)
        self.baseline_distance.setSingleStep(0.25)
        self.baseline_distance.setEnabled(False)

        self.baseline_time = QTimeEdit()
        self.baseline_time.setDisplayFormat("HH:mm:ss")
        self.baseline_time.setEnabled(False)

        self.baseline_rpe = QSpinBox()
        self.baseline_rpe.setRange(1, 10)
        self.baseline_rpe.setValue(6)
        self.baseline_rpe.setEnabled(False)

        form.addRow(self.has_baseline)
        form.addRow("Distance (mi)", self.baseline_distance)
        form.addRow("Time (HH:MM:SS)", self.baseline_time)
        form.addRow("RPE (1–10)", self.baseline_rpe)

        hint = QLabel("Tip: Baseline helps the calendar seed early weeks more accurately. You can skip this now.")
        hint.setWordWrap(True)
        form.addRow(hint)

        self.tabs.addTab(w, "Baseline")

    # ---------- Goal preset & validation ----------

    def _apply_goal_preset(self):
        goal = self.goal_combo.currentText().lower()
        preset = GOAL_PRESETS.get(goal, GOAL_PRESETS["general"])
        # Only set if the user hasn't edited or we’re switching goals
        self.duration_weeks.blockSignals(True)
        self.max_days.blockSignals(True)
        self.duration_weeks.setValue(preset.duration_weeks)
        self.max_days.setValue(preset.max_days_per_week)
        self.max_days.blockSignals(False)
        self.duration_weeks.blockSignals(False)

        idx = self.long_day.findText(preset.long_run_day)
        if idx >= 0:
            self.long_day.setCurrentIndex(idx)

        self._validate_all()

    def _sync_dates_and_validate(self):
        # Keep race date >= start date when both set
        sd = self.start_date.date()
        rd = self.race_date.date()
        if rd.isValid() and sd.isValid() and rd < sd:
            # auto-bump race date to start date
            self.race_date.blockSignals(True)
            self.race_date.setDate(sd)
            self.race_date.blockSignals(False)
        self._validate_all()

    def _toggle_baseline_fields(self, enabled: bool):
        self.baseline_distance.setEnabled(enabled)
        self.baseline_time.setEnabled(enabled)
        self.baseline_rpe.setEnabled(enabled)

    def _validate_all(self) -> bool:
        """
        Returns True if all required fields are valid; also updates UI hints.
        """
        errors = []

        # Name
        name = self.name_edit.text().strip()
        if not name:
            errors.append("Please enter a plan name.")

        # Dates
        sd = self.start_date.date()
        rd = self.race_date.date()
        if not sd.isValid():
            errors.append("Start date is invalid.")
        if rd.isValid() and rd < sd:
            errors.append("Race date must be on/after the start date.")

        # Duration
        if self.duration_weeks.value() <= 0:
            errors.append("Duration must be at least 1 week.")

        # Max days/week
        if not (1 <= self.max_days.value() <= 7):
            errors.append("Max days per week must be between 1 and 7.")

        # Caps
        if not (0.0 <= self.weekly_cap.value() <= 1.0):
            errors.append("Weekly increase cap must be between 0.00 and 1.00.")
        if not (0.0 <= self.long_cap.value() <= 1.0):
            errors.append("Long run cap must be between 0.00 and 1.00.")

        # Baseline (if enabled)
        if self.has_baseline.isChecked():
            if self.baseline_distance.value() <= 0:
                errors.append("Baseline distance must be > 0 if baseline is enabled.")
            # time can be 00:00:00 but warn if both are zero
            t = self._time_to_seconds(self.baseline_time.time())
            if t <= 0:
                errors.append("Baseline time must be > 0 if baseline is enabled.")

        # Enable/disable OK button
        ok_btn = self.buttons.button(QDialogButtonBox.Ok)
        ok_btn.setEnabled(len(errors) == 0)
        return len(errors) == 0

    @staticmethod
    def _time_to_seconds(t) -> int:
        return t.hour() * 3600 + t.minute() * 60 + t.second()

    # ---------- Accept / Emit ----------

    def _on_accept(self):
        if not self._validate_all():
            QMessageBox.warning(self, "Fix issues", "Please correct the highlighted issues and try again.")
            # keep user on the faulty tab if we wanted; for now, just block accept
            return

        data = self._collect_payload()
        self.plan_created.emit(data)
        self.accept()

    def _collect_payload(self) -> dict:
        """
        Build the plan payload + baseline keys exactly as MainWindow.on_plan_created expects.
        """
        name = self.name_edit.text().strip()
        goal = self.goal_combo.currentText().lower()

        sd: QDate = self.start_date.date()
        start_str = sd.toString("yyyy-MM-dd")

        rd: QDate = self.race_date.date()
        race_str = rd.toString("yyyy-MM-dd") if rd.isValid() else None

        payload = {
            "name": name,
            "goal_type": goal,
            "start_date": start_str,
            "race_date": race_str,
            "duration_weeks": int(self.duration_weeks.value()),
            "max_days_per_week": int(self.max_days.value()),
            "long_run_day": self.long_day.currentText(),
            "weekly_increase_cap": float(self.weekly_cap.value()),
            "long_run_cap": float(self.long_cap.value()),
            "guardrails_enabled": bool(self.guardrails.isChecked()),
        }

        # Optional baseline used by on_plan_created; include even if None for simplicity
        if self.has_baseline.isChecked():
            payload["baseline_distance"] = float(self.baseline_distance.value())
            payload["baseline_time"] = int(self._time_to_seconds(self.baseline_time.time()))
            payload["baseline_rpe"] = int(self.baseline_rpe.value())
        else:
            payload["baseline_distance"] = None
            payload["baseline_time"] = None
            payload["baseline_rpe"] = None

        return payload
