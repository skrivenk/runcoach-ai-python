# ui/workout_dialogs.py
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QDialogButtonBox, QDoubleSpinBox, QComboBox, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt


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
