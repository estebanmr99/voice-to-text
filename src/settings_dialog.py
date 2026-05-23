"""Offline-only settings dialog for user preferences.

This dialog exposes local settings for the app and never performs network
operations or telemetry.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
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
    from glossary import GlossaryStore


_HOTKEY_PATTERN = re.compile(
    r"^(Ctrl|Alt|Shift|Win)(\+(Ctrl|Alt|Shift|Win))*\+"
    r"([A-Z0-9]|F[1-9]|F1[0-2]|Space|Enter|Return|Tab|Esc|Escape|"
    r"Insert|Delete|Home|End|PageUp|PageDown|Up|Down|Left|Right)$",
    re.IGNORECASE,
)


class SettingsDialog(QDialog):
    settings_applied = Signal()

    def __init__(
        self,
        settings: "SettingsStore",
        audio_capture: AudioCapture | None = None,
        model_manager: "ModelManager | None" = None,
        glossary_store: "GlossaryStore | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._model_manager = model_manager
        self._audio_capture = audio_capture
        self._glossary_store = glossary_store

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
        self.hotkey_push_to_talk_input.setPlaceholderText("Ctrl+Shift+Space")
        self.hotkey_toggle_input = QLineEdit(self)
        self.hotkey_toggle_input.setPlaceholderText("Ctrl+Shift+D")
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

        # Cloud Provider
        cloud_group = QGroupBox("Cloud Provider", self)
        cloud_layout = QFormLayout(cloud_group)

        self.cloud_profile_combo = QComboBox(self)
        self.cloud_profile_combo.setEditable(True)
        self.cloud_profile_combo.setInsertPolicy(QComboBox.NoInsert)
        cloud_layout.addRow("Profile", self.cloud_profile_combo)

        self.cloud_provider_combo = QComboBox(self)
        self.cloud_provider_combo.addItem("Azure OpenAI", "azure")
        self.cloud_provider_combo.addItem("AWS Transcribe", "aws")
        cloud_layout.addRow("Provider", self.cloud_provider_combo)

        self.cloud_endpoint_input = QLineEdit(self)
        self.cloud_endpoint_input.setPlaceholderText("https://example.openai.azure.com")
        cloud_layout.addRow("Endpoint URL", self.cloud_endpoint_input)

        self.cloud_api_key_input = QLineEdit(self)
        self.cloud_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.cloud_api_key_input.setPlaceholderText("Enter API key")
        cloud_layout.addRow("API Key", self.cloud_api_key_input)

        self.cloud_model_input = QLineEdit(self)
        self.cloud_model_input.setPlaceholderText("whisper-1")
        cloud_layout.addRow("Model/Deployment", self.cloud_model_input)

        self._cloud_region_label = QLabel("Region", self)
        self.cloud_region_input = QLineEdit(self)
        self.cloud_region_input.setPlaceholderText("e.g. us-east-1")
        cloud_layout.addRow(self._cloud_region_label, self.cloud_region_input)

        btn_layout = QHBoxLayout()
        self.cloud_save_button = QPushButton("Save Profile", self)
        self.cloud_delete_button = QPushButton("Delete Profile", self)
        self.cloud_test_button = QPushButton("Test Connection", self)
        btn_layout.addWidget(self.cloud_save_button)
        btn_layout.addWidget(self.cloud_delete_button)
        btn_layout.addWidget(self.cloud_test_button)
        cloud_layout.addRow(btn_layout)

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

        # Import / Export buttons
        glossary_btn_layout = QHBoxLayout()
        self.import_button = QPushButton("Import...", self)
        self.export_button = QPushButton("Export...", self)
        self.import_button.setToolTip("Import a glossary JSON file as your custom glossary")
        self.export_button.setToolTip("Export current glossary (defaults + custom) to a file")
        self.import_button.clicked.connect(self._on_import_glossary)
        self.export_button.clicked.connect(self._on_export_glossary)
        glossary_btn_layout.addWidget(self.import_button)
        glossary_btn_layout.addWidget(self.export_button)
        glossary_layout.addRow(glossary_btn_layout)

        form.addRow(hotkeys_group)
        form.addRow(audio_group)
        form.addRow(processing_group)
        form.addRow(cloud_group)
        form.addRow(paste_lang_group)
        form.addRow(glossary_group)
        root.addWidget(form_host)

        # Cloud provider signal connections
        self.cloud_profile_combo.currentIndexChanged.connect(self._on_cloud_profile_selected)
        self.cloud_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.cloud_save_button.clicked.connect(self._on_cloud_save)
        self.cloud_delete_button.clicked.connect(self._on_cloud_delete)
        self.cloud_test_button.clicked.connect(self._on_cloud_test)

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
        self._populate_cloud_profiles_combo()
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
            name = str(dev.get("display_name") or dev.get("name", "Unknown device"))
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

        # Cloud settings
        provider = self._settings.cloud_provider
        if provider:
            idx = self.cloud_provider_combo.findData(provider)
            if idx >= 0:
                self.cloud_provider_combo.setCurrentIndex(idx)
        self.cloud_endpoint_input.setText(self._settings.cloud_endpoint_url)
        self.cloud_model_input.setText(self._settings.cloud_model_name or "whisper-1")
        api_key = self._settings.get_api_key("cloud/main")
        if api_key:
            self.cloud_api_key_input.setText(api_key)

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

    def _on_import_glossary(self) -> None:
        """Import a glossary JSON file and set it as user glossary."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import glossary file",
            "",
            "Glossary files (*.json *.yaml *.yml *.txt)",
        )
        if not path:
            return

        if self._glossary_store is None:
            QMessageBox.warning(self, "Import Error", "Glossary store not initialized.")
            return

        errors = self._glossary_store.import_glossary(Path(path))
        if errors:
            QMessageBox.warning(
                self,
                "Import Error",
                "Invalid glossary file:\n\n" + "\n".join(errors),
            )
            return

        # Update glossary path setting to point to the imported file location
        if self._glossary_store._user_path is not None:
            self._settings.set("glossary_path", str(self._glossary_store._user_path))
            self.glossary_path_input.setText(str(self._glossary_store._user_path))
        QMessageBox.information(self, "Import Complete", "Glossary imported successfully.")

    def _on_export_glossary(self) -> None:
        """Export current merged glossary to a file."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export glossary file",
            "",
            "Glossary files (*.json)",
        )
        if not path:
            return

        if self._glossary_store is None:
            QMessageBox.warning(self, "Export Error", "Glossary store not initialized.")
            return

        try:
            self._glossary_store.export_glossary(Path(path))
            QMessageBox.information(self, "Export Complete", f"Glossary exported to:\n{path}")
        except OSError as exc:
            QMessageBox.warning(self, "Export Error", f"Failed to write glossary:\n{exc}")

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

        self._settings.begin_batch()
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

        # Cloud settings
        self._settings.cloud_provider = str(self.cloud_provider_combo.currentData())
        self._settings.cloud_endpoint_url = self.cloud_endpoint_input.text().strip()
        self._settings.cloud_model_name = self.cloud_model_input.text().strip() or "whisper-1"
        api_key = self.cloud_api_key_input.text()
        if api_key:
            self._settings.store_api_key("cloud/main", api_key)

        self._settings.end_batch()
        self.settings_applied.emit()
        self.accept()

    def _populate_cloud_profiles_combo(self, select_name: str | None = None) -> None:
        """Populate the saved cloud profiles combo from settings."""
        self.cloud_profile_combo.blockSignals(True)
        self.cloud_profile_combo.clear()
        self.cloud_profile_combo.addItem("New Profile...", None)
        for profile in self._settings.cloud_profiles:
            name = profile.get("name", "")
            self.cloud_profile_combo.addItem(name, name)
        self.cloud_profile_combo.blockSignals(False)

        if select_name:
            idx = self.cloud_profile_combo.findData(select_name)
            if idx >= 0:
                self.cloud_profile_combo.setCurrentIndex(idx)

    def _on_cloud_profile_selected(self, index: int) -> None:
        """Populate fields when a saved cloud profile is selected."""
        name = self.cloud_profile_combo.itemData(index)
        if name is None:
            # "New Profile..." — keep current fields
            return

        for profile in self._settings.cloud_profiles:
            if profile.get("name") == name:
                provider = profile.get("provider", "")
                idx = self.cloud_provider_combo.findData(provider)
                if idx >= 0:
                    self.cloud_provider_combo.setCurrentIndex(idx)
                self.cloud_endpoint_input.setText(profile.get("endpoint_url", ""))
                self.cloud_model_input.setText(profile.get("model_name", ""))
                self.cloud_region_input.setText(profile.get("region", ""))
                api_key = self._settings.get_api_key(f"cloud/{name}")
                if api_key:
                    self.cloud_api_key_input.setText(api_key)
                break

    def _on_cloud_save(self) -> None:
        """Save current cloud configuration as a named profile."""
        name = self.cloud_profile_combo.currentText().strip()
        if not name or name == "New Profile...":
            QMessageBox.warning(self, "Save Error", "Please enter a profile name.")
            return

        profiles = list(self._settings.cloud_profiles)
        provider = self.cloud_provider_combo.currentData()
        endpoint = self.cloud_endpoint_input.text().strip()
        model = self.cloud_model_input.text().strip() or "whisper-1"
        region = self.cloud_region_input.text().strip()

        profile_data: dict[str, str] = {
            "name": name,
            "provider": str(provider) if provider else "",
            "endpoint_url": endpoint,
            "model_name": model,
            "region": region,
        }

        # Update existing or append new
        found = False
        for i, p in enumerate(profiles):
            if p.get("name") == name:
                profiles[i] = profile_data
                found = True
                break
        if not found:
            profiles.append(profile_data)

        self._settings.cloud_profiles = profiles
        self._populate_cloud_profiles_combo(name)

        # Store API key
        api_key = self.cloud_api_key_input.text()
        if api_key:
            self._settings.store_api_key(f"cloud/{name}", api_key)

        QMessageBox.information(self, "Saved", f"Cloud profile '{name}' saved.")

    def _on_cloud_delete(self) -> None:
        """Delete the selected cloud profile."""
        idx = self.cloud_profile_combo.currentIndex()
        name = self.cloud_profile_combo.itemData(idx)
        if name is None:
            QMessageBox.warning(self, "Delete Error", "No saved profile selected.")
            return

        profiles = list(self._settings.cloud_profiles)
        profiles = [p for p in profiles if p.get("name") != name]
        self._settings.cloud_profiles = profiles
        self._settings.delete_api_key(f"cloud/{name}")
        self._populate_cloud_profiles_combo()

        # Clear fields
        self.cloud_endpoint_input.clear()
        self.cloud_api_key_input.clear()
        self.cloud_model_input.clear()
        self.cloud_region_input.clear()

        QMessageBox.information(self, "Deleted", f"Cloud profile '{name}' deleted.")

    def _on_cloud_test(self) -> None:
        """Test connection — no-op for now."""
        QMessageBox.information(
            self,
            "Test Connection",
            "Test not implemented yet.",
        )

    def _on_provider_changed(self, index: int) -> None:
        """Show/hide region field based on provider selection."""
        self._update_region_visibility()

    def _update_region_visibility(self) -> None:
        """Show region field only for AWS Transcribe."""
        provider = self.cloud_provider_combo.currentData()
        visible = provider == "aws"
        self._cloud_region_label.setVisible(visible)
        self.cloud_region_input.setVisible(visible)
