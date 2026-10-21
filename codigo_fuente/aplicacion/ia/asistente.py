"""Tutoría de idiomas con traducción y conversación mediante Ollama local."""

from __future__ import annotations

import json
import queue
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import requests


URL_OLLAMA = "http://127.0.0.1:11434"
MODELO_POR_DEFECTO = "qwen2.5:1.5b"
TIEMPO_ESPERA = 180
_MODELO_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")


@dataclass(frozen=True, slots=True)
class ModeloRecomendado:
    """Información breve para ayudar a elegir un modelo local."""

    nombre: str
    titulo: str
    tamano: str
    descripcion: str


MODELOS_RECOMENDADOS = (
    ModeloRecomendado(
        "qwen2.5:1.5b",
        "Rápido y ligero",
        "~1 GB",
        "Para equipos modestos y primeras pruebas.",
    ),
    ModeloRecomendado(
        "qwen3:8b",
        "Equilibrado",
        "~5,2 GB",
        "Mejor calidad para conversación y explicaciones.",
    ),
    ModeloRecomendado(
        "gemma4:26b",
        "Avanzado",
        "~18 GB",
        "Respuestas más elaboradas; necesita más memoria y tiempo.",
    ),
)


def nombre_modelo_valido(nombre: str) -> bool:
    """Acepta nombres de Ollama sin permitir argumentos o comandos extra."""
    return bool(_MODELO_VALIDO.fullmatch(nombre.strip()))


def buscar_ollama() -> str | None:
    """Encuentra Ollama sin asumir una ruta fija de instalación."""
    encontrado = shutil.which("ollama")
    if encontrado:
        return encontrado
    rutas = (
        Path.home() / "AppData/Local/Programs/Ollama/ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
    )
    return next((str(ruta) for ruta in rutas if ruta.is_file()), None)


