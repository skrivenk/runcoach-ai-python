# ui/insight_dialog.py
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox, QPushButton, QHBoxLayout
)
from PySide6.QtGui import QClipboard


class InsightDialog(QDialog):
    def __init__(self, parent, insight_text: str, usage: dict | None):
        super().__init__(parent)
        self.setWindowTitle("Weekly Coaching Insight")
        self.setMinimumWidth(520)

        lay = QVBoxLayout(self)
        title = QLabel("Coach’s Note")
        title.setStyleSheet("font-weight: 600; font-size: 16px;")
        lay.addWidget(title)

        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setPlainText(insight_text.strip() or "(No insight)")
        lay.addWidget(self.text)

        if usage:
            usage_lbl = QLabel(self._fmt_usage(usage))
            usage_lbl.setStyleSheet("color:#666; font-size:12px;")
            usage_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lay.addWidget(usage_lbl)

        btns = QDialogButtonBox(QDialogButtonBox.Close, self)
        copy_btn = QPushButton("Copy")
        btns.addButton(copy_btn, QDialogButtonBox.ActionRole)
        copy_btn.clicked.connect(self._copy)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _copy(self):
        cb: QClipboard = self.parent().clipboard() if hasattr(self.parent(), "clipboard") else None
        if cb:
            cb.setText(self.text.toPlainText())
        else:
            # fallback
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(self.text.toPlainText())

    @staticmethod
    def _fmt_usage(u: dict) -> str:
        pt = u.get("prompt_tokens")
        ct = u.get("completion_tokens")
        tt = u.get("total_tokens")
        cost = u.get("estimated_cost_usd")
        model = u.get("model")
        bits = []
        if model:
            bits.append(f"Model: {model}")
        if pt is not None:
            bits.append(f"Prompt: {pt}")
        if ct is not None:
            bits.append(f"Completion: {ct}")
        if tt is not None:
            bits.append(f"Total: {tt}")
        if cost is not None:
            bits.append(f"Est. cost: ${cost:.6f}")
        return " • ".join(bits) if bits else ""
