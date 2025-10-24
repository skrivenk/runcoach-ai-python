"""Move/Copy Workout dialog with a date picker."""

from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox,
    QCalendarWidget, QRadioButton, QButtonGroup
)


class MoveCopyDialog(QDialog):
    """
    Lets the user pick a new date and choose Move or Copy.
    Use .result_value() to get {"mode": "move"|"copy", "date": "YYYY-MM-DD"} or None if cancelled.
    """
    def __init__(self, parent=None, *, current_date_str: str):
        super().__init__(parent)
        self.setWindowTitle("Reschedule Workout")
        self._current_date = QDate.fromString(current_date_str, "yyyy-MM-dd")

        root = QVBoxLayout(self)

        info = QLabel("Choose a new date and whether to Move or Copy this workout.")
        root.addWidget(info)

        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        if self._current_date.isValid():
            self.calendar.setSelectedDate(self._current_date)
        root.addWidget(self.calendar)

        # Mode selection
        row = QHBoxLayout()
        row.addWidget(QLabel("Action:"))
        self.btn_move = QRadioButton("Move")
        self.btn_copy = QRadioButton("Copy")
        self.btn_move.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.btn_move)
        group.addButton(self.btn_copy)
        row.addWidget(self.btn_move)
        row.addWidget(self.btn_copy)
        row.addStretch()
        root.addLayout(row)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self.setMinimumWidth(420)

    def result_value(self) -> Optional[dict]:
        if self.result() != QDialog.Accepted:
            return None
        new_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        mode = "copy" if self.btn_copy.isChecked() else "move"
        return {"mode": mode, "date": new_date}