class AsistenteLocal:
    """Usa la API local de Ollama; los modelos ``:cloud`` pueden usar Ollama Cloud."""

    def __init__(self, modelo: str = MODELO_POR_DEFECTO) -> None:
        self.modelo = modelo
        self._proceso: subprocess.Popen[bytes] | None = None

    def _detener_proceso_propietario(self) -> None:
        """Detiene el servidor que esta instancia inició, si sigue activo."""
        proceso = self._proceso
        self._proceso = None
        if proceso is None or proceso.poll() is not None:
            return
        proceso.terminate()
        try:
            proceso.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proceso.kill()
            proceso.wait(timeout=2)

    def iniciar_servidor(self) -> bool:
        """Inicia Ollama oculto si su API local todavía no está activa."""
        if self.disponible():
            return True
        if self._proceso is not None and self._proceso.poll() is None:
            return self._esperar_servidor()
        ejecutable = buscar_ollama()
        if not ejecutable:
            return False
        opciones: dict[str, Any] = {
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            opciones["creationflags"] = subprocess.CREATE_NO_WINDOW
        try:
            self._proceso = subprocess.Popen([ejecutable, "serve"], **opciones)
        except OSError:
            return False
        return self._esperar_servidor()

    def _esperar_servidor(self) -> bool:
        """Espera unos segundos a que la API local acepte conexiones."""
        fin = time.monotonic() + 10
        while time.monotonic() < fin:
            if self.disponible():
                return True
            time.sleep(0.25)
        self._detener_proceso_propietario()
        return False

    def disponible(self) -> bool:
        try:
            respuesta = requests.get(f"{URL_OLLAMA}/api/tags", timeout=1.2)
            return respuesta.ok
        except requests.RequestException:
            return False

    def modelos_instalados(self) -> set[str]:
        respuesta = requests.get(f"{URL_OLLAMA}/api/tags", timeout=3)
        respuesta.raise_for_status()
        return {
            str(item.get("name", ""))
            for item in respuesta.json().get("models", [])
        }

    def instalar_modelo(
        self,
        modelo: str | None = None,
        progreso: Callable[[str], None] | None = None,
    ) -> None:
        """Descarga un modelo validado y comunica el progreso recibido de Ollama."""
        modelo_objetivo = (modelo or self.modelo).strip()
        if not nombre_modelo_valido(modelo_objetivo):
            raise ValueError("El nombre del modelo contiene caracteres no permitidos.")
        ejecutable = buscar_ollama()
        if not ejecutable:
            raise RuntimeError("Instala Ollama para preparar el asistente local.")
        if not self.iniciar_servidor():
            raise RuntimeError("No se pudo iniciar Ollama en este equipo.")
        proceso = subprocess.Popen(
            [ejecutable, "pull", modelo_objetivo],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        lineas: queue.Queue[str | None] = queue.Queue()

        def leer_salida() -> None:
            assert proceso.stdout is not None
            for linea in proceso.stdout:
                lineas.put(linea)
            lineas.put(None)

        lector = threading.Thread(target=leer_salida, daemon=True)
        lector.start()
        fin = time.monotonic() + 900
        try:
            while True:
                restante = fin - time.monotonic()
                if restante <= 0:
                    raise subprocess.TimeoutExpired(proceso.args, 900)
                try:
                    linea = lineas.get(timeout=min(restante, 0.5))
                except queue.Empty:
                    continue
                if linea is None:
                    break
                if progreso:
                    progreso(linea.strip()[:180])
            codigo = proceso.wait(timeout=max(0.1, fin - time.monotonic()))
        except subprocess.TimeoutExpired as error:
            proceso.kill()
            proceso.wait(timeout=2)
            raise RuntimeError("La descarga del modelo tardó demasiado.") from error
        if codigo != 0:
            raise RuntimeError("Ollama no pudo descargar el modelo de IA.")

    def traducir_y_ensenar(
        self,
        texto: str,
        idioma_origen: str,
        nivel: str,
        idioma_destino: str = "inglés",
    ) -> dict[str, Any]:
        """Devuelve traducción y ayudas didácticas en un objeto JSON."""
        texto = " ".join(texto.split())[:1800]
        if not texto:
            raise ValueError("No hay texto para traducir.")
        if idioma_destino not in {"inglés", "español"}:
            raise ValueError("El idioma de destino debe ser inglés o español.")
        sistema = (
            "Eres un traductor preciso y un tutor de idiomas. Responde únicamente con JSON válido "
            'de dos campos: {"translation":"...","explanation":"..."}. '
            f"translation debe estar exclusivamente en {idioma_destino}. "
            "Traduce únicamente el texto delimitado como texto fuente. El campo translation "
            "debe contener solo esa traducción, sin etiquetas, preámbulos, instrucciones ni datos "
            "adicionales. Conserva el significado y los nombres propios. "
            f"Adapta la explicación breve al nivel {nivel}; escríbela en español y déjala vacía "
            "si no aporta nada."
        )
        usuario = (
            f"Traduce del {idioma_origen} al {idioma_destino}. "
            f"Traduce al {idioma_destino} únicamente el contenido de este bloque:\n"
            f"<texto_fuente>\n{texto}\n</texto_fuente>"
        )
        respuesta = requests.post(
            f"{URL_OLLAMA}/api/chat",
            json={
                "model": self.modelo,
                "messages": [
                    {"role": "system", "content": sistema},
                    {"role": "user", "content": usuario},
                ],
                "format": "json",
                "stream": False,
                "think": False,
                "keep_alive": "5m",
                "options": {"temperature": 0.1, "num_ctx": 2048, "num_predict": 160},
            },
            timeout=TIEMPO_ESPERA,
        )
        respuesta.raise_for_status()
        contenido = respuesta.json().get("message", {}).get("content", "")
        resultado = json.loads(contenido)
        traduccion = str(resultado.get("translation", "")).strip()
        if not traduccion:
            raise ValueError("El modelo no devolvió una traducción.")
        return {
            "translation": traduccion[:2500],
            "explanation": str(resultado.get("explanation", "")).strip()[:500],
        }

    def conversar(
        self,
        historial: list[dict[str, str]],
        nivel: str,
        palabras_conocidas: list[str],
        texto_actual: str = "",
        idioma_estudio: str = "inglés",
        perfil_aprendizaje: dict[str, Any] | None = None,
    ) -> str:
        """Responde una conversación usando el nivel y vocabulario del estudiante."""
        if idioma_estudio == "español":
            regla_idioma = (
                "El estudiante aprende español. Palabras nuevas, ejemplos y práctica van en español. "
                "Explica en español sencillo."
            )
        else:
            regla_idioma = (
                "El estudiante aprende inglés. Palabras nuevas, ejemplos y frases de práctica van en inglés. "
                "Puedes explicar en español breve, pero no enseñes vocabulario español salvo que lo pida. "
                "Si pide una palabra nueva, elige una palabra en inglés de su nivel, da el significado en "
                "español y un ejemplo en inglés."
            )
        sistema = (
            "Eres LingoLens, un tutor de idiomas cercano, paciente y conversacional. "
            f"{regla_idioma} Adapta la dificultad al nivel indicado. "
            f"El nivel actual es {nivel}; este nivel tiene prioridad absoluta sobre cualquier turno anterior. "
            "Si el usuario practica, corrige con tacto: muestra una versión natural y explica el cambio "
            "en una frase sencilla. Responde preguntas sobre gramática y uso de palabras con ejemplos "
            "breves. Usa el vocabulario conocido para elegir explicaciones y sugerencias; no afirmes que "
            "conoces otras palabras que no aparecen en esa lista. Sugiere como máximo una palabra nueva "
            "cuando ayude a la conversación. Mantén la respuesta breve y no repitas la pregunta."
        )
        conocidas = ", ".join(palabras_conocidas[:50]) or "todavía no hay palabras guardadas"
        contexto = (
            f"Idioma que estudia: {idioma_estudio}. Nivel: {nivel}. "
            f"Palabras guardadas por el estudiante: {conocidas}."
        )
        perfil = perfil_aprendizaje or {}
        dificiles = ", ".join(
            str(palabra)
            for palabra in perfil.get("palabras_dificiles", [])[:8]
            if palabra
        )
        if dificiles:
            contexto += (
                " Palabras que el estudiante ha practicado con más dificultad: "
                f"{dificiles}. Prioriza ejemplos breves con ellas."
            )
        texto_pantalla = " ".join(texto_actual.split())[:700]
        if texto_pantalla:
            contexto += f" Texto que está leyendo ahora: {texto_pantalla}"

        mensajes = [
            {"role": "system", "content": f"{sistema}\n{contexto}"}
        ]
        for mensaje in historial[-16:]:
            rol = mensaje.get("role")
            contenido = str(mensaje.get("content", "")).strip()
            if rol in {"user", "assistant"} and contenido:
                mensajes.append({"role": rol, "content": contenido[:1400]})
        if len(mensajes) == 1 or mensajes[-1]["role"] != "user":
            raise ValueError("Escribe un mensaje para iniciar la conversación.")

        respuesta = requests.post(
            f"{URL_OLLAMA}/api/chat",
            json={
                "model": self.modelo,
                "messages": mensajes,
                "stream": False,
                "think": False,
                "keep_alive": "5m",
                "options": {"temperature": 0.45, "num_ctx": 3072, "num_predict": 320},
            },
            timeout=TIEMPO_ESPERA,
        )
        respuesta.raise_for_status()
        contenido = str(respuesta.json().get("message", {}).get("content", "")).strip()
        if not contenido:
            raise ValueError("El asistente no devolvió una respuesta. Inténtalo otra vez.")
        return contenido[:1800]
