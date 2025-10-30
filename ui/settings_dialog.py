# ui/settings_dialog.py
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QDialogButtonBox,
    QCheckBox, QHBoxLayout, QLabel, QComboBox, QWidget, QPushButton
)
from PySide6.QtCore import Qt
from typing import Optional

SUPPORTED_MODELS = [
    "gpt-4o-mini",
    "gpt-4.1-mini",
]

class SettingsDialog(QDialog):
    """
    Lets the user paste an OpenAI API key, enable/disable OpenAI,
    and choose a model. Values are persisted via DatabaseManager.app_settings.
    """

    def __init__(self, parent: Optional[QWidget], db_manager):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.db = db_manager

        self.chk_use_openai = QCheckBox("Use OpenAI for weekly planning")
        self.edit_api_key = QLineEdit()
        self.edit_api_key.setEchoMode(QLineEdit.Password)
        self.edit_api_key.setPlaceholderText("sk-... (stored locally in your user DB)")
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(SUPPORTED_MODELS)

        # Load from DB
        use_flag = self.db.get_setting("use_openai") or "0"
        api_key = self.db.get_setting("openai_api_key") or ""
        model = self.db.get_setting("openai_model") or SUPPORTED_MODELS[0]

        self.chk_use_openai.setChecked(use_flag == "1")
        self.edit_api_key.setText(api_key)
        if model in SUPPORTED_MODELS:
            self.cmb_model.setCurrentText(model)

        form = QFormLayout()
        form.addRow(self.chk_use_openai)
        form.addRow("OpenAI API Key:", self.edit_api_key)
        form.addRow("Model:", self.cmb_model)

        hint = QLabel("Tip: you can set OPENAI_API_KEY in your environment; "
                      "the app prefers the saved key here if present.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#666; font-size:12px;")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

        self.setMinimumWidth(480)

    def _on_save(self):
        use_flag = "1" if self.chk_use_openai.isChecked() else "0"
        self.db.set_setting("use_openai", use_flag)

        # Save key only if user typed something (empty = keep/remove)
        key = self.edit_api_key.text().strip()
        if key:
            self.db.set_setting("openai_api_key", key)
        else:
            # allow clearing the key
            self.db.set_setting("openai_api_key", "")

        self.db.set_setting("openai_model", self.cmb_model.currentText())
        self.accept()
