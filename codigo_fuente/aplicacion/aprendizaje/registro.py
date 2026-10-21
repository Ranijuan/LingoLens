"""Guarda vocabulario y nivel del usuario en SQLite local."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone

from aplicacion.rutas import carpeta_datos


class RegistroAprendizaje:
    """Una conexión breve por operación evita compartir conexiones entre hilos."""

    def __init__(self) -> None:
        self.ruta = carpeta_datos() / "aprendizaje.sqlite3"
        self._crear_tablas()

    @contextmanager
    def _conectar(self) -> Iterator[sqlite3.Connection]:
        conexion = sqlite3.connect(self.ruta, timeout=5)
        conexion.execute("PRAGMA journal_mode=WAL")
        conexion.execute("PRAGMA busy_timeout=5000")
        try:
            with conexion:
                yield conexion
        finally:
            conexion.close()

    def _crear_tablas(self) -> None:
        with self._conectar() as db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS vocabulario (
                    palabra TEXT PRIMARY KEY COLLATE NOCASE,
                    significado TEXT NOT NULL,
                    ejemplo TEXT NOT NULL,
                    agregada_utc TEXT NOT NULL,
                    repeticiones INTEGER NOT NULL DEFAULT 1
                )"""
            )
            db.execute(
                """CREATE TABLE IF NOT EXISTS preferencias (
                    clave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL
                )"""
            )

    def guardar_palabra(self, palabra: str, significado: str, ejemplo: str) -> int:
        palabra = palabra.strip()[:80]
        if not palabra:
            return self.cantidad()
        fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._conectar() as db:
            db.execute(
                """INSERT INTO vocabulario(palabra, significado, ejemplo, agregada_utc)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(palabra) DO UPDATE SET
                     significado=excluded.significado,
                     ejemplo=excluded.ejemplo,
                     repeticiones=vocabulario.repeticiones + 1""",
                (palabra, significado[:300], ejemplo[:300], fecha),
            )
            return int(db.execute("SELECT COUNT(*) FROM vocabulario").fetchone()[0])

    def cantidad(self) -> int:
        with self._conectar() as db:
            return int(db.execute("SELECT COUNT(*) FROM vocabulario").fetchone()[0])

    def palabras(self, limite: int = 40) -> list[str]:
        with self._conectar() as db:
            filas = db.execute(
                "SELECT palabra FROM vocabulario ORDER BY agregada_utc DESC LIMIT ?",
                (max(1, min(limite, 100)),),
            ).fetchall()
        return [str(fila[0]) for fila in filas]

    def nivel(self) -> str:
        with self._conectar() as db:
            fila = db.execute(
                "SELECT valor FROM preferencias WHERE clave='nivel'"
            ).fetchone()
        return str(fila[0]) if fila else "A2"

    def guardar_nivel(self, nivel: str) -> None:
        nivel = nivel if nivel in {"A1", "A2", "B1", "B2", "C1"} else "A2"
        with self._conectar() as db:
            db.execute(
                """INSERT INTO preferencias(clave, valor) VALUES ('nivel', ?)
                   ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor""",
                (nivel,),
            )

    def modelo(self) -> str:
        with self._conectar() as db:
            fila = db.execute(
                "SELECT valor FROM preferencias WHERE clave='modelo'"
            ).fetchone()
        return str(fila[0]).strip() if fila else ""

    def guardar_modelo(self, nombre: str) -> None:
        nombre = nombre.strip()[:80]
        if not nombre:
            return
        with self._conectar() as db:
            db.execute(
                """INSERT INTO preferencias(clave, valor) VALUES ('modelo', ?)
                   ON CONFLICT(clave) DO UPDATE SET valor=excluded.valor""",
                (nombre,),
            )
