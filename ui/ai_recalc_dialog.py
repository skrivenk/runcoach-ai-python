# ui/ai_recalc_dialog.py
from __future__ import annotations

from typing import List
from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QTableWidget, QTableWidgetItem, QLabel


class AIRecalcDialog(QDialog):
    def __init__(self, parent=None, week_dates: List[str] = None, suggestions: List[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("AI Week Recalculate – Preview")
        self.resize(640, 360)

        layout = QVBoxLayout(self)

        if not week_dates or not suggestions:
            layout.addWidget(QLabel("No suggestions to show."))
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(self.reject)
            btns.accepted.connect(self.accept)
            layout.addWidget(btns)
            return

        table = QTableWidget(7, 4)
        table.setHorizontalHeaderLabels(["Date", "Type", "Distance (mi)", "Description"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)

        for i, (d, s) in enumerate(zip(week_dates, suggestions)):
            table.setItem(i, 0, QTableWidgetItem(d))
            table.setItem(i, 1, QTableWidgetItem(s.get("workout_type", "")))
            dist = s.get("planned_distance")
            table.setItem(i, 2, QTableWidgetItem("" if dist is None else f"{float(dist):.1f}"))
            table.setItem(i, 3, QTableWidgetItem(s.get("description") or ""))

        table.resizeColumnsToContents()
        layout.addWidget(table)

        btns = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        btns.button(QDialogButtonBox.Ok).setText("Apply to Calendar")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
