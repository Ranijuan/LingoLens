"""Prepara las rutas nativas de Qt antes de iniciar la interfaz."""

from __future__ import annotations

import os
import sys
from pathlib import Path


if sys.platform == "win32" and getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
    rutas = (base / "PySide6", base)
    for ruta in rutas:
        if ruta.is_dir():
            os.add_dll_directory(str(ruta))
            os.environ["PATH"] = str(ruta) + os.pathsep + os.environ.get("PATH", "")
