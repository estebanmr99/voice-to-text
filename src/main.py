"""Application entry point with full module wiring and privacy enforcement."""

from __future__ import annotations

import multiprocessing
import sys
from pathlib import Path

# ------------------------------------------------------------------
# PyInstaller Windows: prevent fork bomb on multiprocessing spawn
# ------------------------------------------------------------------
multiprocessing.freeze_support()

# ------------------------------------------------------------------
# PrivacyGuard MUST be enforced before any import that might network
# ------------------------------------------------------------------
from privacy_guard import PrivacyGuard

PrivacyGuard().enforce()

# ------------------------------------------------------------------
# Standard / third-party imports
# ------------------------------------------------------------------
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from diagnostics import Diagnostics
from settings_store import SettingsStore
from model_manager import ModelManager
from hardware_detector import detect_hardware
from profile_resolver import resolve_profile
from audio_capture import AudioCapture
from speech_detector import SpeechDetector
from transcriber import Transcriber
from paste_controller import PasteController
from dictation_loop import DictationLoop
from confirmation_dialog import ConfirmationDialog
from shell_integration import ShellIntegration
from post_processor import PostProcessor
from glossary import GlossaryStore


def _apply_profile_change(
    new_profile: str,
    settings: SettingsStore,
    model_manager: ModelManager,
    transcriber: Transcriber,
    shell: ShellIntegration,
    diagnostics: Diagnostics,
    hardware_info,
) -> None:
    """Apply profile change by resolving model and restarting transcriber."""
    diagnostics.event("profile_change_requested", profile=new_profile)
    transcriber.stop()
    resolution = resolve_profile(settings, model_manager, hardware_info)
    if resolution.model_info is None:
        shell.show_notification(
            "Spanglish Dictation",
            f"Profile '{new_profile}' unavailable. {resolution.error_message}",
        )
        diagnostics.event(
            "profile_change_failed",
            profile=new_profile,
            error=resolution.error_message[:100],
        )
        return

    success = transcriber.start(resolution.model_info)
    if success:
        shell.update_profile_tooltip(resolution.model_info.name)
        diagnostics.event(
            "profile_changed",
            profile=resolution.profile_used,
            model=resolution.model_info.name,
            fallback=resolution.fallback_applied,
        )
        if resolution.advisory_message:
            shell.show_notification("Spanglish Dictation", resolution.advisory_message)
    else:
        shell.show_notification(
            "Spanglish Dictation",
            f"Failed to load model for profile '{new_profile}'. Check model files.",
        )
        diagnostics.event("profile_change_model_load_failed", profile=new_profile)


def _create_fallback_icon():
    """Build a simple microphone-shaped pixmap icon for Windows."""
    from PySide6.QtCore import Qt as _Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap

    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(_Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Circle background
    painter.setBrush(QColor("#4CAF50"))
    painter.setPen(_Qt.NoPen)
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
    """Launch the Spanglish Dictation application.

    Returns the QApplication exit code.
    """
    # ------------------------------------------------------------------
    # Qt application
    # ------------------------------------------------------------------
    app = QApplication(sys.argv)
    app.setApplicationName("Spanglish Dictation")
    app.setQuitOnLastWindowClosed(False)

    # ------------------------------------------------------------------
    # Core services (order matters)
    # ------------------------------------------------------------------
    settings = SettingsStore()
    diagnostics = Diagnostics()
    diagnostics.event("app_started")

    model_manager = ModelManager(models_dir=Path(__file__).resolve().parent.parent / "models")
    audio_capture = AudioCapture(device_index=settings.audio_device_index)
    speech_detector = SpeechDetector()
    transcriber = Transcriber(model_manager)
    paste_controller = PasteController(diagnostics=diagnostics)

    # ------------------------------------------------------------------
    # Post-processor for Spanglish glossary normalization
    # ------------------------------------------------------------------
    glossary_store = GlossaryStore.from_settings(settings)
    post_processor = PostProcessor(glossary_store)

    # ------------------------------------------------------------------
    # Dictation loop
    # ------------------------------------------------------------------
    dictation_loop = DictationLoop(
        settings=settings,
        audio_capture=audio_capture,
        speech_detector=speech_detector,
        transcriber=transcriber,
        paste_controller=paste_controller,
        diagnostics=diagnostics,
        post_processor=post_processor,
    )

    # ------------------------------------------------------------------
    # Shell integration (tray + hotkey)
    # ------------------------------------------------------------------
    shell = ShellIntegration(
        settings=settings,
        model_manager=model_manager,
        diagnostics=diagnostics,
        glossary_store=glossary_store,
    )

    hardware_info = detect_hardware()

    def _on_profile_changed(new_profile: str) -> None:
        _apply_profile_change(
            new_profile,
            settings,
            model_manager,
            transcriber,
            shell,
            diagnostics,
            hardware_info,
        )

    shell.profile_changed.connect(_on_profile_changed)
    shell.register_hotkeys()
    shell.settings_updated.connect(
        lambda: audio_capture.set_device_index(settings.audio_device_index)
    )

    # Connect signals
    shell.hotkey_pressed.connect(lambda _hid: dictation_loop.toggle())
    shell.ptt_pressed.connect(dictation_loop.start)
    shell.ptt_released.connect(dictation_loop.stop)
    dictation_loop.state_changed.connect(
        lambda state, msg: shell.show_status_panel(state.value, msg)
    )

    def _on_transcription_ready(text: str) -> None:
        accepted, edited_text = ConfirmationDialog.show_confirmation(parent=None, text=text)
        if accepted:
            dictation_loop.confirm_paste(edited_text)
        else:
            dictation_loop.cancel_paste()

    dictation_loop.transcription_ready.connect(_on_transcription_ready)

    tray = shell.setup_tray()

    # Wire tray Start / Stop actions to dictation loop
    menu = tray.contextMenu()
    for action in menu.actions():
        text = action.text().replace("&", "")
        if text == "Start Dictation":
            action.triggered.connect(dictation_loop.start)
        elif text == "Start Continuous":
            action.triggered.connect(dictation_loop.start_continuous)
        elif text == "Stop Dictation":
            action.triggered.connect(dictation_loop.stop)

    # Fallback icon if theme icon missing
    icon = QIcon.fromTheme("audio-input-microphone")
    if icon.isNull():
        icon = QIcon(_create_fallback_icon())
    tray.setIcon(icon)

    # Detect hardware and resolve profile/model selection
    diagnostics.event(
        "hardware_detected",
        cpu_cores=hardware_info.cpu_logical_cores,
        has_nvidia=hardware_info.has_nvidia_gpu,
    )

    resolution = resolve_profile(settings, model_manager, hardware_info)

    if resolution.model_info is None:
        shell.show_notification(
            "Spanglish Dictation",
            (
                f"No model available for profile '{resolution.profile_used}'. "
                f"{resolution.error_message}"
            ),
        )
        diagnostics.event(
            "model_missing_at_startup",
            profile=resolution.profile_used,
            error=resolution.error_message[:100],
        )
    else:
        transcriber.start(resolution.model_info)
        shell.update_profile_tooltip(resolution.model_info.name)
        diagnostics.event(
            "model_loaded",
            model=resolution.model_info.name,
            profile=resolution.profile_used,
            fallback_applied=resolution.fallback_applied,
        )
        if resolution.advisory_message:
            shell.show_notification("Spanglish Dictation", resolution.advisory_message)
            diagnostics.event(
                "profile_advisory",
                message=resolution.advisory_message[:100],
            )

    diagnostics.event("tray_shown")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
