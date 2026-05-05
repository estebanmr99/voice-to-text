"""Offline confirmation dialog for edit-before-paste flow."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ConfirmationDialog(QDialog):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Confirm Dictation")
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint | Qt.WindowTitleHint
        )
        self.setModal(True)
        self.setMinimumSize(400, 200)

        layout = QVBoxLayout(self)
        header = QLabel("Review your dictation before pasting:", self)
        layout.addWidget(header)

        self._text_edit = QTextEdit(self)
        self._text_edit.setPlaceholderText("No text was recognized.")
        self._text_edit.setWordWrapMode(self._text_edit.wordWrapMode())
        self._text_edit.setPlainText(text)
        layout.addWidget(self._text_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button is not None:
            ok_button.setText("Accept")
            ok_button.setDefault(True)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def text(self) -> str:
        return self._text_edit.toPlainText()

    def set_text(self, text: str) -> None:
        self._text_edit.setPlainText(text)

    @staticmethod
    def show_confirmation(parent: QWidget | None, text: str) -> tuple[bool, str]:
        """Open modal dialog and return (accepted, edited_text)."""
        dialog = ConfirmationDialog(text, parent)
        result = dialog.exec()
        return (result == QDialog.Accepted, dialog.text())
