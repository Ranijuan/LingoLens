"""Comprobaciones de primer arranque sin bloquear la interfaz."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from aplicacion.aprendizaje.perfil_seguro import PerfilSeguro
from aplicacion.rutas import carpeta_datos


class AsistenteComprobable(Protocol):
    modelo: str

    def disponible(self) -> bool:
        ...

    def modelos_instalados(self) -> set[str]:
        ...


@dataclass(frozen=True, slots=True)
class ResultadoChequeo:
    """Resultado pequeño y serializable para mostrar un chequeo en la interfaz."""

    clave: str
    titulo: str
    estado: str
    detalle: str
    solucion: str = ""
    modelos: tuple[str, ...] = ()


def _correcto(clave: str, titulo: str, detalle: str) -> ResultadoChequeo:
    return ResultadoChequeo(clave, titulo, "correcto", detalle)


def _advertencia(
    clave: str,
    titulo: str,
    detalle: str,
    solucion: str,
) -> ResultadoChequeo:
    return ResultadoChequeo(clave, titulo, "advertencia", detalle, solucion)


def _error(
    clave: str,
    titulo: str,
    detalle: str,
    solucion: str,
) -> ResultadoChequeo:
    return ResultadoChequeo(clave, titulo, "error", detalle, solucion)


def _comprobar_datos(ruta: Path) -> ResultadoChequeo:
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix="diagnostico-",
            suffix=".tmp",
            dir=ruta,
            delete=False,
        ) as temporal:
            temporal.write(b"LingoLens")
            nombre = Path(temporal.name)
        nombre.unlink(missing_ok=True)
    except OSError as error:
        return _error(
            "datos",
            "Almacenamiento local",
            f"No se puede escribir en {ruta}: {error}",
            "Comprueba los permisos de la carpeta de datos de LingoLens.",
        )
    return _correcto("datos", "Almacenamiento local", f"Se puede escribir en {ruta}.")


def _comprobar_perfil(ruta: Path) -> ResultadoChequeo:
    try:
        if not PerfilSeguro(ruta / "perfil_aprendizaje.seguro").comprobar_proteccion():
            raise RuntimeError("la prueba de cifrado no devolvió los datos originales")
    except Exception as error:  # Un diagnóstico fallido no debe cerrar la aplicación.
        return _error(
            "perfil",
            "Perfil de aprendizaje",
            f"No se pudo comprobar el cifrado DPAPI: {error}",
            "Usa una cuenta de Windows con perfil local disponible y vuelve a intentarlo.",
        )
    return _correcto(
        "perfil",
        "Perfil de aprendizaje",
        "El cifrado DPAPI de Windows está disponible para este usuario.",
    )


def _comprobar_nucleo() -> ResultadoChequeo:
    try:
        from aplicacion.puente_nucleo import Nucleo

        nucleo = Nucleo()
        nucleo.cerrar()
    except Exception as error:  # La DLL puede faltar en una distribución incompleta.
        return _error(
            "nucleo",
            "Núcleo C",
            f"No se pudo cargar la DLL nativa: {error}",
            "Reconstruye el núcleo C o vuelve a descargar la distribución completa.",
        )
    return _correcto("nucleo", "Núcleo C", "La DLL nativa se cargó y liberó correctamente.")


def _comprobar_ocr() -> ResultadoChequeo:
    try:
        from aplicacion.pantalla import _ruta_tesseract

        ejecutable, datos = _ruta_tesseract()
        faltantes = [
            str(ruta)
            for ruta in (
                ejecutable,
                datos / "eng.traineddata",
                datos / "spa.traineddata",
            )
            if not ruta.is_file()
        ]
    except Exception as error:  # Un paquete OCR dañado debe aparecer como diagnóstico.
        return _error(
            "ocr",
            "OCR de pantalla",
            f"No se pudo localizar Tesseract: {error}",
            "Vuelve a extraer el ZIP completo o reconstruye el ejecutable.",
        )
    if faltantes:
        return _error(
            "ocr",
            "OCR de pantalla",
            "Faltan recursos: " + ", ".join(faltantes),
            "Descarga la distribución completa de LingoLens.",
        )
    return _correcto("ocr", "OCR de pantalla", "Tesseract y los idiomas inglés/español están listos.")


def _modelo_disponible(modelo: str, modelos: set[str]) -> bool:
    return any(nombre == modelo or nombre.startswith(modelo + ":") for nombre in modelos)


def comprobar_entorno(
    asistente: AsistenteComprobable,
    ruta: Path | None = None,
) -> list[ResultadoChequeo]:
    """Comprueba las dependencias locales y devuelve siempre todos los resultados."""
    if os.name == "nt":
        sistema = _correcto("sistema", "Windows", "Sistema operativo compatible detectado.")
    else:
        sistema = _advertencia(
            "sistema",
            "Windows",
            "La aplicación está diseñada para Windows.",
            "Usa la distribución oficial en Windows para disponer de DPAPI y captura de pantalla.",
        )

    try:
        carpeta = ruta or carpeta_datos()
        datos = _comprobar_datos(carpeta)
        perfil = _comprobar_perfil(carpeta)
    except OSError as error:
        carpeta = Path(".")
        datos = _error(
            "datos",
            "Almacenamiento local",
            f"No se pudo preparar la carpeta de datos: {error}",
            "Comprueba que la carpeta de usuario esté disponible.",
        )
        perfil = _error(
            "perfil",
            "Perfil de aprendizaje",
            "No se pudo localizar la carpeta del perfil.",
            "Revisa los permisos de la carpeta de datos.",
        )

    resultados = [sistema, datos, perfil, _comprobar_nucleo(), _comprobar_ocr()]

    try:
        servidor = asistente.disponible()
    except Exception as error:  # La comprobación nunca debe cerrar la aplicación.
        servidor = False
        detalle_servidor = f"No se pudo consultar Ollama: {error}"
    else:
        detalle_servidor = (
            "Ollama responde en 127.0.0.1:11434."
            if servidor
            else "Ollama no responde en 127.0.0.1:11434."
        )
    if servidor:
        ollama = _correcto("ollama", "Ollama", detalle_servidor)
    else:
        ollama = _advertencia(
            "ollama",
            "Ollama",
            detalle_servidor,
            "Abre Ollama o pulsa «Preparar IA local». El OCR seguirá funcionando.",
        )
    resultados.append(ollama)

    if not servidor:
        resultados.append(
            _advertencia(
                "modelo",
                "Modelo de IA",
                f"No se pudo comprobar {asistente.modelo} porque Ollama no está disponible.",
                "Inicia Ollama y vuelve a revisar el diagnóstico.",
            )
        )
        return resultados

    try:
        modelos = {modelo for modelo in asistente.modelos_instalados() if modelo}
    except Exception as error:  # La aplicación puede seguir usando OCR.
        resultados.append(
            _advertencia(
                "modelo",
                "Modelo de IA",
                f"Ollama responde, pero no se pudo leer la lista de modelos: {error}",
                "Comprueba Ollama y vuelve a revisar el diagnóstico.",
            )
        )
        return resultados

    if _modelo_disponible(asistente.modelo, modelos):
        resultados.append(
            ResultadoChequeo(
                "modelo",
                "Modelo de IA",
                "correcto",
                f"Está instalado {asistente.modelo}.",
                modelos=tuple(sorted(modelos)),
            )
        )
    else:
        nombres = ", ".join(sorted(modelos)[:4]) or "ninguno"
        resultados.append(
            ResultadoChequeo(
                "modelo",
                "Modelo de IA",
                "advertencia",
                f"Falta {asistente.modelo}. Modelos detectados: {nombres}.",
                "Pulsa «Preparar IA local» o selecciona un modelo instalado.",
                tuple(sorted(modelos)),
            )
        )
    return resultados
