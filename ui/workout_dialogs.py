"""Workout dialogs: Add/Edit planned workouts and Complete workout details."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox, QComboBox, QDoubleSpinBox,
    QLineEdit, QTextEdit, QLabel, QHBoxLayout, QSpinBox, QMessageBox, QWidget
)


# -----------------------------
# Helpers
# -----------------------------

def _parse_hhmmss_to_seconds(text: str) -> Optional[int]:
    """
    Parse a time string "hh:mm:ss" (or "mm:ss", or "ss") into total seconds.
    Returns None if empty; raises ValueError if malformed.
    """
    t = (text or "").strip()
    if not t:
        return None
    parts = t.split(":")
    if len(parts) == 1:
        # seconds
        s = int(parts[0])
        if s < 0:
            raise ValueError
        return s
    elif len(parts) == 2:
        m = int(parts[0])
        s = int(parts[1])
        if m < 0 or not (0 <= s < 60):
            raise ValueError
        return m * 60 + s
    elif len(parts) == 3:
        h = int(parts[0])
        m = int(parts[1])
        s = int(parts[2])
        if h < 0 or not (0 <= m < 60) or not (0 <= s < 60):
            raise ValueError
        return h * 3600 + m * 60 + s
    else:
        raise ValueError


# -----------------------------
# Add / Edit planned workout
# -----------------------------

class AddEditWorkoutDialog(QDialog):
    """
    Dialog for adding or editing a *planned* workout.
    Returns a dict via .value() matching DB fields used by DatabaseManager.update_workout/create_workout:
      - workout_type (str)
      - planned_distance (float or None)
      - planned_intensity (str or None)
      - description (str or None)
      - notes (str or None)
    """

    def __init__(self, parent: Optional[QWidget] = None, *, date_str: str, workout: Optional[dict]):
        super().__init__(parent)
        self.setWindowTitle("Edit Workout" if workout else f"Add Workout – {date_str}")
        self._date_str = date_str
        self._workout = workout or {}

        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Workout type
        self.type_box = QComboBox()
        self.type_box.addItems(["easy", "tempo", "intervals", "long", "rest"])

        # Planned distance
        self.dist_box = QDoubleSpinBox()
        self.dist_box.setDecimals(1)
        self.dist_box.setRange(0.0, 300.0)
        self.dist_box.setSingleStep(0.5)
        self.dist_box.setSpecialValueText("")

        # Planned intensity (free text, e.g., "T pace", "I pace")
        self.intensity_edit = QLineEdit()
        self.intensity_edit.setPlaceholderText("e.g., T pace, I pace")

        # Description / notes
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Description (e.g., 'Progression run' or interval details)")
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Notes")

        # Populate if editing
        if workout:
            wt = (workout.get("workout_type") or "").lower()
            idx = max(0, self.type_box.findText(wt))
            self.type_box.setCurrentIndex(idx)

            pd = workout.get("planned_distance")
            if pd is not None:
                try:
                    self.dist_box.setValue(float(pd))
                except Exception:
                    pass

            self.intensity_edit.setText(workout.get("planned_intensity") or "")
            self.desc_edit.setPlainText(workout.get("description") or "")
            self.notes_edit.setPlainText(workout.get("notes") or "")

        # React to type 'rest' (disable distance/intensity)
        self.type_box.currentTextChanged.connect(self._maybe_disable_fields)
        self._maybe_disable_fields(self.type_box.currentText())

        form.addRow("Type", self.type_box)
        form.addRow("Planned distance (mi)", self.dist_box)
        form.addRow("Planned intensity", self.intensity_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Notes", self.notes_edit)

        layout.addLayout(form)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setMinimumWidth(520)

    def _maybe_disable_fields(self, workout_type: str):
        is_rest = workout_type.lower() == "rest"
        self.dist_box.setEnabled(not is_rest)
        self.intensity_edit.setEnabled(not is_rest)
        self.desc_edit.setEnabled(True)   # description could hold "Rest / cross-train"
        # For rest, distance value should visually be empty (0), but we’ll treat it as None in .value()

    def _on_accept(self):
        # Light validation: if not rest, distance should be > 0
        if self.type_box.currentText().lower() != "rest":
            if float(self.dist_box.value()) <= 0.0:
                QMessageBox.warning(self, "Invalid distance", "Please enter a planned distance greater than 0.")
                return
        self.accept()

    def value(self) -> dict:
        wt = self.type_box.currentText().lower()
        planned_distance = float(self.dist_box.value())
        if wt == "rest":
            planned_distance = None

        planned_intensity = self.intensity_edit.text().strip() or None
        if wt == "rest":
            planned_intensity = None

        desc = self.desc_edit.toPlainText().strip() or ("Rest / cross-train" if wt == "rest" else None)
        notes = self.notes_edit.toPlainText().strip() or None

        return {
            "workout_type": wt,
            "planned_distance": planned_distance,
            "planned_intensity": planned_intensity,
            "description": desc,
            "notes": notes,
        }


# -----------------------------
# Complete workout dialog
# -----------------------------

class CompleteWorkoutDialog(QDialog):
    """
    Dialog for completing a workout.
    Returns a dict via .value() matching DatabaseManager.update_workout_completion:
      - actual_distance (float or None)
      - actual_time_seconds (int or None)  ← parsed from hh:mm:ss
      - actual_rpe (int or None, 1..10)
      - avg_hr (int or None)
      - elevation_gain (int or None)
      - completion_notes (str or None)
    """

    def __init__(self, parent: Optional[QWidget] = None, *, date_str: str, workout: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Mark Completed – {date_str}")
        self._workout = workout or {}

        layout = QVBoxLayout(self)

        # Planned summary
        summary = QLabel(self._planned_summary_text())
        summary.setWordWrap(True)
        layout.addWidget(summary)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Actual distance
        self.actual_dist = QDoubleSpinBox()
        self.actual_dist.setRange(0.0, 500.0)
        self.actual_dist.setDecimals(2)
        self.actual_dist.setSingleStep(0.25)
        self.actual_dist.setSpecialValueText("")
        # Prefill with planned as a convenience (if present)
        try:
            pd = self._workout.get("planned_distance")
            if pd is not None:
                self.actual_dist.setValue(float(pd))
        except Exception:
            pass

        # Actual time (hh:mm:ss)
        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("hh:mm:ss (or mm:ss)")

        # RPE 1..10
        self.rpe_box = QSpinBox()
        self.rpe_box.setRange(1, 10)
        self.rpe_box.setSpecialValueText("")

        # Avg HR
        self.hr_box = QSpinBox()
        self.hr_box.setRange(0, 250)
        self.hr_box.setSpecialValueText("")

        # Elevation gain
        self.elev_box = QSpinBox()
        self.elev_box.setRange(0, 10000)
        self.elev_box.setSpecialValueText("")

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("How did it feel? Conditions? Shoes?")

        form.addRow("Actual distance (mi)", self.actual_dist)
        form.addRow("Time", self.time_edit)
        form.addRow("RPE (1–10)", self.rpe_box)
        form.addRow("Avg HR", self.hr_box)
        form.addRow("Elevation gain (ft)", self.elev_box)
        form.addRow("Notes", self.notes_edit)

        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setMinimumWidth(520)

    def _planned_summary_text(self) -> str:
        wt = (self._workout.get("workout_type") or "").upper()
        pd = self._workout.get("planned_distance")
        if pd is not None:
            try:
                return f"Planned: {wt} – {float(pd):.1f} mi"
            except Exception:
                pass
        return f"Planned: {wt}"

    def _on_accept(self):
        # Validate time format, if provided
        try:
            _ = _parse_hhmmss_to_seconds(self.time_edit.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid time", "Please enter time as hh:mm:ss, mm:ss, or ss.")
            return

        # If distance is 0 and nothing else provided, nudge user
        if (
            float(self.actual_dist.value()) <= 0.0
            and not self.time_edit.text().strip()
            and self.rpe_box.value() == self.rpe_box.minimum()
            and self.hr_box.value() == 0
            and self.elev_box.value() == 0
            and not self.notes_edit.toPlainText().strip()
        ):
            proceed = QMessageBox.question(
                self,
                "No data entered",
                "You’re about to mark this as completed with no data. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if proceed != QMessageBox.Yes:
                return

        self.accept()

    def value(self) -> dict:
        secs = None
        try:
            secs = _parse_hhmmss_to_seconds(self.time_edit.text())
        except Exception:
            secs = None

        actual_distance = float(self.actual_dist.value())
        if actual_distance <= 0:
            actual_distance = None

        actual_rpe = self.rpe_box.value()
        if actual_rpe < self.rpe_box.minimum():
            actual_rpe = None

        avg_hr = self.hr_box.value() or None
        elevation_gain = self.elev_box.value() or None
        notes = self.notes_edit.toPlainText().strip() or None

        return {
            "actual_distance": actual_distance,
            "actual_time_seconds": secs,
            "actual_rpe": actual_rpe,
            "avg_hr": avg_hr,
            "elevation_gain": elevation_gain,
            "completion_notes": notes,
        }
