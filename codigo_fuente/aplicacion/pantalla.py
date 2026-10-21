"""Captura la pantalla y ejecuta OCR local solo cuando hay cambios visibles."""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import tempfile
import threading
import zipfile
from dataclasses import dataclass
from pathlib import Path

import mss
from PIL import Image, ImageDraw, ImageOps

from aplicacion.puente_nucleo import Nucleo
from aplicacion.rutas import recurso


@dataclass(slots=True)
class ResultadoPantalla:
    texto: str
    vista: Image.Image
    hubo_cambios: bool


_BLOQUEO_TESSERACT = threading.Lock()
_MAX_PALABRAS_OCR = 250


def _extraer_tesseract(archivo: Path) -> tuple[Path, Path]:
    """Extrae el OCR empaquetado fuera del directorio temporal de PyInstaller."""
    destino = Path(tempfile.gettempdir()) / "LingoLens" / "tesseract"
    ejecutable = destino / "tesseract.exe"
    datos = destino / "tessdata"
    if ejecutable.is_file() and datos.is_dir():
        return ejecutable, datos

    with _BLOQUEO_TESSERACT:
        if ejecutable.is_file() and datos.is_dir():
            return ejecutable, datos
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporal = Path(tempfile.mkdtemp(prefix="lingolens-tesseract-"))
        try:
            with zipfile.ZipFile(archivo) as comprimido:
                comprimido.extractall(temporal)
            if not (temporal / "tesseract.exe").is_file():
                raise FileNotFoundError("El paquete interno de Tesseract está incompleto.")
            if destino.exists():
                shutil.rmtree(destino)
            temporal.replace(destino)
        finally:
            if temporal.exists():
                shutil.rmtree(temporal, ignore_errors=True)
    return ejecutable, datos


def _ruta_tesseract() -> tuple[Path, Path]:
    ejecutable = recurso("tesseract/tesseract.exe")
    datos = recurso("tesseract/tessdata")
    if ejecutable.is_file() and datos.is_dir():
        return ejecutable, datos
    comprimido = recurso("recursos/tesseract.zip")
    if comprimido.is_file():
        return _extraer_tesseract(comprimido)
    externo = Path("C:/Program Files/Tesseract-OCR")
    return externo / "tesseract.exe", externo / "tessdata"


def _ocultar_ventana(
    imagen: Image.Image,
    geometria: tuple[int, int, int, int] | None,
    origen: tuple[int, int],
) -> None:
    """Pinta de blanco la ventana de LingoLens para no leer sus propios textos."""
    if not geometria:
        return
    x, y, ancho, alto = geometria
    x -= origen[0]
    y -= origen[1]
    if ancho > 0 and alto > 0:
        ImageDraw.Draw(imagen).rectangle(
            (x, y, x + ancho, y + alto), fill=(255, 255, 255)
        )


def _normalizar_texto(texto: str) -> str:
    parrafos: list[str] = []
    vistos: set[str] = set()
    for bloque in re.split(r"\n\s*\n", texto):
        lineas: list[str] = []
        for linea in bloque.splitlines():
            limpia = re.sub(r"\s+", " ", linea).strip(" |·—-\t")
            clave = limpia.casefold()
            if len(limpia) >= 2 and clave not in vistos:
                lineas.append(limpia)
                vistos.add(clave)
        if lineas:
            parrafos.append(" ".join(lineas))

    seleccionadas: list[str] = []
    usadas = 0
    for parrafo in parrafos:
        partes = re.split(r"(?<=[.!?])\s+", parrafo)
        completas = [
            parte.strip()
            for parte in partes
            if re.search(r"[.!?][\"')\]]*$", parte.strip())
        ]
        candidatas = completas or ([parrafo] if len(parrafo.split()) <= _MAX_PALABRAS_OCR else [])
        for oracion in candidatas:
            cantidad = len(oracion.split())
            if cantidad and usadas + cantidad <= _MAX_PALABRAS_OCR:
                seleccionadas.append(oracion)
                usadas += cantidad
    return " ".join(seleccionadas)


def capturar_y_leer(
    nucleo: Nucleo,
    idioma: str,
    geometria: tuple[int, int, int, int] | None,
) -> ResultadoPantalla:
    """Captura todos los monitores y devuelve texto OCR si la imagen cambió."""
    ejecutable, carpeta_datos = _ruta_tesseract()
    if not ejecutable.is_file():
        raise FileNotFoundError("No se encontró Tesseract, incluido en LingoLens.")
    codigo_idioma = "eng" if idioma == "inglés" else "spa"
    archivo_idioma = carpeta_datos / f"{codigo_idioma}.traineddata"
    if not archivo_idioma.is_file():
        raise FileNotFoundError(f"Falta el paquete de OCR para {idioma}.")

    with mss.mss() as capturador:
        monitor = capturador.monitors[0]
        toma = capturador.grab(monitor)
        imagen = Image.frombytes("RGB", toma.size, toma.bgra, "raw", "BGRX")
        _ocultar_ventana(
            imagen,
            geometria,
            (int(monitor["left"]), int(monitor["top"])),
        )
        bytes_bgra = imagen.tobytes("raw", "BGRX")
        cambio = nucleo.cambio(
            bytes_bgra,
            imagen.width,
            imagen.height,
            imagen.width * 4,
        )

        vista = imagen.copy()
        vista.thumbnail((480, 270), Image.Resampling.LANCZOS)
        if not cambio:
            return ResultadoPantalla("", vista, False)

        procesada = ImageOps.autocontrast(ImageOps.grayscale(imagen))
        if procesada.width > 2560:
            alto = round(procesada.height * 2560 / procesada.width)
            procesada = procesada.resize((2560, alto), Image.Resampling.LANCZOS)
        salida = io.BytesIO()
        procesada.save(salida, format="PNG", optimize=True)

    opciones = {
        "capture_output": True,
        "input": salida.getvalue(),
        "timeout": 14,
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }
    try:
        resultado = subprocess.run(
            [
                str(ejecutable),
                "stdin",
                "stdout",
                "--oem",
                "1",
                "--psm",
                "11",
                "-l",
                codigo_idioma,
                "--tessdata-dir",
                str(carpeta_datos),
            ],
            **opciones,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise TimeoutError("El OCR tardó demasiado; vuelve a intentarlo.") from error

    if resultado.returncode != 0:
        detalle = resultado.stderr.decode("utf-8", errors="replace")[:260]
        raise RuntimeError(f"Tesseract no pudo leer la pantalla: {detalle}")
    texto = resultado.stdout.decode("utf-8", errors="replace")
    return ResultadoPantalla(_normalizar_texto(texto), vista, True)
