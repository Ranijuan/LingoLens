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
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        )
        funcion.restype = ctypes.c_int
        self._comparar = funcion
        self._reset = self._dll.tp_reiniciar
        self._reset.argtypes = ()
        self._reset.restype = None
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
            resultado = self._comparar(buffer, ancho, alto, paso, 36)
        if resultado < 0:
            raise RuntimeError("El núcleo C no pudo comparar la captura.")
        return resultado == 1

    def reiniciar(self) -> None:
        with self._bloqueo:
            self._reset()
