"""Pruebas automáticas de LingoLens."""

from pathlib import Path
import sys


RUTA_CODIGO = Path(__file__).resolve().parents[1] / "codigo_fuente"
if str(RUTA_CODIGO) not in sys.path:
    sys.path.insert(0, str(RUTA_CODIGO))
