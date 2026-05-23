"""Tests for shell_integration.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_pynput():
    """Mock pynput.keyboard.GlobalHotKeys for hotkey tests."""
    mock_listener = MagicMock()
    mock_listener.daemon = True
    with patch("shell_integration.pynput_keyboard") as mock_kb:
        mock_kb.GlobalHotKeys.return_value = mock_listener
        yield mock_kb


# Legacy fixture kept for compatibility with tests that reference it
@pytest.fixture
def mock_user32():
    with patch("shell_integration.pynput_keyboard") as mock_kb:
        mock_listener = MagicMock()
        mock_listener.daemon = True
        mock_kb.GlobalHotKeys.return_value = mock_listener
        yield mock_kb


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
        shell._settings.hotkey_toggle = "Ctrl+Shift+D"
        shell._settings.hotkey_push_to_talk = "Ctrl+Alt+D"
        result = shell.register_hotkeys()
        assert result is True
        assert shell._registered is True
        # pynput GlobalHotKeys should be created with a dict of hotkeys
        assert mock_user32.GlobalHotKeys.called

    def test_hotkey_unregistration(self, shell, mock_user32):
        shell.register_hotkeys()
        shell.unregister_hotkeys()
        assert shell._registered is False

    def test_hotkey_registration_failure(self, shell, mock_user32):
        shell._settings.hotkey_toggle = "Ctrl+Shift+D"
        shell._settings.hotkey_push_to_talk = "Ctrl+Alt+D"
        mock_user32.GlobalHotKeys.side_effect = Exception("test error")
        result = shell.register_hotkeys()
        assert result is False

    def test_hotkey_registration_uses_saved_settings(self, shell, mock_user32):
        shell._settings.hotkey_toggle = "Ctrl+Shift+G"
        shell._settings.hotkey_push_to_talk = "Ctrl+Alt+F"

        shell.register_hotkeys()

        call_args = mock_user32.GlobalHotKeys.call_args[0][0]
        assert "<ctrl>+<shift>+g" in call_args
        assert "<ctrl>+<alt>+f" not in call_args
        assert mock_user32.Listener.called

    def test_duplicate_hotkeys_keep_ptt_and_add_fallback_toggle(self, shell, mock_user32):
        shell._settings.hotkey_toggle = "Ctrl+Alt+F"
        shell._settings.hotkey_push_to_talk = "Ctrl+Alt+F"

        shell.register_hotkeys()

        # Same combo cannot mean both toggle and PTT. PTT keeps the configured
        # combo; toggle gets a safe fallback so both modes remain reachable.
        call_args = mock_user32.GlobalHotKeys.call_args[0][0]
        assert "<ctrl>+<shift>+d" in call_args
        assert "<ctrl>+<alt>+f" not in call_args
        assert mock_user32.Listener.called

    def test_tray_menu_has_actions(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        actions = [a.text().replace("&", "") for a in menu.actions() if a.text()]
        assert "Start Dictation" in actions
        assert "Stop Dictation" in actions
        assert "Settings" in actions
        assert "Show Status Panel" in actions
        assert "Exit" in actions

    def test_tray_menu_has_grouped_sections(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        actions = [a.text().replace("&", "") for a in menu.actions() if a.text()]
        assert "Dictation" in actions
        assert "Mode" in actions
        assert "Profile" in actions
        assert "Tools" in actions
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
        assert flags & Qt.WindowDoesNotAcceptFocus

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
        # Simulate pynput callback firing
        shell.hotkey_pressed.emit(1)
        assert received == [1]

    def test_ptt_listener_emits_press_and_release(self, shell, mock_user32):
        class FakeHotKey:
            def __init__(self, keys, on_activate):
                self.keys = set(keys)
                self.on_activate = on_activate
                self.held = set()
                self.active = False

            @staticmethod
            def parse(_hotkey):
                return {"ctrl", "alt", "d"}

            def press(self, key):
                self.held.add(key)
                if not self.active and self.keys.issubset(self.held):
                    self.active = True
                    self.on_activate()

            def release(self, key):
                self.held.discard(key)
                if not self.keys.issubset(self.held):
                    self.active = False

        class FakeListener:
            def __init__(self, on_press, on_release):
                self.on_press = on_press
                self.on_release = on_release
                self.daemon = False
                self.started = False

            def canonical(self, key):
                return key

            def start(self):
                self.started = True

        mock_user32.HotKey = FakeHotKey
        mock_user32.Listener = FakeListener
        seen = []
        shell.ptt_pressed.connect(lambda: seen.append("pressed"))
        shell.ptt_released.connect(lambda: seen.append("released"))

        shell._setup_ptt_listener("<ctrl>+<alt>+d")

        listener = shell._ptt_listener
        assert listener is not None
        listener.on_press("ctrl")
        listener.on_press("alt")
        listener.on_press("d")
        listener.on_release("d")

        assert seen == ["pressed", "released"]

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
        profile_menu = next(a.menu() for a in menu.actions() if a.menu() and a.text() == "Profile")
        actions = {a.text(): a for a in profile_menu.actions() if a.text()}
        assert actions["CPU Portable"].isChecked()
        assert not actions["CPU High Accuracy"].isChecked()

    def test_profile_selection_emits_signal(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        profile_menu = next(a.menu() for a in menu.actions() if a.menu() and a.text() == "Profile")
        target = next(a for a in profile_menu.actions() if a.text() == "CPU High Accuracy")
        seen = []
        shell.profile_changed.connect(lambda p: seen.append(p))
        target.trigger()
        assert seen == ["cpu-high-accuracy"]

    def test_profile_selection_updates_settings(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        profile_menu = next(a.menu() for a in menu.actions() if a.menu() and a.text() == "Profile")
        target = next(a for a in profile_menu.actions() if a.text() == "CPU High Accuracy")
        target.trigger()
        assert shell._settings.model_profile == "cpu-high-accuracy"

    def test_profile_submenu_skipped_without_model_manager(self, qapp, mock_pynput):
        from shell_integration import ShellIntegration
        from settings_store import SettingsStore

        shell = ShellIntegration(settings=SettingsStore(), model_manager=None)
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        assert all(a.text().replace("&", "") != "Profile" for a in menu.actions())

    def test_status_panel_shows_profile(self, shell, qapp):
        shell._settings.model_profile = "cpu-portable"
        shell.show_status_panel("idle")
        assert shell._status_label is not None
        assert "CPU Portable" in shell._status_label.text()

    def test_status_panel_prefers_detail_message(self, shell, qapp):
        shell.show_status_panel("ready", "No speech detected")
        assert shell._status_label is not None
        assert "No speech detected" in shell._status_label.text()

    def test_update_profile_tooltip(self, shell, qapp):
        shell.setup_tray()
        shell._settings.model_profile = "cpu-portable"
        shell.update_profile_tooltip("base")
        tip = shell._tray_icon.toolTip()
        assert "cpu-portable" in tip
        assert "base" in tip

    def test_start_disabled_while_listening(self, shell, qapp):
        shell.setup_tray()
        shell.update_action_state("listening")
        assert shell._action_start is not None and not shell._action_start.isEnabled()
        assert shell._action_stop is not None and shell._action_stop.isEnabled()

    def test_stop_disabled_while_idle(self, shell, qapp):
        shell.setup_tray()
        shell.update_action_state("idle")
        assert shell._action_start is not None and shell._action_start.isEnabled()
        assert shell._action_stop is not None and not shell._action_stop.isEnabled()

    def test_start_enabled_after_ready(self, shell, qapp):
        shell.setup_tray()
        shell.update_action_state("ready")
        assert shell._action_start is not None and shell._action_start.isEnabled()
        assert shell._action_stop is not None and not shell._action_stop.isEnabled()

    def test_show_status_panel_action_exists(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        labels = [a.text().replace("&", "") for a in menu.actions() if a.text()]
        assert "Show Status Panel" in labels

    def test_show_status_panel_action_shows_panel(self, shell, qapp):
        tray = shell.setup_tray()
        menu = tray.contextMenu()
        action = next(a for a in menu.actions() if a.text().replace("&", "") == "Show Status Panel")
        action.trigger()
        assert shell._status_panel is not None and shell._status_panel.isVisible()

    def test_status_panel_close_button_hides(self, shell, qapp):
        from PySide6.QtWidgets import QPushButton

        shell.show_status_panel("idle")
        panel = shell._status_panel
        assert panel is not None
        close_btn = panel.findChild(QPushButton)
        assert close_btn is not None
        close_btn.click()
        assert not panel.isVisible()

    def test_status_panel_shows_profile_name(self, shell, qapp):
        shell._settings.model_profile = "cpu-portable"
        shell.show_status_panel("idle")
        assert shell._status_label is not None
        assert "CPU Portable" in shell._status_label.text()

    def test_status_panel_size_increased(self, shell, qapp):
        shell.show_status_panel("idle")
        panel = shell._status_panel
        assert panel is not None
        assert panel.width() >= 200
        assert panel.height() >= 50

    def test_double_click_tray_shows_panel(self, shell, qapp):
        from PySide6.QtWidgets import QSystemTrayIcon

        shell.setup_tray()
        shell._on_tray_activated(QSystemTrayIcon.DoubleClick)
        assert shell._status_panel is not None
        assert shell._status_panel.isVisible()
