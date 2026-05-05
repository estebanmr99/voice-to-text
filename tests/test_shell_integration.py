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
    @staticmethod
    def _mock_model_manager():
        from model_manager import Profile

        profile_a = Profile(
            canonical_name="cpu-portable",
            display_name="CPU Portable",
            description="Portable",
            preferred_model="base",
            fallback_order=["small"],
            backend_hint="whisper.cpp",
            shipping_default=True,
        )
        profile_b = Profile(
            canonical_name="cpu-high-accuracy",
            display_name="CPU High Accuracy",
            description="Accurate",
            preferred_model="small",
            fallback_order=["base"],
            backend_hint="whisper.cpp",
        )
        mgr = MagicMock()
        mgr.list_profiles.return_value = [profile_a, profile_b]
        mgr.get_profile.side_effect = lambda canonical: {
            "cpu-portable": profile_a,
            "cpu-high-accuracy": profile_b,
        }[canonical]
        return mgr

    @pytest.fixture
    def shell(self, qapp, mock_user32):
        from shell_integration import ShellIntegration
        from settings_store import SettingsStore

        settings = SettingsStore()
        diag = MagicMock()
        return ShellIntegration(
            settings=settings,
            model_manager=self._mock_model_manager(),
            diagnostics=diag,
        )

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

    def test_tray_has_profile_submenu(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        submenu = None
        for action in menu.actions():
            if action.menu() and action.text() == "Profile":
                submenu = action.menu()
                break
        assert submenu is not None
        labels = [a.text() for a in submenu.actions() if a.text()]
        assert "CPU Portable" in labels
        assert "CPU High Accuracy" in labels

    def test_profile_submenu_checks_current_profile(self, shell, qapp):
        shell._settings.model_profile = "cpu-portable"
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        profile_menu = next(a.menu() for a in menu.actions() if a.text() == "Profile")
        actions = {a.text(): a for a in profile_menu.actions() if a.text()}
        assert actions["CPU Portable"].isChecked()
        assert not actions["CPU High Accuracy"].isChecked()

    def test_profile_selection_emits_signal(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        profile_menu = next(a.menu() for a in menu.actions() if a.text() == "Profile")
        target = next(a for a in profile_menu.actions() if a.text() == "CPU High Accuracy")
        seen = []
        shell.profile_changed.connect(lambda p: seen.append(p))
        target.trigger()
        assert seen == ["cpu-high-accuracy"]

    def test_profile_selection_updates_settings(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        profile_menu = next(a.menu() for a in menu.actions() if a.text() == "Profile")
        target = next(a for a in profile_menu.actions() if a.text() == "CPU High Accuracy")
        target.trigger()
        assert shell._settings.model_profile == "cpu-high-accuracy"

    def test_profile_submenu_skipped_without_model_manager(self, qapp, mock_user32):
        from shell_integration import ShellIntegration
        from settings_store import SettingsStore

        shell = ShellIntegration(settings=SettingsStore(), model_manager=None)
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        assert all(a.text() != "Profile" for a in menu.actions())

    def test_status_panel_shows_profile(self, shell, qapp):
        shell._settings.model_profile = "cpu-portable"
        shell.show_status_panel("idle")
        assert shell._status_label is not None
        assert "CPU Portable" in shell._status_label.text()

    def test_update_profile_tooltip(self, shell, qapp):
        shell.setup_tray()
        shell._settings.model_profile = "cpu-portable"
        shell.update_profile_tooltip("base")
        tip = shell._tray_icon.toolTip()
        assert "cpu-portable" in tip
        assert "base" in tip
