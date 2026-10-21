"""Perfil de aprendizaje cifrado con DPAPI para el usuario actual de Windows."""

from __future__ import annotations

import ctypes
import json
import os
import re
from ctypes import wintypes
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any


_MAX_EVENTOS = 200
_MAX_PALABRAS = 500
_MAX_PALABRAS_EVENTO = 40
_TOKEN = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)?", re.UNICODE)


class _Blob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _proteger(datos: bytes) -> bytes:
    """Cifra datos con la clave de usuario de Windows."""
    if os.name != "nt":
        raise RuntimeError("El perfil seguro solo está disponible en Windows.")
    entrada, referencia = _crear_blob(datos)
    salida = _Blob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptProtectData.argtypes = (
        ctypes.POINTER(_Blob),
        wintypes.LPCWSTR,
        ctypes.POINTER(_Blob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_Blob),
    )
    crypt32.CryptProtectData.restype = wintypes.BOOL
    if not crypt32.CryptProtectData(
        ctypes.byref(entrada),
        "LingoLens perfil de aprendizaje",
        None,
        None,
        None,
        1,
        ctypes.byref(salida),
    ):
        raise ctypes.WinError()
    return _leer_blob_y_liberar(salida)


def _desproteger(datos: bytes) -> bytes:
    """Descifra datos que protegió el mismo usuario de Windows."""
    if os.name != "nt":
        raise RuntimeError("El perfil seguro solo está disponible en Windows.")
    entrada, referencia = _crear_blob(datos)
    salida = _Blob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptUnprotectData.argtypes = (
        ctypes.POINTER(_Blob),
        ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(_Blob),
        wintypes.LPVOID,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(_Blob),
    )
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    descripcion = wintypes.LPWSTR()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(entrada),
        ctypes.byref(descripcion),
        None,
        None,
        None,
        1,
        ctypes.byref(salida),
    ):
        raise ctypes.WinError()
    if descripcion:
        ctypes.windll.kernel32.LocalFree(descripcion)
    return _leer_blob_y_liberar(salida)


def _crear_blob(datos: bytes) -> tuple[_Blob, Any]:
    referencia = (ctypes.c_ubyte * len(datos)).from_buffer_copy(datos)
    return _Blob(len(datos), referencia), referencia


def _leer_blob_y_liberar(blob: _Blob) -> bytes:
    datos = ctypes.string_at(blob.pbData, blob.cbData)
    ctypes.windll.kernel32.LocalFree(blob.pbData)
    return datos


def _nuevo_perfil() -> dict[str, Any]:
    return {
        "version": 1,
        "nivel": "A2",
        "idioma": "inglés",
        "interacciones": 0,
        "palabras": {},
        "historial": [],
    }


def _tokens(texto: str) -> list[str]:
    vistos: set[str] = set()
    resultado: list[str] = []
    for token in _TOKEN.findall(texto.casefold()):
        if len(token) < 2 or token in vistos:
            continue
        vistos.add(token)
        resultado.append(token)
    return resultado[:_MAX_PALABRAS_EVENTO]


class PerfilSeguro:
    """Guarda señales de aprendizaje, sin almacenar el texto de la pantalla."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        self._bloqueo = RLock()

    def _leer(self) -> dict[str, Any]:
        if not self.ruta.is_file():
            return _nuevo_perfil()
        try:
            datos = _desproteger(self.ruta.read_bytes())
            perfil = json.loads(datos.decode("utf-8"))
        except (OSError, ValueError, TypeError, RuntimeError):
            return _nuevo_perfil()
        if not isinstance(perfil, dict):
            return _nuevo_perfil()
        base = _nuevo_perfil()
        base.update(perfil)
        if not isinstance(base.get("palabras"), dict):
            base["palabras"] = {}
        if not isinstance(base.get("historial"), list):
            base["historial"] = []
        return base

    def _guardar(self, perfil: dict[str, Any]) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        contenido = json.dumps(
            perfil,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        temporal = self.ruta.with_suffix(self.ruta.suffix + ".tmp")
        temporal.write_bytes(_proteger(contenido))
        os.replace(temporal, self.ruta)

    def establecer_contexto(self, nivel: str, idioma: str) -> None:
        with self._bloqueo:
            perfil = self._leer()
            perfil["nivel"] = nivel if nivel in {"A1", "A2", "B1", "B2", "C1"} else "A2"
            perfil["idioma"] = idioma[:30]
            self._guardar(perfil)

    def registrar(
        self,
        tipo: str,
        idioma: str,
        texto: str,
        dificultad: bool = False,
    ) -> None:
        """Guarda solo palabras y métricas, nunca el texto completo."""
        palabras = _tokens(texto)
        with self._bloqueo:
            perfil = self._leer()
            ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
            perfil["interacciones"] = int(perfil.get("interacciones", 0)) + 1
            por_palabra = perfil["palabras"]
            for palabra in palabras:
                actual = por_palabra.setdefault(
                    palabra,
                    {"vistas": 0, "dificultad": 0, "ultima": ahora},
                )
                actual["vistas"] = int(actual.get("vistas", 0)) + 1
                actual["dificultad"] = int(actual.get("dificultad", 0)) + int(dificultad)
                actual["ultima"] = ahora
            if len(por_palabra) > _MAX_PALABRAS:
                ordenadas = sorted(
                    por_palabra.items(),
                    key=lambda item: str(item[1].get("ultima", "")),
                    reverse=True,
                )
                perfil["palabras"] = dict(ordenadas[:_MAX_PALABRAS])
            historial = perfil["historial"]
            historial.append(
                {
                    "fecha": ahora,
                    "tipo": tipo[:30],
                    "idioma": idioma[:30],
                    "palabras": palabras,
                }
            )
            perfil["historial"] = historial[-_MAX_EVENTOS:]
            self._guardar(perfil)

    def resumen(self) -> dict[str, Any]:
        with self._bloqueo:
            perfil = self._leer()
        palabras = perfil["palabras"]
        practicas = sorted(
            (
                palabra,
                int(datos.get("vistas", 0)),
                int(datos.get("dificultad", 0)),
            )
            for palabra, datos in palabras.items()
            if isinstance(datos, dict)
        )
        practicas.sort(key=lambda item: (item[2], item[1]), reverse=True)
        return {
            "nivel": str(perfil.get("nivel", "A2")),
            "idioma": str(perfil.get("idioma", "inglés")),
            "interacciones": int(perfil.get("interacciones", 0)),
            "palabras_practicadas": len(palabras),
            "palabras_dificiles": [palabra for palabra, _, _ in practicas[:8]],
            "historial_reciente": list(perfil["historial"][-8:]),
        }

    def comprobar_proteccion(self) -> bool:
        """Comprueba DPAPI en memoria sin crear ni modificar el perfil del usuario."""
        prueba = b"LingoLens-DPAPI"
        with self._bloqueo:
            return _desproteger(_proteger(prueba)) == prueba
