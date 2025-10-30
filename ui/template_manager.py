"""Template Manager dialog for workout templates."""

from __future__ import annotations
from typing import Optional, Dict

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QWidget, QMessageBox, QInputDialog
)


class TemplateManager(QDialog):
    """Create / rename / delete workout templates."""
    changed = Signal()  # emitted when templates are added/removed/renamed

    def __init__(self, parent: Optional[QWidget], db_manager):
        super().__init__(parent)
        self.setWindowTitle("Template Manager")
        self._db = db_manager

        root = QVBoxLayout(self)

        title = QLabel("<b>Workout Templates</b>")
        root.addWidget(title)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self._rename)
        root.addWidget(self.list, 1)

        btns = QHBoxLayout()
        self.add_btn = QPushButton("New…")
        self.rename_btn = QPushButton("Rename…")
        self.delete_btn = QPushButton("Delete")
        self.close_btn = QPushButton("Close")

        self.add_btn.clicked.connect(self._add)
        self.rename_btn.clicked.connect(self._rename)
        self.delete_btn.clicked.connect(self._delete)
        self.close_btn.clicked.connect(self.accept)

        btns.addWidget(self.add_btn)
        btns.addWidget(self.rename_btn)
        btns.addWidget(self.delete_btn)
        btns.addStretch()
        btns.addWidget(self.close_btn)
        root.addLayout(btns)

        self.setMinimumWidth(520)
        self.reload()

    # --- data ---

    def reload(self):
        self.list.clear()
        for tpl in self._db.get_all_templates():
            it = QListWidgetItem(tpl["name"])
            it.setData(Qt.ItemDataRole.UserRole, tpl)
            self.list.addItem(it)
        self._update_enabled()

    def _current(self) -> Optional[Dict]:
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    def _update_enabled(self):
        has = self.list.currentItem() is not None
        self.rename_btn.setEnabled(has)
        self.delete_btn.setEnabled(has)

    def showEvent(self, e):
        super().showEvent(e)
        self._update_enabled()

    def keyPressEvent(self, e):
        super().keyPressEvent(e)
        self._update_enabled()

    # --- actions ---

    def _add(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        # seed a minimal easy run; user can edit later via Add/Edit dialog
        payload = {
            "name": name,
            "workout_type": "easy",
            "planned_distance": 3.0,
            "planned_intensity": None,
            "description": "Easy run",
            "notes": None,
        }
        try:
            self._db.create_template(payload)
            self.changed.emit()
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Template", f"Could not create template:\n{e}")

    def _rename(self):
        tpl = self._current()
        if not tpl:
            return
        new_name, ok = QInputDialog.getText(self, "Rename Template", "New name:", text=tpl["name"])
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name == tpl["name"]:
            return
        # Upsert by name: fetch details and re-create with new name, then delete old (if different)
        try:
            new_payload = dict(tpl)
            new_payload["name"] = new_name
            new_payload.pop("id", None)
            self._db.create_template(new_payload)  # upsert by name
            # If name was unique, now both exist; delete the old one
            self._db.delete_template(tpl["id"])
            self.changed.emit()
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Template", f"Rename failed:\n{e}")

    def _delete(self):
        tpl = self._current()
        if not tpl:
            return
        confirm = QMessageBox.question(
            self, "Delete Template",
            f"Delete template “{tpl['name']}”?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._db.delete_template(tpl["id"])
            self.changed.emit()
            self.reload()
        except Exception as e:
            QMessageBox.warning(self, "Template", f"Delete failed:\n{e}")
