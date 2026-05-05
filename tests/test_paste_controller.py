"""Tests for PasteController."""

import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "src")

from paste_controller import PasteController, PasteMode


class MockWin32Con:
    CF_UNICODETEXT = 13
    CF_TEXT = 1


@pytest.fixture
def mock_clipboard():
    """Provide mocked win32clipboard and win32con for PasteController."""
    mock_wc = MagicMock()
    mock_wc.CF_UNICODETEXT = MockWin32Con.CF_UNICODETEXT
    mock_wc.CF_TEXT = MockWin32Con.CF_TEXT

    mock_wc.IsClipboardFormatAvailable.side_effect = lambda fmt: fmt == MockWin32Con.CF_UNICODETEXT
    mock_wc.GetClipboardData.return_value = "original text"

    mock_wc_module = MagicMock()
    mock_wc_module.OpenClipboard = mock_wc.OpenClipboard
    mock_wc_module.CloseClipboard = mock_wc.CloseClipboard
    mock_wc_module.EmptyClipboard = mock_wc.EmptyClipboard
    mock_wc_module.SetClipboardText = mock_wc.SetClipboardText
    mock_wc_module.SetClipboardData = mock_wc.SetClipboardData
    mock_wc_module.GetClipboardData = mock_wc.GetClipboardData
    mock_wc_module.IsClipboardFormatAvailable = mock_wc.IsClipboardFormatAvailable

    mock_con = MagicMock()
    mock_con.CF_UNICODETEXT = MockWin32Con.CF_UNICODETEXT
    mock_con.CF_TEXT = MockWin32Con.CF_TEXT

    with patch("paste_controller.win32clipboard", mock_wc_module), patch("paste_controller.win32con", mock_con):
        yield mock_wc


@pytest.fixture
def mock_sendinput():
    """Mock SendInput to succeed by default."""
    with patch("paste_controller.ctypes.windll.user32.SendInput") as mock:
        mock.return_value = 4
        yield mock


class TestPasteControllerBackupRestore:
    """Clipboard backup and restore round-trip."""

    def test_backup_returns_format_and_data(self, mock_clipboard):
        fmt, data = PasteController._backup_clipboard()
        assert fmt == MockWin32Con.CF_UNICODETEXT
        assert data == "original text"
        mock_clipboard.OpenClipboard.assert_called_once()

    def test_backup_empty_clipboard(self, mock_clipboard):
        mock_clipboard.IsClipboardFormatAvailable.side_effect = None
        mock_clipboard.IsClipboardFormatAvailable.return_value = False
        fmt, data = PasteController._backup_clipboard()
        assert fmt == 0
        assert data is None

    def test_restore_calls_set_clipboard_data(self, mock_clipboard):
        PasteController._restore_clipboard(MockWin32Con.CF_UNICODETEXT, "restored text")
        mock_clipboard.SetClipboardData.assert_called_once_with(
            MockWin32Con.CF_UNICODETEXT, "restored text"
        )

    def test_restore_empty_does_not_set_data(self, mock_clipboard):
        PasteController._restore_clipboard(0, None)
        mock_clipboard.SetClipboardData.assert_not_called()
        mock_clipboard.EmptyClipboard.assert_called_once()


class TestPasteControllerSendInput:
    """SendInput key sequence and behavior."""

    def test_send_ctrl_v_sequence_order(self, mock_clipboard):
        captured = []

        def capture_sendinput(n_inputs, p_inputs, cb_size):
            for i in range(n_inputs):
                ki = p_inputs[i].ki
                captured.append(
                    {
                        "type": p_inputs[i].type,
                        "wVk": ki.wVk,
                        "dwFlags": ki.dwFlags,
                    }
                )
            return n_inputs

        with patch("paste_controller.time.sleep"), patch(
            "paste_controller.ctypes.windll.user32.SendInput",
            side_effect=capture_sendinput,
        ):
            ctrl = PasteController(mode=PasteMode.SENDINPUT)
            result = ctrl.paste("hello")

        assert result is True
        assert len(captured) == 4
        assert captured[0] == {"type": 1, "wVk": 0x11, "dwFlags": 0}
        assert captured[1] == {"type": 1, "wVk": 0x56, "dwFlags": 0}
        assert captured[2] == {"type": 1, "wVk": 0x56, "dwFlags": 0x0002}
        assert captured[3] == {"type": 1, "wVk": 0x11, "dwFlags": 0x0002}

    def test_fallback_when_sendinput_returns_zero(self, mock_clipboard, mock_sendinput):
        mock_sendinput.return_value = 0
        with patch("paste_controller.time.sleep"):
            ctrl = PasteController(mode=PasteMode.SENDINPUT)
            result = ctrl.paste("hello")

        assert result is True
        assert mock_clipboard.SetClipboardText.call_count == 2

    def test_sendinput_failure_no_infinite_fallback(self, mock_clipboard, mock_sendinput):
        mock_sendinput.return_value = 0
        with patch("paste_controller.time.sleep"):
            ctrl = PasteController(mode=PasteMode.SENDINPUT)
            ctrl.paste("first")  # triggers fallback, _fallback_once becomes True
            result = ctrl.paste("second")  # should not fallback again

        assert result is False


