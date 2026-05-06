"""PasteController — universal text pasting into Windows applications.

Uses Win32 clipboard manipulation and SendInput keystroke simulation
to paste transcribed text into the focused application.  Previous
clipboard content is backed up and restored to minimise data exposure.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes
from enum import Enum, auto
from typing import Any

logger = logging.getLogger(__name__)

# Try to import Diagnostics from the sibling module; fall back to a no-op
# logger so the module can be imported in environments where diagnostics.py
# is not on ``sys.path`` yet.
try:
    from diagnostics import Diagnostics
except Exception:  # pragma: no cover
    Diagnostics = None  # type: ignore[misc,assignment]

try:
    import win32clipboard
    import win32con
except Exception:  # pragma: no cover
    win32clipboard = None  # type: ignore[assignment]
    win32con = None  # type: ignore[assignment]

# ------------------------------------------------------------------
# Win32 constants / structures for SendInput
# ------------------------------------------------------------------

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
VK_CONTROL = 0x11
VK_V = 0x56

# ULONG_PTR is not always present in ctypes.wintypes; define it manually.
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("ki", KEYBDINPUT),
    ]


class PasteMode(Enum):
    """Paste strategy."""

    SENDINPUT = auto()
    CLIPBOARD_ONLY = auto()


class PasteController:
    """Paste text into the focused Windows application.

    Parameters
    ----------
    mode:
        ``SENDINPUT`` (default) simulates *Ctrl+V* after placing the
        text on the clipboard.  ``CLIPBOARD_ONLY`` only sets the
        clipboard and leaves the paste gesture to the user.
    diagnostics:
        Optional :class:`Diagnostics` instance for structured event
        logging.  Errors are also emitted via the standard logger.
    """

    def __init__(
        self,
        mode: PasteMode = PasteMode.SENDINPUT,
        diagnostics: "Diagnostics | None" = None,
    ) -> None:
        self.mode = mode
        self._diagnostics = diagnostics

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def paste(self, text: str) -> bool:
        """Paste *text* using the current mode.

        Returns ``True`` on success, ``False`` otherwise.  Never raises.
        """
        if not text:
            self._log_event("paste_empty_text", mode=str(self.mode))
            return True

        if self.mode is PasteMode.SENDINPUT:
            # Retry up to 3 times with increasing delay for clipboard locks
            for attempt in range(3):
                ok = self._paste_sendinput(text)
                if ok:
                    return True
                if attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
            # All SendInput attempts failed — fall back to clipboard-only
            self._log_event("paste_sendinput_fallback", reason="all retries failed")
            return self._paste_clipboard(text)

        return self._paste_clipboard(text)

    # ------------------------------------------------------------------
    # Internal implementations
    # ------------------------------------------------------------------

    def _paste_sendinput(self, text: str) -> bool:
        """Backup → set clipboard → SendInput Ctrl+V → restore."""
        backup = self._backup_clipboard()
        if backup is None:
            return False

        if not self._set_clipboard_text(text):
            self._restore_clipboard(*backup)
            return False

        sent = self._send_ctrl_v()
        time.sleep(0.15)  # allow target app to process paste

        self._restore_clipboard(*backup)
        return sent

    def _paste_clipboard(self, text: str) -> bool:
        """Set clipboard only; user must trigger paste manually."""
        return self._set_clipboard_text(text)

    # ------------------------------------------------------------------
    # Clipboard helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _backup_clipboard() -> tuple[int, Any] | None:
        """Save current clipboard format and data.

        Returns ``(format, data)`` or ``(0, None)`` when the clipboard
        is empty / non-text.  Returns ``None`` on unrecoverable error.
        """
        if win32clipboard is None:
            logger.error("win32clipboard not available")
            return None

        for attempt in range(2):
            try:
                win32clipboard.OpenClipboard()
                fmt = 0
                data: Any = None
                # Prefer Unicode text; fall back to ANSI text
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    fmt = win32con.CF_UNICODETEXT
                    data = win32clipboard.GetClipboardData(fmt)
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                    fmt = win32con.CF_TEXT
                    data = win32clipboard.GetClipboardData(fmt)
                else:
                    fmt = 0
                    data = None
                win32clipboard.CloseClipboard()
                return (fmt, data)
            except Exception as exc:
                logger.warning("Clipboard backup attempt %d failed: %s", attempt + 1, exc)
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
                if attempt == 0:
                    time.sleep(0.1)
                else:
                    return None
        return None  # pragma: no cover

    @staticmethod
    def _restore_clipboard(fmt: int, data: Any) -> bool:
        """Restore previous clipboard content.

        Returns ``True`` on success.
        """
        if win32clipboard is None:
            return False

        for attempt in range(2):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                if fmt and data is not None:
                    win32clipboard.SetClipboardData(fmt, data)
                win32clipboard.CloseClipboard()
                return True
            except Exception as exc:
                logger.warning("Clipboard restore attempt %d failed: %s", attempt + 1, exc)
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
                if attempt == 0:
                    time.sleep(0.1)
        return False

    @staticmethod
    def _set_clipboard_text(text: str) -> bool:
        """Place *text* on the clipboard as ``CF_UNICODETEXT``.

        Returns ``True`` on success.
        """
        if win32clipboard is None:
            logger.error("win32clipboard not available")
            return False

        for attempt in range(2):
            try:
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                return True
            except Exception as exc:
                logger.warning("Clipboard set attempt %d failed: %s", attempt + 1, exc)
                try:
                    win32clipboard.CloseClipboard()
                except Exception:
                    pass
                if attempt == 0:
                    time.sleep(0.1)
        return False

    # ------------------------------------------------------------------
    # SendInput helper
    # ------------------------------------------------------------------

    @staticmethod
    def _send_ctrl_v() -> bool:
        """Simulate *Ctrl+V* via ``SendInput``.

        Returns ``True`` if all four keystroke events were accepted.
        """
        user32 = ctypes.windll.user32

        inputs = (INPUT * 4)(
            INPUT(
                INPUT_KEYBOARD,
                KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0),
            ),
            INPUT(
                INPUT_KEYBOARD,
                KEYBDINPUT(VK_V, 0, 0, 0, 0),
            ),
            INPUT(
                INPUT_KEYBOARD,
                KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, 0),
            ),
            INPUT(
                INPUT_KEYBOARD,
                KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0),
            ),
        )

        n_inputs = len(inputs)
        p_inputs = ctypes.cast(inputs, ctypes.POINTER(INPUT))
        cb_size = ctypes.sizeof(INPUT)
        result = user32.SendInput(n_inputs, p_inputs, cb_size)
        return result == n_inputs

    # ------------------------------------------------------------------
    # Logging helper
    # ------------------------------------------------------------------

    def _log_event(self, name: str, **kwargs: object) -> None:
        """Emit a redacted event via Diagnostics if available."""
        if self._diagnostics is not None:
            try:
                self._diagnostics.event(name, **kwargs)
            except Exception:
                pass
        logger.debug("Event: %s %r", name, kwargs)
