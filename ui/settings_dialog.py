# ui/settings_dialog.py
from __future__ import annotations

from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QHBoxLayout, QPushButton, QDialogButtonBox, QLabel
)


class SettingsDialog(QDialog):
    """
    App settings:
      - Planner engine: Heuristic (offline) or OpenAI
      - OpenAI API Key (stored in app_settings)
    """
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 260)

        self.db = db_manager

        # UI
        root = QVBoxLayout(self)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.engine = QComboBox()
        self.engine.addItems(["Heuristic (offline)", "OpenAI"])
        self.engine.currentIndexChanged.connect(self._engine_changed)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("sk-...")

        # Show/Hide key button
        sh_layout = QHBoxLayout()
        sh_layout.setSpacing(8)
        sh_layout.addWidget(self.api_key, 1)
        self.toggle_btn = QPushButton("Show")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._toggle_echo)
        sh_layout.addWidget(self.toggle_btn, 0, Qt.AlignRight)

        form.addRow("Planner engine", self.engine)
        form.addRow("OpenAI API key", sh_layout)

        hint = QLabel("Note: OpenAI mode requires a valid API key and the 'openai' package installed.\n"
                      "Your key is stored locally in the app database (app_settings).")
        hint.setWordWrap(True)

        root.addLayout(form)
        root.addWidget(hint)

        btns = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

        self._load_settings()
        self._engine_changed(self.engine.currentIndex())

    # --- internal ---

    def _toggle_echo(self, checked: bool):
        self.api_key.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        self.toggle_btn.setText("Hide" if checked else "Show")

    def _engine_changed(self, idx: int):
        use_openai = (idx == 1)
        self.api_key.setEnabled(use_openai)

    def _load_settings(self):
        # planner_mode ∈ {"heuristic", "openai"}
        mode = (self.db.get_setting("planner_mode") or "heuristic").lower() if self.db else "heuristic"
        key = self.db.get_setting("openai_api_key") if self.db else None

        self.engine.setCurrentIndex(1 if mode == "openai" else 0)
        if key:
            self.api_key.setText(key)

    def _save(self):
        if not self.db:
            self.reject()
            return

        mode = "openai" if self.engine.currentIndex() == 1 else "heuristic"
        key = self.api_key.text().strip() or None

        self.db.set_setting("planner_mode", mode)
        if key is not None:
            self.db.set_setting("openai_api_key", key)
        else:
            # Optional: clear stored key by setting empty
            self.db.set_setting("openai_api_key", "")

        self.accept()
