# ui/workout_dialogs.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QComboBox,
    QLineEdit, QTextEdit, QTimeEdit, QSpinBox
)
from PySide6.QtCore import Qt, QTime


class AddEditWorkoutDialog(QDialog):
    """
    One dialog for both add and edit.
    If workout is provided (dict), dialog loads it and returns updated fields.
    Otherwise acts as an Add dialog.
    """
    def __init__(self, parent=None, date_str=None, workout: dict | None = None):
        super().__init__(parent)
        mode = "Edit" if workout else "Add"
        self.setWindowTitle(f"{mode} Workout – {date_str}")
        self.date_str = date_str
        self._workout = workout

        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.type_box = QComboBox()
        self.type_box.addItems(["easy", "tempo", "intervals", "long", "rest"])

        self.dist_box = QDoubleSpinBox()
        self.dist_box.setRange(0, 1000)
        self.dist_box.setDecimals(1)
        self.dist_box.setSingleStep(0.5)

        self.intensity = QLineEdit()
        self.desc = QTextEdit()
        self.notes = QTextEdit()

        # Seed fields for edit
        if workout:
            self.type_box.setCurrentText(workout.get("workout_type", "easy"))
            if workout.get("planned_distance") is not None:
                try:
                    self.dist_box.setValue(float(workout["planned_distance"]))
                except Exception:
                    pass
            if workout.get("planned_intensity"):
                self.intensity.setText(str(workout["planned_intensity"]))
            if workout.get("description"):
                self.desc.setPlainText(workout["description"])
            if workout.get("notes"):
                self.notes.setPlainText(workout["notes"])

        layout.addRow("Type", self.type_box)
        layout.addRow("Planned distance (mi)", self.dist_box)
        layout.addRow("Intensity", self.intensity)
        layout.addRow("Description", self.desc)
        layout.addRow("Notes", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def value(self) -> dict:
        """Return dict of fields to persist (for add or update)."""
        return {
            "workout_type": self.type_box.currentText(),
            "planned_distance": float(self.dist_box.value()),
            "planned_intensity": (self.intensity.text().strip() or None),
            "description": (self.desc.toPlainText().strip() or None),
            "notes": (self.notes.toPlainText().strip() or None),
        }


class CompleteWorkoutDialog(QDialog):
    """
    Dialog to record workout completion metrics.
    Returns a dict ready for DatabaseManager.update_workout_completion().
    """
    def __init__(self, parent=None, date_str: str | None = None, workout: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Complete Workout – {date_str or ''}".strip())

        layout = QFormLayout(self)
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # Actual distance
        self.actual_distance = QDoubleSpinBox()
        self.actual_distance.setRange(0, 1000)
        self.actual_distance.setDecimals(2)
        self.actual_distance.setSingleStep(0.25)
        # Seed from planned if present
        if workout and workout.get("planned_distance") is not None:
            try:
                self.actual_distance.setValue(float(workout["planned_distance"]))
            except Exception:
                pass

        # Duration (hh:mm:ss)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime(0, 45, 0))  # sensible default

        # RPE 1-10
        self.rpe = QSpinBox()
        self.rpe.setRange(1, 10)
        self.rpe.setValue(6)

        # Avg HR
        self.avg_hr = QSpinBox()
        self.avg_hr.setRange(0, 240)
        self.avg_hr.setSpecialValueText("—")
        self.avg_hr.setValue(0)

        # Elevation gain
        self.elev = QSpinBox()
        self.elev.setRange(0, 20000)
        self.elev.setSpecialValueText("—")
        self.elev.setValue(0)

        # Notes
        self.notes = QTextEdit()

        layout.addRow("Actual distance (mi)", self.actual_distance)
        layout.addRow("Duration (HH:MM:SS)", self.time_edit)
        layout.addRow("RPE (1–10)", self.rpe)
        layout.addRow("Avg HR", self.avg_hr)
        layout.addRow("Elevation gain (ft)", self.elev)
        layout.addRow("Notes", self.notes)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    @staticmethod
    def _time_to_seconds(t: QTime) -> int:
        return t.hour() * 3600 + t.minute() * 60 + t.second()

    def value(self) -> dict:
        """Shape matches DatabaseManager.update_workout_completion() expectations."""
        t = self._time_to_seconds(self.time_edit.time())
        avg_hr_val = None if self.avg_hr.value() == 0 else int(self.avg_hr.value())
        elev_val = None if self.elev.value() == 0 else int(self.elev.value())
        notes_val = self.notes.toPlainText().strip() or None
        return {
            "actual_distance": float(self.actual_distance.value()),
            "actual_time_seconds": t,
            "actual_rpe": int(self.rpe.value()),
            "avg_hr": avg_hr_val,
            "elevation_gain": elev_val,
            "completion_notes": notes_val,
        }
