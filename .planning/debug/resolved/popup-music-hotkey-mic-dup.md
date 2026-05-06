---
status: resolved
trigger: "I keep getting: in the popup window: [Music] as the recorded things, also the shortcuts doesnt work at all, each app always have a mapping with ctrl so I guess it doesnt trigger, also the input devices detected I want to use the microphone of the camera Logitech Brio but I see it repeated like 4 times, I know the mic works but the apps read it properly?"
created: "2026-05-05"
updated: "2026-05-05"
---

# Debug Session: Popup Music Hotkey Mic Dup

## Symptoms

- expected_behavior: When using the shortcut, the app should start recording from the selected microphone anywhere, show a meaningful recording overlay, and transcribe the spoken voice.
- actual_behavior: Shortcuts do not work, the preferred microphone appears duplicated several times and does not seem to activate correctly, and the overlay is unclear and not meaningful.
- error_messages: |
    Popup text can show: [Music]
    Console output:
    requestActivate() called for QWidgetWindow(0x2c0b9baa970, name="QWidgetClassWindow") which has Qt::WindowDoesNotAcceptFocus set.
    UpdateLayeredWindowIndirect failed for ptDst=(1679, 951), size=(248x60), dirty=(288x100 -20, -14) (El parßmetro no es correcto.)
    requestActivate() called for QWidgetWindow(0x2c0b9baa970, name="QWidgetClassWindow") which has Qt::WindowDoesNotAcceptFocus set.
    Progress:   0%
    Progress: 100%
    requestActivate() called for QWidgetWindow(0x2c0b9baa970, name="QWidgetClassWindow") which has Qt::WindowDoesNotAcceptFocus set.
    UpdateLayeredWindowIndirect failed for ptDst=(1679, 951), size=(261x60), dirty=(301x100 -20, -14) (El parßmetro no es correcto.)
    requestActivate() called for QWidgetWindow(0x2c0b9baa970, name="QWidgetClassWindow") which has Qt::WindowDoesNotAcceptFocus set.
    UpdateLayeredWindowIndirect failed for ptDst=(1679, 951), size=(261x60), dirty=(301x100 -20, -14) (El parßmetro no es correcto.)
    UpdateLayeredWindowIndirect failed for ptDst=(1679, 951), size=(261x60), dirty=(301x100 -20, -14) (El parßmetro no es correcto.)
- timeline: Never worked.
- reproduction: Start the app, then press the Start Dictation button. Shortcuts also do not work when pressed.

## Current Focus

- hypothesis: Global hotkey registration may be failing or conflicting with modifier parsing, microphone enumeration may be surfacing duplicate WASAPI endpoints without clear labeling, and the overlay window flags/layout may be producing the Qt warnings and confusing status text.
- test: Inspect hotkey registration, input-device listing/selection, and overlay status rendering paths.
- expecting: The app likely has separate issues in ShellIntegration/overlay behavior and audio device presentation, with `[Music]` coming from status text or transcription handling rather than actual dictation success.
- next_action: complete
- reasoning_checkpoint:
- tdd_checkpoint:

## Evidence

- timestamp: 2026-05-05T00:00:00Z
  finding: Global hotkey registration is hardcoded to Ctrl+Alt+D and ignores saved settings.
  evidence:
    - src/shell_integration.py:123-136 registers only one Win32 hotkey using MOD_CONTROL | MOD_ALT and ord("D").
    - src/settings_dialog.py:270-288 saves both hotkey fields, but no code re-reads or parses them during registration.
    - src/main.py:182-185 calls shell.register_hotkeys() once at startup and connects only a single emitted hotkey to dictation_loop.toggle().

- timestamp: 2026-05-05T00:00:00Z
  finding: The selected microphone is only captured once at startup, while the UI exposes raw duplicated PortAudio device names.
  evidence:
    - src/main.py:134 constructs AudioCapture(device_index=settings.audio_device_index) once during app startup.
    - src/settings_dialog.py:162-185 lists devices by raw name/index and can save a new audio_device_index, but no runtime code updates the existing AudioCapture instance afterward.
    - src/audio_capture.py:208-224 returns every input-capable PortAudio device without host API labeling or deduplication, which can surface the same physical Logitech Brio mic multiple times.

- timestamp: 2026-05-05T00:00:00Z
  finding: The overlay is using conflicting window behavior that matches the Qt warnings seen by the user.
  evidence:
    - src/shell_integration.py:357-362 sets Qt.WindowDoesNotAcceptFocus on the panel.
    - src/shell_integration.py:335-338 immediately calls panel.activateWindow(), which explains the requestActivate warning.
    - src/shell_integration.py:363 and 386-390 combine WA_TranslucentBackground with a drop shadow effect on a frameless tool window, consistent with the UpdateLayeredWindowIndirect errors and negative dirty rect logs.

- timestamp: 2026-05-05T00:00:00Z
  finding: Approved fixes were implemented for hotkey registration, audio-device labeling/application, and overlay presentation.
  evidence:
    - src/shell_integration.py now parses and registers configured hotkeys, refreshes them after settings changes, and shows the panel without focus activation.
    - src/audio_capture.py now exposes clearer device labels with host API/channel info, removes exact duplicate input entries, and allows the selected device index to be refreshed for later captures.
    - src/main.py and src/settings_dialog.py now propagate saved settings so the chosen audio device is applied to the existing capture service.
    - tests/test_audio_capture.py, tests/test_settings_dialog.py, and tests/test_shell_integration.py cover the new behavior.

## Eliminated

## Resolution

- root_cause: Multiple UI integration bugs are stacked together: hotkeys are hardcoded instead of using configured settings, microphone selection is not reapplied after settings changes and raw PortAudio devices are shown without normalization, and the overlay activates a non-focusable translucent window configuration that triggers the observed Qt warnings.
- fix: ShellIntegration now registers the saved global hotkeys and refreshes them after settings changes, AudioCapture surfaces deduplicated labeled microphone entries and applies the selected device on later captures, and the overlay no longer tries to focus a non-focusable translucent popup.
- verification:
    - `pytest tests/test_audio_capture.py tests/test_settings_dialog.py tests/test_shell_integration.py` ✅ (60 passed)
    - Followed by the later post-Phase 5 bug-fix session that the user reported as green end-to-end with `378 passed, 3 skipped`.
- files_changed:
    - src/audio_capture.py
    - src/main.py
    - src/settings_dialog.py
    - src/shell_integration.py
    - tests/test_audio_capture.py
    - tests/test_settings_dialog.py
    - tests/test_shell_integration.py
