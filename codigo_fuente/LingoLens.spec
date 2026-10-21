# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.building.datastruct import TOC


raiz = Path(SPECPATH).resolve()
nucleo = raiz / "nucleo" / "bin" / "nucleo.dll"
archivo_tesseract = raiz / "recursos" / "tesseract.zip"
runtime_hook_qt = raiz / "aplicacion" / "qt_runtime_hook.py"

a = Analysis(
    [str(raiz / "aplicacion" / "main.py")],
    pathex=[str(raiz)],
    binaries=[(str(nucleo), ".")],
    datas=[(str(archivo_tesseract), "recursos")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(runtime_hook_qt)],
    excludes=[],
    noarchive=False,
    optimize=0,
)

binaries = TOC()
for destino, origen, tipo in a.binaries:
    nombre = Path(destino).name.casefold()
    if nombre.startswith("icu") and nombre.endswith(".dll"):
        continue
    binaries.append((destino, origen, tipo))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    binaries,
    a.datas,
    [],
    name="LingoLens",
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
