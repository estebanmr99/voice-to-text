"""Shell integration — global hotkey, system tray, and floating status panel.

Uses Win32 ``RegisterHotKey`` (user-mode, no admin) and a Qt native event
filter to intercept ``WM_HOTKEY`` messages inside PySide6's event loop.
"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, QTimer, QAbstractNativeEventFilter
from PySide6.QtGui import QAction, QActionGroup, QCursor, QIcon, QPixmap, QColor, QPainter, Qt
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
    QWidget,
    QLabel,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QPushButton,
)
from settings_dialog import SettingsDialog

if TYPE_CHECKING:
    from model_manager import ModelManager
    from settings_store import SettingsStore
    from diagnostics import Diagnostics
    from glossary import GlossaryStore

logger = logging.getLogger(__name__)

# Win32 constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
WM_HOTKEY = 0x0312


class HotkeyNativeEventFilter(QObject, QAbstractNativeEventFilter):
    """Native event filter that intercepts WM_HOTKEY and emits a Qt signal."""

    hotkey_pressed = Signal(int)

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = message
            if msg.message == WM_HOTKEY:
                self.hotkey_pressed.emit(msg.wParam)
                return (True, 0)
        return (False, 0)


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
    status_changed = Signal(str)
    profile_changed = Signal(str)

    # Status color mapping
    _STATUS_COLORS: dict[str, str] = {
        "idle": "#4CAF50",      # green
        "listening": "#F44336",  # red
        "processing": "#FF9800", # yellow
        "ready": "#4CAF50",      # green check
        "error": "#FFC107",      # warning
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
        self._hotkey_id = 1
        self._registered = False
        self._app = QApplication.instance()

        self._tray_icon: QSystemTrayIcon | None = None
        self._status_panel: QWidget | None = None
        self._status_label: QLabel | None = None
        self._auto_hide_timer: QTimer | None = None
        self._action_start: QAction | None = None
        self._action_stop: QAction | None = None

        self._event_filter = HotkeyNativeEventFilter()
        self._event_filter.hotkey_pressed.connect(self.hotkey_pressed)
        if self._app is not None:
            self._app.installNativeEventFilter(self._event_filter)

    # ------------------------------------------------------------------
    # Hotkey
    # ------------------------------------------------------------------

    def register_hotkeys(self) -> bool:
        """Register global hotkeys via Win32 RegisterHotKey (no admin)."""
        user32 = ctypes.windll.user32
        # Default hotkey: Ctrl+Alt+D
        result = user32.RegisterHotKey(
            None, self._hotkey_id, MOD_CONTROL | MOD_ALT, ord("D")
        )
        if result:
            self._registered = True
            self._log_event("hotkey_registered", modifiers="Ctrl+Alt", key="D")
            logger.info("Registered global hotkey Ctrl+Alt+D")
        else:
            logger.warning("Failed to register global hotkey")
        return self._registered

    def unregister_hotkeys(self) -> None:
        """Unregister all global hotkeys."""
        if not self._registered:
            return
        user32 = ctypes.windll.user32
        user32.UnregisterHotKey(None, self._hotkey_id)
        self._registered = False
        self._log_event("hotkey_unregistered")
        logger.info("Unregistered global hotkey")

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
        action_stop = QAction("St&op Dictation", menu)
        action_settings = QAction("&Settings", menu)
        action_exit = QAction("E&xit", menu)
        action_show_panel = QAction("Show Status Panel", menu)

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
        action_stop.triggered.connect(lambda: self._log_event("tray_stop_clicked"))
        action_settings.triggered.connect(self._on_settings)
        action_show_panel.triggered.connect(lambda: self.show_status_panel("idle"))
        action_exit.triggered.connect(self._on_exit)

        self._action_start = action_start
        self._action_stop = action_stop

        menu.addSection("Dictation")
        menu.addAction(action_start)
        menu.addAction(action_stop)
        menu.addSection("Mode")
        menu.addMenu(paste_mode_menu)

        if self._model_manager is not None:
            profile_menu = QMenu("Profile", menu)
            profile_group = QActionGroup(profile_menu)
            profile_group.setExclusive(True)

            for profile in self._model_manager.list_profiles():
                action = QAction(profile.display_name, profile_menu)
                action.setCheckable(True)
                action.setChecked(
                    profile.canonical_name == self._settings.model_profile
                )
                action.setActionGroup(profile_group)
                action.setData(profile.canonical_name)
                profile_menu.addAction(action)

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
        tooltip = f"Spanglish Dictation — {profile_name}"
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
        dialog = SettingsDialog(
            settings=self._settings,
            audio_capture=None,
            model_manager=self._model_manager,
            glossary_store=self._glossary_store,
            parent=None,
        )
        dialog.exec()

    # ------------------------------------------------------------------
    # Status panel
    # ------------------------------------------------------------------

    def show_status_panel(self, status: str) -> None:
        """Show or update the floating status panel."""
        if self._status_panel is None:
            self._status_panel = self._create_status_panel()

        self.status_changed.emit(status)
        self.update_action_state(status)

        color = self._STATUS_COLORS.get(status, "#9E9E9E")
        label = self._STATUS_LABELS.get(status, status.capitalize())
        if self._model_manager is not None:
            try:
                profile = self._model_manager.get_profile(self._settings.model_profile)
                label = f"{label} | {profile.display_name}"
            except KeyError:
                label = f"{label} | {self._settings.model_profile}"

        if self._status_label is not None:
            self._status_label.setText(label)
            self._status_label.setStyleSheet(
                f"color: white; font-weight: bold; font-size: 14px;"
            )

        panel = self._status_panel
        panel.setStyleSheet(
            f"background-color: {color}; border-radius: 10px; padding: 10px;"
        )
        panel.show()
        panel.raise_()
        panel.activateWindow()

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

    def _create_status_panel(self) -> QWidget:
        panel = QWidget()
        panel.setWindowFlags(
            Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        panel.setAttribute(Qt.WA_TranslucentBackground, True)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)

        self._status_label = QLabel("Idle")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self._status_label, stretch=1)

        close_btn = QPushButton("x", panel)
        close_btn.setFlat(True)
        close_btn.setStyleSheet("color: white; font-weight: bold; font-size: 12px;")
        close_btn.setMaximumWidth(24)
        close_btn.setMaximumHeight(24)
        close_btn.clicked.connect(self._hide_status_panel)
        top_layout.addWidget(close_btn)

        layout.addLayout(top_layout)

        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        panel.setGraphicsEffect(shadow)

        # Position bottom-right of primary screen
        screen = QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            panel.resize(220, 60)
            x = geo.right() - panel.width() - 20
            y = geo.bottom() - panel.height() - 20
            panel.move(x, y)

        return panel

    # ------------------------------------------------------------------
    # Icon helper
    # ------------------------------------------------------------------

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
