"""Rutas compartidas para desarrollo y para el ejecutable empaquetado."""

from __future__ import annotations

import sys
from pathlib import Path


def recurso(nombre: str) -> Path:
    """Busca un archivo incluido en el ejecutable o en el proyecto."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[1]
    return base / nombre


def carpeta_datos() -> Path:
    """Devuelve una carpeta de datos persistentes fuera del ejecutable."""
    raiz = Path.home() / "AppData" / "Local" / "LingoLens"
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz
