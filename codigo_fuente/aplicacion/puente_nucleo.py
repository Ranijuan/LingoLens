"""Puente pequeño y seguro entre Python y el núcleo optimizado en C."""

from __future__ import annotations

import ctypes
import threading

from aplicacion.rutas import recurso


class Nucleo:
    """Carga la DLL y compara capturas sin bloquear la interfaz."""

    def __init__(self) -> None:
        ruta = recurso("nucleo.dll")
        if not ruta.is_file():
            ruta = recurso("nucleo/bin/nucleo.dll")
        self._dll = ctypes.CDLL(str(ruta))
        funcion = self._dll.tp_detectar_cambio
        funcion.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        )
        funcion.restype = ctypes.c_int
        self._comparar = funcion
        crear = self._dll.tp_crear
        crear.argtypes = ()
        crear.restype = ctypes.c_void_p
        self._contexto = crear()
        if not self._contexto:
            raise MemoryError("El núcleo C no pudo reservar su contexto.")
        self._reset = self._dll.tp_reiniciar
        self._reset.argtypes = (ctypes.c_void_p,)
        self._reset.restype = None
        self._destruir = self._dll.tp_destruir
        self._destruir.argtypes = (ctypes.c_void_p,)
        self._destruir.restype = None
        self._bloqueo = threading.Lock()

    def cambio(self, datos: bytes, ancho: int, alto: int, paso: int) -> bool:
        """Actualiza la captura guardada y avisa si cambió suficiente."""
        if (
            ancho <= 0
            or alto <= 0
            or paso < ancho * 4
            or len(datos) != paso * alto
        ):
            raise ValueError("La captura tiene dimensiones no válidas.")
        buffer = (ctypes.c_uint8 * len(datos)).from_buffer_copy(datos)
        with self._bloqueo:
            if self._contexto is None:
                raise RuntimeError("El núcleo C ya está cerrado.")
            resultado = self._comparar(
                self._contexto, buffer, ancho, alto, paso, 36
            )
        if resultado < 0:
            raise RuntimeError("El núcleo C no pudo comparar la captura.")
        return resultado == 1

    def reiniciar(self) -> None:
        with self._bloqueo:
            if self._contexto is not None:
                self._reset(self._contexto)

    def cerrar(self) -> None:
        """Libera la memoria nativa asociada a esta instancia."""
        with self._bloqueo:
            if self._contexto is not None:
                self._destruir(self._contexto)
                self._contexto = None

    def __enter__(self) -> "Nucleo":
        return self

    def __exit__(self, *_: object) -> None:
        self.cerrar()

    def __del__(self) -> None:
        try:
            self.cerrar()
        except Exception:
            pass
