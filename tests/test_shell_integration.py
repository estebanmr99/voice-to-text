"""Tests for shell_integration.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_user32():
    with patch("shell_integration.ctypes.windll.user32") as mock:
        mock.RegisterHotKey.return_value = 1
        mock.UnregisterHotKey.return_value = 1
        yield mock


class TestShellIntegration:
    @pytest.fixture
    def shell(self, qapp, mock_user32):
        from shell_integration import ShellIntegration
        from settings_store import SettingsStore

        settings = SettingsStore()
        diag = MagicMock()
        return ShellIntegration(settings=settings, diagnostics=diag)

    def test_hotkey_registration(self, shell, mock_user32):
        result = shell.register_hotkeys()
        assert result is True
        assert shell._registered is True
        mock_user32.RegisterHotKey.assert_called_once()

    def test_hotkey_unregistration(self, shell, mock_user32):
        shell.register_hotkeys()
        shell.unregister_hotkeys()
        assert shell._registered is False
        mock_user32.UnregisterHotKey.assert_called_once()

    def test_hotkey_registration_failure(self, shell, mock_user32):
        mock_user32.RegisterHotKey.return_value = 0
        result = shell.register_hotkeys()
        assert result is False

    def test_tray_menu_has_actions(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        actions = [a.text() for a in menu.actions() if a.text()]
        assert "Start Dictation" in actions
        assert "Stop Dictation" in actions
        assert "Settings" in actions
        assert "Exit" in actions

    def test_tray_has_paste_mode_submenu(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        submenu = None
        for action in menu.actions():
            if action.menu() and "Paste Mode" in action.text():
                submenu = action.menu()
                break
        assert submenu is not None
        labels = [a.text() for a in submenu.actions() if a.text()]
        assert "Immediate" in labels
        assert "Confirmation" in labels

    def test_status_panel_position(self, shell, qapp):
        from PySide6.QtCore import Qt
        shell.show_status_panel("idle")
        panel = shell._status_panel
        assert panel is not None
        assert panel.isVisible()
        # Check flags
        flags = panel.windowFlags()
        assert flags & Qt.WindowStaysOnTopHint

    def test_status_panel_auto_hide_ready(self, shell, qapp):
        shell.show_status_panel("ready")
        assert shell._auto_hide_timer is not None
        assert shell._auto_hide_timer.isActive()

    def test_status_panel_colors(self, shell, qapp):
        from shell_integration import ShellIntegration
        assert ShellIntegration._STATUS_COLORS["idle"] == "#4CAF50"
        assert ShellIntegration._STATUS_COLORS["listening"] == "#F44336"
        assert ShellIntegration._STATUS_COLORS["processing"] == "#FF9800"
        assert ShellIntegration._STATUS_COLORS["ready"] == "#4CAF50"
        assert ShellIntegration._STATUS_COLORS["error"] == "#FFC107"

    def test_hotkey_signal_emitted(self, shell):
        received = []
        shell.hotkey_pressed.connect(lambda hid: received.append(hid))
        shell._event_filter.hotkey_pressed.emit(1)
        assert received == [1]

    def test_update_tray_tooltip(self, shell, qapp):
        shell.setup_tray()
        shell.update_tray_tooltip("Testing")
        assert shell._tray_icon.toolTip() == "Testing"

    def test_show_notification(self, shell, qapp):
        shell.setup_tray()
        # Just ensure it doesn't raise
        shell.show_notification("Title", "Message")
