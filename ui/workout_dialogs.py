"""Workout dialogs: Add/Edit and Complete, with Templates + Manager."""

from __future__ import annotations
from typing import Optional, Dict, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QTextEdit, QDoubleSpinBox,
    QComboBox, QDialogButtonBox, QPushButton, QWidget, QMessageBox, QFormLayout, QSpinBox, QInputDialog
)

from ui.template_manager import TemplateManager


_WORKOUT_TYPES = ["easy", "tempo", "intervals", "long", "recovery", "rest", "crosstrain"]


class AddEditWorkoutDialog(QDialog):
    """
    Add or edit a workout for a specific date.
    Includes template dropdown, Manage Templates, and Save as Template.
    """
    def __init__(self, parent: Optional[QWidget], *, date_str: str, workout: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.setWindowTitle(("Edit" if workout else "Add") + f" Workout – {date_str}")
        self._date = date_str
        self._workout = workout
        self._db = getattr(parent, "db_manager", None)

        root = QVBoxLayout(self)

        # --- Template row ---
        tpl_row = QHBoxLayout()
        tpl_label = QLabel("Template:")
        self.tpl_combo = QComboBox()
        self.manage_btn = QPushButton("Manage…")
        self.manage_btn.clicked.connect(self._open_manager)

        self._load_templates_into_combo()
        self.tpl_combo.currentIndexChanged.connect(self._apply_template_selection)

        tpl_row.addWidget(tpl_label)
        tpl_row.addWidget(self.tpl_combo, 1)
        tpl_row.addWidget(self.manage_btn)
        root.addLayout(tpl_row)

        # --- Form fields ---
        form = QFormLayout()

        self.type_box = QComboBox()
        self.type_box.addItems(_WORKOUT_TYPES)

        self.dist_box = QDoubleSpinBox()
        self.dist_box.setRange(0, 1000)
        self.dist_box.setDecimals(1)
        self.dist_box.setSingleStep(0.5)

        self.intensity_edit = QLineEdit()
        self.desc_edit = QTextEdit()
        self.notes_edit = QTextEdit()

        form.addRow("Type", self.type_box)
        form.addRow("Planned distance (mi)", self.dist_box)
        form.addRow("Planned intensity", self.intensity_edit)
        form.addRow("Description", self.desc_edit)
        form.addRow("Notes", self.notes_edit)

        root.addLayout(form)

        # Buttons row (OK/Cancel + Save as Template…)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)

        self.save_tpl_btn = QPushButton("Save as Template…")
        self.save_tpl_btn.clicked.connect(self._save_as_template)

        b_row = QHBoxLayout()
        b_row.addWidget(self.save_tpl_btn)
        b_row.addStretch()
        b_row.addWidget(btns)
        root.addLayout(b_row)

        self.setMinimumWidth(560)

        # If editing, populate from workout
        if workout:
            self._populate_from_workout(workout)

    # --- Template support ---

    def _load_templates_into_combo(self):
        self.tpl_combo.clear()
        self.tpl_combo.addItem("— Select template —", None)
        if not self._db:
            return
        for tpl in self._db.get_all_templates():
            self.tpl_combo.addItem(tpl["name"], tpl)

    def _apply_template_selection(self, idx: int):
        tpl = self.tpl_combo.currentData()
        if not tpl:
            return
        # If editing an existing workout, confirm overwrite of fields
        if self._workout:
            ok = QMessageBox.question(
                self,
                "Apply template?",
                "Apply this template over the current values?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if ok != QMessageBox.Yes:
                return
        # Fill fields
        wt = (tpl.get("workout_type") or "easy").lower()
        if wt not in _WORKOUT_TYPES:
            wt = "easy"
        self.type_box.setCurrentText(wt)

        pd = tpl.get("planned_distance")
        try:
            self.dist_box.setValue(float(pd) if pd is not None else 0.0)
        except Exception:
            self.dist_box.setValue(0.0)

        self.intensity_edit.setText(tpl.get("planned_intensity") or "")
        self.desc_edit.setPlainText(tpl.get("description") or "")
        self.notes_edit.setPlainText(tpl.get("notes") or "")

    def _save_as_template(self):
        if not self._db:
            QMessageBox.information(self, "Templates", "Database not available.")
            return
        name, ok = QInputDialog.getText(self, "Save as Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        tpl = {
            "name": name,
            "workout_type": self.type_box.currentText(),
            "planned_distance": float(self.dist_box.value()) if self.dist_box.value() > 0 else None,
            "planned_intensity": self.intensity_edit.text().strip() or None,
            "description": self.desc_edit.toPlainText().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
        try:
            self._db.create_template(tpl)
            QMessageBox.information(self, "Templates", f"Saved template “{name}”.")
            self._load_templates_into_combo()
            # Select the saved template
            for i in range(self.tpl_combo.count()):
                if self.tpl_combo.itemText(i) == name:
                    self.tpl_combo.setCurrentIndex(i)
                    break
        except Exception as e:
            QMessageBox.warning(self, "Templates", f"Failed to save template:\n{e}")

    def _open_manager(self):
        if not self._db:
            QMessageBox.information(self, "Templates", "Database not available.")
            return
        dlg = TemplateManager(self, self._db)
        dlg.changed.connect(self._load_templates_into_combo)
        dlg.exec()

    # --- Populate / Extract ---

    def _populate_from_workout(self, w: Dict[str, Any]):
        wt = (w.get("workout_type") or "easy").lower()
        if wt not in _WORKOUT_TYPES:
            wt = "easy"
        self.type_box.setCurrentText(wt)

        pd = w.get("planned_distance")
        try:
            self.dist_box.setValue(float(pd) if pd is not None else 0.0)
        except Exception:
            self.dist_box.setValue(0.0)

        self.intensity_edit.setText(w.get("planned_intensity") or "")
        self.desc_edit.setPlainText(w.get("description") or "")
        self.notes_edit.setPlainText(w.get("notes") or "")

    def value(self) -> Dict[str, Any]:
        return {
            "workout_type": self.type_box.currentText(),
            "planned_distance": float(self.dist_box.value()) if self.dist_box.value() > 0 else None,
            "planned_intensity": self.intensity_edit.text().strip() or None,
            "description": self.desc_edit.toPlainText().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }


class CompleteWorkoutDialog(QDialog):
    """Mark a workout completed with basic metrics."""
    def __init__(self, parent: Optional[Widget], *, date_str: str, workout: Dict[str, Any]):
        super().__init__(parent)
        self.setWindowTitle(f"Complete Workout – {date_str}")
        self._workout = workout

        root = QVBoxLayout(self)
        form = QFormLayout()

        self.actual_distance = QDoubleSpinBox()
        self.actual_distance.setRange(0, 1000)
        self.actual_distance.setDecimals(2)
        self.actual_distance.setSingleStep(0.5)

        self.actual_time_min = QSpinBox()
        self.actual_time_min.setRange(0, 999)
        self.actual_time_sec = QSpinBox()
        self.actual_time_sec.setRange(0, 59)

        self.rpe = QSpinBox()
        self.rpe.setRange(1, 10)

        self.avg_hr = QSpinBox()
        self.avg_hr.setRange(0, 250)

        self.elev_gain = QSpinBox()
        self.elev_gain.setRange(0, 20000)

        self.notes = QTextEdit()

        form.addRow("Actual distance (mi)", self.actual_distance)
        form.addRow("Time (min / sec)", self.actual_time_min)
        form.addRow("", self.actual_time_sec)
        form.addRow("RPE (1-10)", self.rpe)
        form.addRow("Avg HR", self.avg_hr)
        form.addRow("Elevation gain (ft)", self.elev_gain)
        form.addRow("Notes", self.notes)

        root.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.setMinimumWidth(480)

    def value(self) -> Dict[str, Any]:
        mins = int(self.actual_time_min.value())
        secs = int(self.actual_time_sec.value())
        total_secs = mins * 60 + secs
        return {
            "actual_distance": float(self.actual_distance.value()) if self.actual_distance.value() > 0 else None,
            "actual_time_seconds": total_secs if total_secs > 0 else None,
            "actual_rpe": int(self.rpe.value()) if self.rpe.value() > 0 else None,
            "avg_hr": int(self.avg_hr.value()) if self.avg_hr.value() > 0 else None,
            "elevation_gain": int(self.elev_gain.value()) if self.elev_gain.value() > 0 else None,
            "completion_notes": self.notes.toPlainText().strip() or None,
        }