class TestPasteControllerClipboardOnly:
    """CLIPBOARD_ONLY mode."""

    def test_clipboard_only_sets_text(self, mock_clipboard, mock_sendinput):
        ctrl = PasteController(mode=PasteMode.CLIPBOARD_ONLY)
        result = ctrl.paste("hello")
        assert result is True
        mock_clipboard.SetClipboardText.assert_called_with(
            "hello", MockWin32Con.CF_UNICODETEXT
        )
        mock_sendinput.assert_not_called()


class TestPasteControllerEmptyText:
    """Empty text handling."""

    def test_empty_text_returns_true_without_paste(self, mock_clipboard, mock_sendinput):
        ctrl = PasteController(mode=PasteMode.SENDINPUT)
        result = ctrl.paste("")
        assert result is True
        mock_clipboard.OpenClipboard.assert_not_called()
        mock_sendinput.assert_not_called()


class TestPasteControllerClipboardLocked:
    """Clipboard locked error handling with retry."""

    @patch("paste_controller.time.sleep")
    def test_backup_retries_once_then_fails(self, mock_sleep, mock_clipboard):
        mock_clipboard.OpenClipboard.side_effect = [Exception("locked"), Exception("still locked")]
        result = PasteController._backup_clipboard()
        assert result is None
        assert mock_clipboard.OpenClipboard.call_count == 2

    @patch("paste_controller.time.sleep")
    def test_backup_retry_succeeds(self, mock_sleep, mock_clipboard):
        mock_clipboard.OpenClipboard.side_effect = [Exception("locked"), None]
        fmt, data = PasteController._backup_clipboard()
        assert fmt == MockWin32Con.CF_UNICODETEXT
        assert data == "original text"
        assert mock_clipboard.OpenClipboard.call_count == 2

    @patch("paste_controller.time.sleep")
    def test_set_clipboard_retries_once_then_fails(self, mock_sleep, mock_clipboard):
        mock_clipboard.OpenClipboard.side_effect = [Exception("locked"), Exception("still locked")]
        result = PasteController._set_clipboard_text("hello")
        assert result is False
        assert mock_clipboard.OpenClipboard.call_count == 2

    @patch("paste_controller.time.sleep")
    def test_restore_retries_once_then_fails(self, mock_sleep, mock_clipboard):
        mock_clipboard.OpenClipboard.side_effect = [Exception("locked"), Exception("still locked")]
        result = PasteController._restore_clipboard(MockWin32Con.CF_UNICODETEXT, "hello")
        assert result is False
        assert mock_clipboard.OpenClipboard.call_count == 2


class TestPasteControllerNoExceptions:
    """Never raise unhandled exceptions."""

    def test_paste_never_raises(self, mock_clipboard, mock_sendinput):
        mock_clipboard.OpenClipboard.side_effect = Exception("boom")
        with patch("paste_controller.time.sleep"):
            ctrl = PasteController(mode=PasteMode.SENDINPUT)
            result = ctrl.paste("hello")
        assert result is False

    def test_paste_clipboard_only_never_raises(self, mock_clipboard):
        mock_clipboard.OpenClipboard.side_effect = Exception("boom")
        ctrl = PasteController(mode=PasteMode.CLIPBOARD_ONLY)
        result = ctrl.paste("hello")
        assert result is False
