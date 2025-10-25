"""Day Workouts Manager dialog.

Shows all workouts for a given date; lets you add, edit, complete, or delete.
Integrates with DatabaseManager and the Add/Edit/Complete dialogs you already have.
"""

from __future__ import annotations
from typing import List, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QWidget, QMessageBox
)

from ui.workout_dialogs import AddEditWorkoutDialog, CompleteWorkoutDialog


def _workout_title(w: Dict) -> str:
    wt = (w.get("workout_type") or "").upper()
    pd = w.get("planned_distance")
    dist = f"{float(pd):.1f} mi" if pd is not None else "—"
    done = "✓ " if w.get("completed") else ""
    return f"{done}{wt} · {dist}"


def _workout_subtitle(w: Dict) -> str:
    desc = w.get("description") or ""
    return desc


class DayWorkoutsDialog(QDialog):
    """Dialog to manage all workouts for a specific date."""
    # Emitted when anything changes (for parent calendar to reload)
    data_changed = Signal()

    def __init__(self, parent: Optional[QWidget], *, date_str: str, db_manager, plan_id: int):
        super().__init__(parent)
        self.setWindowTitle(f"Manage Workouts – {date_str}")
        self._date = date_str
        self._db = db_manager
        self._plan_id = plan_id

        self._workouts: List[Dict] = []

        root = QVBoxLayout(self)

        # Header
        hdr = QLabel(f"<b>{date_str}</b>")
        root.addWidget(hdr)

        # List of workouts
        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._edit_selected)
        root.addWidget(self.list, 1)

        # Buttons row
        btns = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.complete_btn = QPushButton("Mark Completed")
        self.delete_btn = QPushButton("Delete")
        self.close_btn = QPushButton("Close")

        self.add_btn.clicked.connect(self._add)
        self.edit_btn.clicked.connect(self._edit_selected)
        self.complete_btn.clicked.connect(self._complete_selected)
        self.delete_btn.clicked.connect(self._delete_selected)
        self.close_btn.clicked.connect(self.accept)

        btns.addWidget(self.add_btn)
        btns.addWidget(self.edit_btn)
        btns.addWidget(self.complete_btn)
        btns.addWidget(self.delete_btn)
        btns.addStretch()
        btns.addWidget(self.close_btn)

        root.addLayout(btns)

        self.setMinimumWidth(560)
        self.reload()

    # --- Data / UI ---

    def reload(self):
        """Reload workouts for the date and repopulate the list."""
        self._workouts = self._db.get_workouts_on_date(self._plan_id, self._date, current_only=True)
        self.list.clear()
        for w in self._workouts:
            item = QListWidgetItem(_workout_title(w))
            item.setData(Qt.ItemDataRole.UserRole, w)
            subtitle = _workout_subtitle(w)
            if subtitle:
                item.setToolTip(subtitle)
            self.list.addItem(item)
        self._update_buttons_enabled()

    def _selected_workout(self) -> Optional[Dict]:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _update_buttons_enabled(self):
        has_sel = self.list.currentItem() is not None
        self.edit_btn.setEnabled(has_sel)
        self.complete_btn.setEnabled(has_sel)
        self.delete_btn.setEnabled(has_sel)

    # --- Actions ---

    def _add(self):
        dlg = AddEditWorkoutDialog(self, date_str=self._date, workout=None)
        if dlg.exec():
            data = dlg.value()
            self._db.create_workout({
                "plan_id": self._plan_id,
                "date": self._date,
                "workout_type": data["workout_type"],
                "planned_distance": data["planned_distance"],
                "planned_intensity": data["planned_intensity"],
                "description": data["description"],
                "notes": data["notes"],
                "modified_by": "user",
            })
            self.data_changed.emit()
            self.reload()

    def _edit_selected(self):
        w = self._selected_workout()
        if not w:
            return
        dlg = AddEditWorkoutDialog(self, date_str=self._date, workout=w)
        if dlg.exec():
            data = dlg.value()
            payload = {**data, "modified_by": "user"}
            self._db.update_workout(w["id"], payload)
            self.data_changed.emit()
            self.reload()

    def _complete_selected(self):
        w = self._selected_workout()
        if not w:
            return
        dlg = CompleteWorkoutDialog(self, date_str=self._date, workout=w)
        if dlg.exec():
            data = dlg.value()
            self._db.update_workout_completion(w["id"], data)
            self.data_changed.emit()
            self.reload()

    def _delete_selected(self):
        w = self._selected_workout()
        if not w:
            return
        confirm = QMessageBox.question(
            self,
            "Delete workout",
            "Are you sure you want to delete this workout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self._db.delete_workout(w["id"])
            self.data_changed.emit()
            self.reload()

    # Keep buttons properly enabled as selection changes
    def showEvent(self, e):
        super().showEvent(e)
        self._update_buttons_enabled()

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        if e.key() in (Qt.Key_Up, Qt.Key_Down):
            self._update_buttons_enabled()
