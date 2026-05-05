"""Tests for confirmation_dialog.py."""

from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QDialog, QTextEdit


def test_dialog_construction(qapp):
    from confirmation_dialog import ConfirmationDialog

    dialog = ConfirmationDialog("hello world")
    assert dialog.windowTitle() == "Confirm Dictation"
    assert dialog.text() == "hello world"


def test_text_accessor_after_edit(qapp):
    from confirmation_dialog import ConfirmationDialog

    dialog = ConfirmationDialog("initial")
    dialog.set_text("edited text")
    assert dialog.text() == "edited text"


def test_show_confirmation_accept(qapp):
    from confirmation_dialog import ConfirmationDialog

    with patch.object(ConfirmationDialog, "exec", return_value=QDialog.Accepted):
        accepted, text = ConfirmationDialog.show_confirmation(None, "hello")
    assert accepted is True
    assert text == "hello"


def test_show_confirmation_cancel(qapp):
    from confirmation_dialog import ConfirmationDialog

    with patch.object(ConfirmationDialog, "exec", return_value=QDialog.Rejected):
        accepted, text = ConfirmationDialog.show_confirmation(None, "hello")
    assert accepted is False
    assert text == "hello"


def test_dialog_has_text_edit(qapp):
    from confirmation_dialog import ConfirmationDialog

    dialog = ConfirmationDialog("x")
    assert dialog.findChild(QTextEdit) is not None
