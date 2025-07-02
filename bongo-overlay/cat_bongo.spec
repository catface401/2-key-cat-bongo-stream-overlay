# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['cat_overlay_gui.py'],
    pathex=[],
    binaries=[],
    datas=[('keybinds.txt', '.'), ('sensitivity.txt', '.'), ('bothslap.png', '.'), ('idle.png', '.'), ('leftslap.png', '.'), ('rightslap.png', '.'), ('talking.png', '.')],
    hiddenimports=['PIL', 'PIL.Image'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='cat_bongo',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
