"""Application entry point with PySide6 QApplication and system tray shell."""

from __future__ import annotations

import sys
from pathlib import Path

from diagnostics import Diagnostics
from settings_store import SettingsStore


def _create_fallback_icon():
    """Build a simple microphone-shaped pixmap icon for Windows."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap

    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Circle background
    painter.setBrush(QColor("#4CAF50"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # Microphone body (white rectangle with rounded top)
    painter.setBrush(QColor("white"))
    painter.drawRoundedRect(size // 2 - 8, 16, 16, 24, 8, 8)

    # Microphone base (white arc)
    painter.drawArc(size // 2 - 12, 30, 24, 20, 0, 180 * 16)

    # Stand (white line)
    painter.setPen(QColor("white"))
    painter.drawLine(size // 2, 40, size // 2, 50)
    painter.drawLine(size // 2 - 6, 50, size // 2 + 6, 50)

    painter.end()
    return pixmap


def main() -> int:
    """Launch the Spanglish Dictation tray application.

    Returns the QApplication exit code.
    """
    from PySide6.QtGui import QAction, QIcon, QCursor
    from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

    app = QApplication(sys.argv)
    app.setApplicationName("Spanglish Dictation")
    app.setQuitOnLastWindowClosed(False)

    # ------------------------------------------------------------------
    # Core services
    # ------------------------------------------------------------------
    settings = SettingsStore()
    diagnostics = Diagnostics()
    diagnostics.event("app_started")

    # ------------------------------------------------------------------
    # Tray icon
    # ------------------------------------------------------------------
    icon = QIcon.fromTheme("audio-input-microphone")
    if icon.isNull():
        icon = QIcon(_create_fallback_icon())

    tray_icon = QSystemTrayIcon(icon, parent=app)
    tray_icon.setToolTip("Spanglish Dictation")

    # ------------------------------------------------------------------
    # Tray menu
    # ------------------------------------------------------------------
    menu = QMenu()

    action_start = QAction("Start Dictation", menu)
    action_stop = QAction("Stop Dictation", menu)
    action_settings = QAction("Settings", menu)
    action_exit = QAction("Exit", menu)

    action_stop.setEnabled(False)

    def _on_start() -> None:
        action_start.setEnabled(False)
        action_stop.setEnabled(True)
        diagnostics.event("dictation_started", audio_device="redacted")

    def _on_stop() -> None:
        action_start.setEnabled(True)
        action_stop.setEnabled(False)
        diagnostics.event("dictation_stopped")

    def _on_settings() -> None:
        diagnostics.event("settings_opened")
        # Placeholder — settings UI will be wired in a future plan.

    def _on_exit() -> None:
        diagnostics.event("app_exited")
        app.quit()

    action_start.triggered.connect(_on_start)
    action_stop.triggered.connect(_on_stop)
    action_settings.triggered.connect(_on_settings)
    action_exit.triggered.connect(_on_exit)

    menu.addAction(action_start)
    menu.addAction(action_stop)
    menu.addSeparator()
    menu.addAction(action_settings)
    menu.addSeparator()
    menu.addAction(action_exit)

    tray_icon.setContextMenu(menu)

    # Show menu on left-click as well as right-click
    def _on_activated(reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            menu.popup(QCursor.pos())

    tray_icon.activated.connect(_on_activated)
    tray_icon.show()

    diagnostics.event("tray_shown")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
