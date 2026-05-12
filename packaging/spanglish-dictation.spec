# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir packaging contract for Spanglish Dictation.

Generates a distributable folder at dist/spanglish-dictation/.
The portable zip build script stages this folder into dist/release/.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        (str(ROOT / "data" / "default_glossary.json"), "data"),
    ],
    hiddenimports=[
        "privacy_guard",
        "audio_capture",
        "speech_detector",
        "transcriber",
        "transcriber_worker",
        "model_manager",
        "profile_resolver",
        "hardware_detector",
        "dictation_loop",
        "post_processor",
        "glossary",
        "paste_controller",
        "shell_integration",
        "settings_store",
        "settings_dialog",
        "confirmation_dialog",
        "diagnostics",
        "pywin32",
        "win32api",
        "win32con",
        "win32gui",
        "win32clipboard",
        "webrtcvad",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "unittest",
        "email",
        "http",
        "xmlrpc",
        "pydoc",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="spanglish-dictation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="spanglish-dictation",
)
