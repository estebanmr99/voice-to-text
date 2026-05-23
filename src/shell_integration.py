"""Shell integration — global hotkey, system tray, and floating status panel.

Uses pynput low-level keyboard hooks for global hotkey detection,
system tray integration via Qt, and a floating status panel.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QTimer, QSize
from PySide6.QtGui import QAction, QActionGroup, QCursor, QIcon, QPixmap, QColor, QPainter, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from settings_dialog import SettingsDialog

try:
    from pynput import keyboard as pynput_keyboard
except ImportError:  # pragma: no cover
    pynput_keyboard = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from model_manager import ModelManager
    from settings_store import SettingsStore
    from diagnostics import Diagnostics
    from glossary import GlossaryStore

logger = logging.getLogger(__name__)

# Mapping from user-friendly key names to pynput hotkey format
_PYNPUT_MODIFIER_MAP = {
    "CTRL": "<ctrl>",
    "ALT": "<alt>",
    "SHIFT": "<shift>",
    "WIN": "<cmd>",
}

_PYNPUT_SPECIAL_KEY_MAP = {
    "SPACE": "<space>",
    "ENTER": "<enter>",
    "RETURN": "<enter>",
    "TAB": "<tab>",
    "ESC": "<esc>",
    "ESCAPE": "<esc>",
    "F1": "<f1>", "F2": "<f2>", "F3": "<f3>", "F4": "<f4>",
    "F5": "<f5>", "F6": "<f6>", "F7": "<f7>", "F8": "<f8>",
    "F9": "<f9>", "F10": "<f10>", "F11": "<f11>", "F12": "<f12>",
    "INSERT": "<insert>", "DELETE": "<delete>",
    "HOME": "<home>", "END": "<end>",
    "PAGEUP": "<page_up>", "PAGEDOWN": "<page_down>",
    "UP": "<up>", "DOWN": "<down>", "LEFT": "<left>", "RIGHT": "<right>",
}

# Legacy Win32 constants (kept for _parse_hotkey compatibility with tests)
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
_MODIFIER_MAP = {
    "ALT": MOD_ALT,
    "CTRL": MOD_CONTROL,
    "SHIFT": MOD_SHIFT,
    "WIN": MOD_WIN,
}
_VK_MAP = {
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "SPACE": 0x20, "ENTER": 0x0D, "RETURN": 0x0D,
    "TAB": 0x09, "ESC": 0x1B, "ESCAPE": 0x1B,
    "INSERT": 0x2D, "DELETE": 0x2E, "HOME": 0x24, "END": 0x23,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
}


def _hotkey_to_pynput_format(hotkey_str: str) -> str | None:
    """Convert 'Ctrl+Shift+D' format to pynput '<ctrl>+<shift>+d' format."""
    tokens = [t.strip() for t in hotkey_str.split("+") if t.strip()]
    if len(tokens) < 2:
        return None

    key_token = tokens[-1].upper()
    modifier_tokens = [t.upper() for t in tokens[:-1]]

    pynput_parts = []
    for mod in modifier_tokens:
        pynput_mod = _PYNPUT_MODIFIER_MAP.get(mod)
        if pynput_mod is None:
            return None
        pynput_parts.append(pynput_mod)

    # Map the key
    special = _PYNPUT_SPECIAL_KEY_MAP.get(key_token)
    if special:
        pynput_parts.append(special)
    elif len(key_token) == 1 and key_token.isalnum():
        pynput_parts.append(key_token.lower())
    else:
        return None

    return "+".join(pynput_parts)


class ShellIntegration(QObject):
    """Global hotkey, tray icon, and floating status panel.

    Signals
    -------
    hotkey_pressed(hotkey_id: int)
        Emitted when the registered global hotkey is pressed.
    status_changed(status: str)
        Emitted when the visual status changes.
    """

    hotkey_pressed = Signal(int)
    ptt_pressed = Signal()
    ptt_released = Signal()
    status_changed = Signal(str)
    profile_changed = Signal(str)
    settings_updated = Signal()

    # Status color mapping
    _STATUS_COLORS: dict[str, str] = {
        "idle": "#4CAF50",      # green
        "listening": "#F44336",  # red
        "processing": "#FF9800", # yellow
        "ready": "#4CAF50",      # green check
        "error": "#FFC107",      # warning
    }

    # Cloud mode color mapping (blue theme)
    _CLOUD_STATUS_COLORS: dict[str, str] = {
        "idle": "#1565C0",      # blue
        "listening": "#E65100",  # deep orange
        "processing": "#F9A825", # amber
        "ready": "#1976D2",      # blue
        "error": "#C62828",      # dark red
    }

    _STATUS_LABELS: dict[str, str] = {
        "idle": "Idle",
        "listening": "Listening...",
        "processing": "Processing...",
        "ready": "Ready",
        "error": "Error",
    }

    def __init__(
        self,
        settings: "SettingsStore",
        model_manager: "ModelManager | None" = None,
        diagnostics: "Diagnostics | None" = None,
        glossary_store: "GlossaryStore | None" = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._model_manager = model_manager
        self._diagnostics = diagnostics
        self._glossary_store = glossary_store
        self._hotkey_ids = {
            "toggle": 1,
            "push_to_talk": 2,
        }
        self._registered_hotkeys: dict[int, str] = {}
        self._registered = False
        self._app = QApplication.instance()

        self._tray_icon: QSystemTrayIcon | None = None
        self._status_panel: QWidget | None = None
        self._status_label: QLabel | None = None
        self._auto_hide_timer: QTimer | None = None
        self._action_start: QAction | None = None
        self._action_stop: QAction | None = None

        # pynput-based global hotkey listener
        self._hotkey_listener: object | None = None
        self._ptt_listener: object | None = None
        self._ptt_active: bool = False

    # ------------------------------------------------------------------
    # Hotkey (pynput-based)
    # ------------------------------------------------------------------

    def register_hotkeys(self) -> bool:
        """Register global hotkeys via pynput low-level keyboard hooks."""
        self.unregister_hotkeys()

        if pynput_keyboard is None:
            logger.error("pynput not installed — global hotkeys unavailable")
            self._log_event("hotkey_registration_failed", reason="pynput_missing")
            return False

        hotkey_map: dict[str, callable] = {}
        # Register only toggle with GlobalHotKeys. Push-to-talk needs key
        # release events, so it is handled by _setup_ptt_listener below.
        # If both settings use the same combo, PTT wins to avoid the combo
        # also firing toggle on key press.
        toggle_hotkey = self._settings.hotkey_toggle.strip()
        ptt_hotkey = self._settings.hotkey_push_to_talk.strip()
        desired_hotkeys = []
        if toggle_hotkey.upper() != ptt_hotkey.upper():
            desired_hotkeys.append(("toggle", toggle_hotkey))
        else:
            fallback_toggle = "Ctrl+Shift+D"
            if fallback_toggle.upper() != ptt_hotkey.upper():
                desired_hotkeys.append(("toggle", fallback_toggle))
                logger.warning(
                    "Toggle hotkey duplicates PTT hotkey (%s); using fallback toggle %s",
                    ptt_hotkey,
                    fallback_toggle,
                )
        seen: set[str] = set()

        for role, raw_hotkey in desired_hotkeys:
            normalized = raw_hotkey.strip().upper()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)

            pynput_str = _hotkey_to_pynput_format(raw_hotkey)
            if pynput_str is None:
                logger.warning("Invalid hotkey setting ignored: %s", raw_hotkey)
                continue

            hotkey_id = self._hotkey_ids[role]
            # Create a closure that captures the hotkey_id
            def _make_callback(hid: int):
                def _cb():
                    self.hotkey_pressed.emit(hid)
                return _cb

            hotkey_map[pynput_str] = _make_callback(hotkey_id)
            self._registered_hotkeys[hotkey_id] = raw_hotkey.strip()
            self._log_event("hotkey_registered", role=role, hotkey=raw_hotkey.strip())
            logger.info("Registered global hotkey %s for %s (pynput: %s)", raw_hotkey.strip(), role, pynput_str)

        # Set up PTT press/release listener for the push_to_talk hotkey
        ptt_raw = ptt_hotkey.upper()
        if ptt_raw:
            ptt_format = _hotkey_to_pynput_format(self._settings.hotkey_push_to_talk)
            if ptt_format:
                self._setup_ptt_listener(ptt_format)

        if not hotkey_map:
            if self._ptt_listener is not None:
                self._registered = True
                return True
            self._log_event("hotkey_registration_failed")
            return False

        try:
            self._hotkey_listener = pynput_keyboard.GlobalHotKeys(hotkey_map)
            self._hotkey_listener.daemon = True
            self._hotkey_listener.start()
            self._registered = True
            logger.info("pynput hotkey listener started")
        except Exception as exc:
            logger.exception("Failed to start pynput hotkey listener: %s", exc)
            self._registered = False
            self._log_event("hotkey_registration_failed", error=str(exc)[:100])

        return self._registered

    def unregister_hotkeys(self) -> None:
        """Stop the pynput hotkey listener and PTT listener."""
        if self._hotkey_listener is not None:
            try:
                self._hotkey_listener.stop()
            except Exception:
                pass
            self._hotkey_listener = None
        if self._ptt_listener is not None:
            try:
                self._ptt_listener.stop()
            except Exception:
                pass
            self._ptt_listener = None
        self._registered = False
        self._registered_hotkeys.clear()
        self._ptt_active = False
        logger.info("Hotkeys unregistered")

    # ------------------------------------------------------------------
    # Push-to-talk press/release listener
    # ------------------------------------------------------------------

    def _setup_ptt_listener(self, pynput_format: str) -> None:
        """Start a keyboard.Listener that tracks press/release for the PTT hotkey.

        When all PTT keys are pressed simultaneously, emits ``ptt_pressed``.
        When any PTT key is released, emits ``ptt_released``.
        """
        self._ptt_listener: object | None = None
        self._ptt_active = False

        try:
            ptt_keys = set(pynput_keyboard.HotKey.parse(pynput_format))
        except Exception as exc:
            logger.warning("PTT listener: invalid hotkey '%s': %s", pynput_format, exc)
            return

        listener_ref: dict[str, object] = {}

        def _canonical(key):
            listener = listener_ref.get("listener")
            if listener is None:
                return key
            return listener.canonical(key)

        def _on_activate():
            if not self._ptt_active:
                self._ptt_active = True
                logger.debug("PTT pressed")
                self.ptt_pressed.emit()

        hotkey = pynput_keyboard.HotKey(ptt_keys, _on_activate)

        def _on_press(key):
            hotkey.press(_canonical(key))

        def _on_release(key):
            canonical_key = _canonical(key)
            if self._ptt_active and canonical_key in ptt_keys:
                self._ptt_active = False
                logger.debug("PTT released")
                self.ptt_released.emit()
            hotkey.release(canonical_key)

        try:
            self._ptt_listener = pynput_keyboard.Listener(
                on_press=_on_press, on_release=_on_release
            )
            listener_ref["listener"] = self._ptt_listener
            self._ptt_listener.daemon = True
            self._ptt_listener.start()
            logger.info("PTT press/release listener started for %s", pynput_format)
        except Exception as exc:
            logger.exception("Failed to start PTT listener: %s", exc)
            self._ptt_listener = None

    # ------------------------------------------------------------------
    # Tray
    # ------------------------------------------------------------------

    def setup_tray(self) -> QSystemTrayIcon:
        """Create QSystemTrayIcon with context menu."""
        icon = QIcon.fromTheme("audio-input-microphone")
        if icon.isNull():
            icon = QIcon(self._create_fallback_icon())

        self._tray_icon = QSystemTrayIcon(icon, parent=self)
        self._tray_icon.setToolTip("Spanglish Dictation")

        menu = QMenu()

        action_start = QAction("&Start Dictation", menu)
        action_continuous = QAction("Start &Continuous", menu)
        action_stop = QAction("St&op Dictation", menu)
        action_settings = QAction("&Settings", menu)
        action_exit = QAction("E&xit", menu)
        action_show_panel = QAction("Show Status Panel", menu)
        self._action_show_panel = action_show_panel

        action_stop.setEnabled(False)

        # Paste Mode submenu
        paste_mode_menu = QMenu("Paste Mode", menu)
        paste_mode_group = QActionGroup(paste_mode_menu)
        paste_mode_group.setExclusive(True)

        action_paste_immediate = QAction("Immediate", paste_mode_menu)
        action_paste_immediate.setCheckable(True)
        action_paste_immediate.setChecked(self._settings.paste_mode == "immediate")
        action_paste_immediate.setActionGroup(paste_mode_group)

        action_paste_confirm = QAction("Confirmation", paste_mode_menu)
        action_paste_confirm.setCheckable(True)
        action_paste_confirm.setChecked(self._settings.paste_mode == "confirmation")
        action_paste_confirm.setActionGroup(paste_mode_group)

        paste_mode_menu.addAction(action_paste_immediate)
        paste_mode_menu.addAction(action_paste_confirm)

        def _on_paste_mode_changed(action: QAction) -> None:
            if action == action_paste_immediate:
                self._settings.paste_mode = "immediate"
            else:
                self._settings.paste_mode = "confirmation"
            self._log_event("paste_mode_changed", mode=self._settings.paste_mode)

        paste_mode_group.triggered.connect(_on_paste_mode_changed)

        action_start.triggered.connect(lambda: self._log_event("tray_start_clicked"))
        action_continuous.triggered.connect(lambda: self._log_event("tray_continuous_clicked"))
        action_stop.triggered.connect(lambda: self._log_event("tray_stop_clicked"))
        action_settings.triggered.connect(self._on_settings)
        action_show_panel.triggered.connect(self._toggle_status_panel)
        action_exit.triggered.connect(self._on_exit)

        self._action_start = action_start
        self._action_stop = action_stop

        menu.addSection("Dictation")
        menu.addAction(action_start)
        menu.addAction(action_continuous)
        menu.addAction(action_stop)
        menu.addSection("Mode")
        menu.addMenu(paste_mode_menu)

        if self._model_manager is not None:
            profile_menu = QMenu("Profile", menu)
            profile_group = QActionGroup(profile_menu)
            profile_group.setExclusive(True)
            self._profile_actions: list[QAction] = []

            for profile in self._model_manager.list_profiles():
                action = QAction(profile.display_name, profile_menu)
                action.setCheckable(True)
                action.setChecked(
                    profile.canonical_name == self._settings.model_profile
                )
                action.setActionGroup(profile_group)
                action.setData(profile.canonical_name)
                profile_menu.addAction(action)
                self._profile_actions.append(action)

            def _on_profile_changed(action: QAction) -> None:
                new_profile = action.data()
                if (
                    new_profile
                    and isinstance(new_profile, str)
                    and new_profile != self._settings.model_profile
                ):
                    self._settings.model_profile = new_profile
                    self._log_event("profile_changed", profile=new_profile)
                    self.profile_changed.emit(new_profile)

            profile_group.triggered.connect(_on_profile_changed)
            menu.addSection("Profile")
            menu.addMenu(profile_menu)

        menu.addSection("Tools")
        menu.addAction(action_settings)
        menu.addAction(action_show_panel)
        menu.addSection("Exit")
        menu.addAction(action_exit)

        self._tray_icon.setContextMenu(menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        self.update_profile_tooltip("")
        self.update_action_state("idle")
        self._log_event("tray_shown")
        return self._tray_icon

    def update_tray_tooltip(self, text: str) -> None:
        if self._tray_icon is not None:
            self._tray_icon.setToolTip(text)

    def update_profile_tooltip(self, model_name: str = "") -> None:
        profile_name = self._settings.model_profile
        mode = self._get_profile_mode(profile_name).capitalize()
        tooltip = f"Spanglish Dictation — {profile_name} [{mode}]"
        if model_name:
            tooltip += f" ({model_name})"
        self.update_tray_tooltip(tooltip)

    def show_notification(self, title: str, message: str) -> None:
        if self._tray_icon is not None:
            self._tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_status_panel("idle")
            return
        if reason == QSystemTrayIcon.Trigger and self._tray_icon is not None:
            menu = self._tray_icon.contextMenu()
            if menu is not None:
                menu.popup(QCursor.pos())

    def update_action_state(self, state: str) -> None:
        if self._action_start is not None:
            self._action_start.setEnabled(state in ("idle", "ready", "error"))
        if self._action_stop is not None:
            self._action_stop.setEnabled(state in ("listening", "processing"))

    def _on_exit(self) -> None:
        self._log_event("app_exited")
        self.unregister_hotkeys()
        if self._app is not None:
            self._app.quit()

    def _on_settings(self) -> None:
        self._log_event("tray_settings_opened")
        # Capture current profile before dialog may change it
        self._pre_dialog_profile = self._settings.model_profile
        dialog = SettingsDialog(
            settings=self._settings,
            audio_capture=None,
            model_manager=self._model_manager,
            glossary_store=self._glossary_store,
            parent=None,
        )
        dialog.settings_applied.connect(self._apply_updated_settings)
        dialog.exec()

    def _apply_updated_settings(self) -> None:
        old_profile = getattr(self, "_pre_dialog_profile", None)
        self.update_profile_tooltip("")
        if not self.register_hotkeys():
            self.show_notification(
                "Spanglish Dictation",
                "Could not register the selected global hotkeys. Try another combination.",
            )
        self._sync_profile_menu()
        self.settings_updated.emit()
        # If model profile changed via settings dialog, trigger profile reload
        new_profile = self._settings.model_profile
        if old_profile is not None and new_profile != old_profile:
            self.profile_changed.emit(new_profile)

    def _sync_profile_menu(self) -> None:
        """Sync tray Profile submenu checkmarks with current settings."""
        for action in getattr(self, "_profile_actions", []):
            action.setChecked(action.data() == self._settings.model_profile)

    # ------------------------------------------------------------------
    # Status panel
    # ------------------------------------------------------------------

    def show_status_panel(self, status: str, detail: str = "") -> None:
        """Show or update the floating status panel.

        Displays a coloured floating panel with status, profile, and
        current mode (local / cloud).  Local mode uses green status
        colours; cloud mode uses a blue theme.
        """
        if self._status_panel is None:
            self._status_panel = self._create_status_panel()

        self.status_changed.emit(status)
        self.update_action_state(status)

        # Determine which colour map to use based on profile mode
        mode = self._get_profile_mode(self._settings.model_profile)
        if mode == "cloud":
            color = self._CLOUD_STATUS_COLORS.get(status, "#1565C0")
        else:
            color = self._STATUS_COLORS.get(status, "#9E9E9E")

        label = self._STATUS_LABELS.get(status, status.capitalize())
        if detail:
            label = detail
        if self._model_manager is not None:
            try:
                profile = self._model_manager.get_profile(self._settings.model_profile)
                label = f"{label} | {profile.display_name}"
            except KeyError:
                label = f"{label} | {self._settings.model_profile}"

        # Prepend a mode badge for clarity
        mode_badge = "[Cloud]" if mode == "cloud" else "[Local]"
        label = f"{mode_badge} {label}"

        if self._status_label is not None:
            self._status_label.setText(label)
            self._status_label.setStyleSheet(
                f"color: white; font-weight: bold; font-size: 14px;"
            )

        panel = self._status_panel
        panel.setStyleSheet(
            f"background-color: rgba({self._hex_to_rgba(color, 200)}); "
            f"border: 1px solid rgba(255,255,255,0.18); border-radius: 10px; padding: 10px;"
        )
        panel.adjustSize()
        self._position_status_panel(panel)
        panel.show()
        panel.raise_()
        if hasattr(self, "_action_show_panel") and self._action_show_panel is not None:
            self._action_show_panel.setText("Hide Status Panel")

        # Auto-hide after 3s in ready state
        if status == "ready":
            if self._auto_hide_timer is None:
                self._auto_hide_timer = QTimer(self)
                self._auto_hide_timer.setSingleShot(True)
                self._auto_hide_timer.timeout.connect(self._hide_status_panel)
            self._auto_hide_timer.start(3000)
        elif self._auto_hide_timer is not None and self._auto_hide_timer.isActive():
            self._auto_hide_timer.stop()

    def _hide_status_panel(self) -> None:
        if self._auto_hide_timer is not None and self._auto_hide_timer.isActive():
            self._auto_hide_timer.stop()
        if self._status_panel is not None:
            self._status_panel.hide()
        if hasattr(self, "_action_show_panel") and self._action_show_panel is not None:
            self._action_show_panel.setText("Show Status Panel")

    def _toggle_status_panel(self) -> None:
        """Toggle status panel visibility from tray menu."""
        if self._status_panel is not None and self._status_panel.isVisible():
            self._hide_status_panel()
        else:
            self.show_status_panel("idle")

    def _get_profile_mode(self, profile_name: str) -> str:
        """Return ``'cloud'`` or ``'local'`` for the given profile name.

        Falls back to ``'local'`` when the profile is unknown or the
        model manager is not available.
        """
        if self._model_manager is None:
            return "local"
        try:
            profile = self._model_manager.get_profile(profile_name)
            return profile.mode
        except KeyError:
            return "local"

    def _create_status_panel(self) -> QWidget:
        panel = QWidget()
        panel.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        panel.setAttribute(Qt.WA_ShowWithoutActivating, True)
        panel.setAttribute(Qt.WA_TranslucentBackground, True)
        panel.setMinimumSize(QSize(240, 50))

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._status_label = QLabel("Idle")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self._status_label, stretch=1)

        close_btn = QPushButton("\u2715", panel)
        close_btn.setFlat(True)
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(
            "QPushButton { color: rgba(255,255,255,0.8); font-size: 16px; "
            "border: none; border-radius: 14px; background: rgba(0,0,0,0.2); }"
            "QPushButton:hover { background: rgba(255,255,255,0.3); color: white; }"
        )
        close_btn.clicked.connect(self._hide_status_panel)
        top_layout.addWidget(close_btn)

        layout.addLayout(top_layout)

        self._position_status_panel(panel)

        return panel

    def _position_status_panel(self, panel: QWidget) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        panel.adjustSize()
        x = geo.right() - panel.width() - 20
        y = geo.bottom() - panel.height() - 20
        panel.move(x, y)

    @staticmethod
    def _parse_hotkey(value: str) -> tuple[int, int, str] | None:
        tokens = [token.strip() for token in value.split("+") if token.strip()]
        if len(tokens) < 2:
            return None

        key_token = tokens[-1].upper()
        modifier_tokens = [token.upper() for token in tokens[:-1]]
        modifiers = 0
        for token in modifier_tokens:
            mod = _MODIFIER_MAP.get(token)
            if mod is None:
                return None
            modifiers |= mod

        if modifiers == 0:
            return None

        # Look up virtual key code
        vk_code = _VK_MAP.get(key_token)
        if vk_code is None:
            # Single alphanumeric character
            if len(key_token) == 1 and key_token.isalnum():
                vk_code = ord(key_token)
            else:
                return None

        return modifiers, vk_code, "+".join([*modifier_tokens, key_token])

    # ------------------------------------------------------------------
    # Icon helper
    # ------------------------------------------------------------------

    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: int = 255) -> str:
        """Convert '#RRGGBB' to 'R, G, B, A' for use in rgba() CSS."""
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}, {alpha}"

    @staticmethod
    def _create_fallback_icon() -> QPixmap:
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setBrush(QColor("#4CAF50"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size - 8, size - 8)

        painter.setBrush(QColor("white"))
        painter.drawRoundedRect(size // 2 - 8, 16, 16, 24, 8, 8)
        painter.drawArc(size // 2 - 12, 30, 24, 20, 0, 180 * 16)
        painter.setPen(QColor("white"))
        painter.drawLine(size // 2, 40, size // 2, 50)
        painter.drawLine(size // 2 - 6, 50, size // 2 + 6, 50)

        painter.end()
        return pixmap

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_event(self, name: str, **kwargs: object) -> None:
        if self._diagnostics is not None:
            try:
                self._diagnostics.event(name, **kwargs)
            except Exception:
                pass
        logger.debug("Event: %s %r", name, kwargs)
