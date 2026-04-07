# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [
    ('gesture', 'gesture'),
    ('voice_assistant', 'voice_assistant'),
    ('extensions', 'extensions'),
    ('controller', 'controller'),
    ('ui', 'ui'),
    ('storage', 'storage'),
]
binaries = []
hiddenimports = [
    'PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets',
    'cv2', 'mediapipe', 'numpy',
    'pyautogui', 'pyaudio',
    'vosk',
    'pyttsx3', 'pyttsx3.drivers', 'pyttsx3.drivers.sapi5',
    'speech_recognition',
    'screen_brightness_control', 'screen_brightness_control.windows',
    'pycaw', 'pycaw.pycaw',
    'comtypes', 'comtypes.client', 'comtypes.server',
    'fuzzywuzzy', 'fuzzywuzzy.fuzz', 'fuzzywuzzy.process',
    'Levenshtein',
    'logging', 'logging.handlers',
    'sqlite3',
    'tempfile', 'threading', 'subprocess',
    'difflib', 'json', 'queue', 'pathlib',
    'math', 'wave', 'struct',
]

tmp_ret = collect_all('vosk')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('pyaudio')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('pyttsx3')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

tmp_ret = collect_all('screen_brightness_control')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

hiddenimports += collect_submodules('comtypes')
hiddenimports += collect_submodules('pycaw')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='G-Vox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='G-Vox',
)
