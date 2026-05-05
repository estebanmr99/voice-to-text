"""Offline-only settings dialog for user preferences.

This dialog exposes local settings for the app and never performs network
operations or telemetry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from audio_capture import AudioCapture

if TYPE_CHECKING:
    from model_manager import ModelManager
    from settings_store import SettingsStore


_HOTKEY_PATTERN = re.compile(
    r"^(Ctrl|Alt|Shift|Win)(\+(Ctrl|Alt|Shift|Win))*\+[A-Z0-9]$",
    re.IGNORECASE,
)


class SettingsDialog(QDialog):
    def __init__(
        self,
        settings: "SettingsStore",
        audio_capture: AudioCapture | None = None,
        model_manager: "ModelManager | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._model_manager = model_manager
        self._audio_capture = audio_capture

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setMinimumWidth(480)
        self.resize(560, 460)

        root = QVBoxLayout(self)

        form_host = QWidget(self)
        form = QFormLayout(form_host)

        # Hotkeys
        hotkeys_group = QGroupBox("Hotkeys", self)
        hotkeys_layout = QFormLayout(hotkeys_group)
        self.hotkey_push_to_talk_input = QLineEdit(self)
        self.hotkey_push_to_talk_input.setPlaceholderText("Ctrl+Alt+D")
        self.hotkey_toggle_input = QLineEdit(self)
        self.hotkey_toggle_input.setPlaceholderText("Ctrl+Alt+T")
        hotkeys_layout.addRow("Push-to-talk", self.hotkey_push_to_talk_input)
        hotkeys_layout.addRow("Toggle", self.hotkey_toggle_input)
        note = QLabel("Format: Ctrl+Alt+Key or Win+Key", self)
        note.setStyleSheet("color: #666;")
        hotkeys_layout.addRow(note)

        # Audio
        audio_group = QGroupBox("Audio", self)
        audio_layout = QFormLayout(audio_group)
        self.audio_device_combo = QComboBox(self)
        audio_layout.addRow("Input device", self.audio_device_combo)

        # Processing
        processing_group = QGroupBox("Processing", self)
        processing_layout = QFormLayout(processing_group)
        self.model_profile_combo = QComboBox(self)
        self.vad_profile_combo = QComboBox(self)
        self.vad_profile_combo.addItem("WebRTC VAD — default", "webrtc")
        self.vad_profile_combo.addItem("Silero VAD — accurate", "silero")
        processing_layout.addRow("Model profile", self.model_profile_combo)
        processing_layout.addRow("VAD profile", self.vad_profile_combo)

        # Paste & Language
        paste_lang_group = QGroupBox("Paste & Language", self)
        paste_lang_layout = QFormLayout(paste_lang_group)
        self.paste_mode_combo = QComboBox(self)
        self.paste_mode_combo.addItem("Paste immediately", "immediate")
        self.paste_mode_combo.addItem("Confirm before paste", "confirmation")
        self.language_combo = QComboBox(self)
        self.language_combo.addItem("Auto-detect", "auto")
        self.language_combo.addItem("Spanish", "es")
        self.language_combo.addItem("English", "en")
        paste_lang_layout.addRow("Paste mode", self.paste_mode_combo)
        paste_lang_layout.addRow("Language", self.language_combo)

        # Glossary
        glossary_group = QGroupBox("Glossary", self)
        glossary_layout = QFormLayout(glossary_group)
        self.glossary_path_input = QLineEdit(self)
        browse_button = QPushButton("Browse...", self)
        browse_button.clicked.connect(self._browse_glossary)
        glossary_row = QHBoxLayout()
        glossary_row.addWidget(self.glossary_path_input, stretch=1)
        glossary_row.addWidget(browse_button)
        glossary_layout.addRow("Glossary path", glossary_row)

        form.addRow(hotkeys_group)
        form.addRow(audio_group)
        form.addRow(processing_group)
        form.addRow(paste_lang_group)
        form.addRow(glossary_group)
        root.addWidget(form_host)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
            self,
        )
        self.button_box.accepted.connect(self._on_save)
        self.button_box.rejected.connect(self.reject)
        root.addWidget(self.button_box)

        self._populate_model_profiles()
        self._populate_audio_devices()
        self._load_from_settings()

    def _populate_model_profiles(self) -> None:
        self.model_profile_combo.clear()
        if self._model_manager is None:
            self.model_profile_combo.addItem(self._settings.model_profile, self._settings.model_profile)
            return
        for profile in self._model_manager.list_profiles():
            self.model_profile_combo.addItem(profile.display_name, profile.canonical_name)

    def _populate_audio_devices(self) -> None:
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("Default", None)
        capture = self._audio_capture
        if capture is None:
            try:
                capture = AudioCapture()
            except Exception:
                capture = None

        try:
            devices = capture.list_devices() if capture is not None else AudioCapture.list_devices()
        except Exception:
            self.audio_device_combo.clear()
            self.audio_device_combo.addItem("sounddevice not available", None)
            self.audio_device_combo.setEnabled(False)
            return

        self.audio_device_combo.setEnabled(True)
        for dev in devices:
            name = str(dev.get("name", "Unknown device"))
            idx = dev.get("index")
            self.audio_device_combo.addItem(name, idx)

    def _load_from_settings(self) -> None:
        self.hotkey_push_to_talk_input.setText(self._settings.hotkey_push_to_talk)
        self.hotkey_toggle_input.setText(self._settings.hotkey_toggle)
        self._set_combo_value(self.audio_device_combo, self._settings.audio_device_index)
        self._set_combo_value(self.model_profile_combo, self._settings.model_profile)
        self._set_combo_value(self.vad_profile_combo, self._settings.vad_profile)
        self._set_combo_value(self.paste_mode_combo, self._settings.paste_mode)
        self._set_combo_value(self.language_combo, self._settings.language)
        glossary_value = self._settings.get("glossary_path", "")
        self.glossary_path_input.setText(str(glossary_value or ""))

    @staticmethod
    def _set_combo_value(combo: QComboBox, value: object) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _browse_glossary(self) -> None:
        current = self.glossary_path_input.text().strip()
        start_dir = str(Path(current).parent) if current else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select glossary file",
            start_dir,
            "Glossary files (*.json *.yaml *.yml *.txt)",
        )
        if path:
            self.glossary_path_input.setText(path)

    @staticmethod
    def _is_valid_hotkey(value: str) -> bool:
        return bool(_HOTKEY_PATTERN.match(value.strip().upper()))

    def _on_save(self) -> None:
        ptt = self.hotkey_push_to_talk_input.text().strip()
        toggle = self.hotkey_toggle_input.text().strip()
        if not self._is_valid_hotkey(ptt):
            QMessageBox.warning(self, "Invalid hotkey", "Push-to-talk hotkey format is invalid.")
            return
        if not self._is_valid_hotkey(toggle):
            QMessageBox.warning(self, "Invalid hotkey", "Toggle hotkey format is invalid.")
            return

        self._settings.hotkey_push_to_talk = ptt
        self._settings.hotkey_toggle = toggle
        self._settings.audio_device_index = self.audio_device_combo.currentData()
        model_profile = self.model_profile_combo.currentData()
        if isinstance(model_profile, str) and model_profile:
            self._settings.model_profile = model_profile
        self._settings.vad_profile = str(self.vad_profile_combo.currentData())
        self._settings.paste_mode = str(self.paste_mode_combo.currentData())
        self._settings.language = str(self.language_combo.currentData())
        self._settings.set("glossary_path", self.glossary_path_input.text().strip())
        self._settings.save()
        self.accept()
