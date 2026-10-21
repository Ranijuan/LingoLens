"""Ventana principal: lectura, traducción y aprendizaje."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable
from typing import Any

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from aplicacion.aprendizaje.registro import RegistroAprendizaje
from aplicacion.diagnostico import ResultadoChequeo, comprobar_entorno
from aplicacion.ia.asistente import (
    MODELO_POR_DEFECTO,
    MODELOS_RECOMENDADOS,
    AsistenteLocal,
    nombre_modelo_valido,
)
from aplicacion.pantalla import ResultadoPantalla, capturar_y_leer
from aplicacion.puente_nucleo import Nucleo


class SenalesTrabajo(QObject):
    terminado = Signal(object)
    fallo = Signal(str)
    progreso = Signal(str)


class Trabajo(QRunnable):
    """Ejecuta una función lenta fuera del hilo gráfico."""

    def __init__(self, funcion: Callable[[Callable[[str], None]], Any]) -> None:
        super().__init__()
        self.senales = SenalesTrabajo()
        self._funcion = funcion
        self._cancelado = threading.Event()

    def cancelar(self) -> None:
        """Evita emitir señales cuando la ventana ya se está cerrando."""
        self._cancelado.set()

    def _informar_progreso(self, mensaje: str) -> None:
        if not self._cancelado.is_set():
            self.senales.progreso.emit(mensaje)

    def run(self) -> None:
        try:
            valor = self._funcion(self._informar_progreso)
        except Exception as error:  # La interfaz muestra el error y sigue abierta.
            if not self._cancelado.is_set():
                self.senales.fallo.emit(str(error))
        else:
            if not self._cancelado.is_set():
                self.senales.terminado.emit(valor)


class EntradaChat(QPlainTextEdit):
    """Caja que envía con Enter y conserva Shift+Enter para escribir otra línea."""

    enviar = Signal()

    def keyPressEvent(self, evento: QKeyEvent) -> None:
        teclas_enter = {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }
        con_shift = bool(evento.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if evento.key() in teclas_enter and not con_shift:
            evento.accept()
            self.enviar.emit()
            return
        super().keyPressEvent(evento)


def tarjeta(
    titulo: str,
    contenido: QWidget,
    nota: str = "",
    control: QWidget | None = None,
) -> QFrame:
    marco = QFrame()
    marco.setObjectName("tarjeta")
    caja = QVBoxLayout(marco)
    caja.setContentsMargins(18, 16, 18, 16)
    caja.setSpacing(10)
    encabezado = QHBoxLayout()
    nombre = QLabel(titulo)
    nombre.setObjectName("tituloTarjeta")
    encabezado.addWidget(nombre)
    if control is not None:
        encabezado.addWidget(control)
    encabezado.addStretch(1)
    if nota:
        etiqueta = QLabel(nota)
        etiqueta.setObjectName("nota")
        encabezado.addWidget(etiqueta)
    caja.addLayout(encabezado)
    caja.addWidget(contenido)
    return marco


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LingoLens · Aprende mientras lees")
        self.setMinimumSize(QSize(820, 700))
        self.resize(960, 800)
        self.setStyleSheet(ESTILOS)

        self._registro = RegistroAprendizaje()
        self._asistente = AsistenteLocal(self._registro.modelo() or MODELO_POR_DEFECTO)
        self._nucleo = Nucleo()
        self._grupo = QThreadPool(self)
        self._grupo.setMaxThreadCount(3)
        self._grupo.setExpiryTimeout(1000)
        self._reloj = QTimer(self)
        self._reloj.setInterval(1700)
        self._reloj.timeout.connect(self._leer_pantalla)
        self._captura_activa = False
        self._cerrando = False
        self._captura_en_curso = False
        self._asistencia_en_curso = False
        self._ia_lista = False
        self._texto_actual = ""
        self._texto_pendiente = ""
        self._trabajos: set[Trabajo] = set()
        self._diagnostico: list[ResultadoChequeo] = []
        self._modelos_instalados: tuple[str, ...] = ()
        self._historial_chat: list[dict[str, str]] = []
        self._chat_en_curso = False
        self._ultimo_mensaje_chat = ""
        self._nivel_chat_contexto = self._registro.nivel()
        self._fuente_texto = "pantalla"

        self._crear_interfaz()
        QTimer.singleShot(250, self._revisar_ia)

    def _crear_interfaz(self) -> None:
        desplazable = QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QFrame.Shape.NoFrame)
        contenido = QWidget()
        principal = QVBoxLayout(contenido)
        principal.setContentsMargins(26, 22, 26, 26)
        principal.setSpacing(16)

        encabezado = QHBoxLayout()
        marca = QLabel("L")
        marca.setObjectName("marca")
        marca.setAlignment(Qt.AlignmentFlag.AlignCenter)
        encabezado.addWidget(marca)
        nombre = QLabel("LingoLens")
        nombre.setObjectName("marcaNombre")
        encabezado.addWidget(nombre)
        self.notificacion = QLabel(
            "Aprende mientras lees · traducción a tu nivel"
        )
        self.notificacion.setObjectName("notificacion")
        encabezado.addWidget(self.notificacion)
        encabezado.addStretch(1)
        self.estado_ia = QLabel("Conectando IA local…")
        self.estado_ia.setObjectName("estado")
        encabezado.addWidget(self.estado_ia)
        self.boton_diagnostico = QPushButton("Diagnóstico")
        self.boton_diagnostico.setObjectName("botonSecundario")
        self.boton_diagnostico.setToolTip(
            "Comprueba OCR, núcleo C, almacenamiento, Ollama y el modelo elegido."
        )
        self.boton_diagnostico.clicked.connect(self._mostrar_diagnostico)
        encabezado.addWidget(self.boton_diagnostico)
        principal.addLayout(encabezado)

        controles = QHBoxLayout()
        controles.setSpacing(10)
        controles.addWidget(QLabel("Texto de entrada"))
        self.selector_fuente = QComboBox()
        self.selector_fuente.setObjectName("selectorFuente")
        self.selector_fuente.addItem("Texto de pantalla", "pantalla")
        self.selector_fuente.addItem("Texto propio", "propio")
        self.selector_fuente.setMinimumWidth(150)
        self.selector_fuente.setToolTip(
            "Elige entre leer la pantalla o escribir tu propio texto."
        )
        self.selector_fuente.currentIndexChanged.connect(self._cambio_fuente)
        controles.addWidget(self.selector_fuente)
        controles.addSpacing(10)
        controles.addWidget(QLabel("Leo en"))
        self.idioma = QComboBox()
        self.idioma.addItem("Inglés", "inglés")
        self.idioma.addItem("Español", "español")
        self.idioma.setFixedWidth(125)
        controles.addWidget(self.idioma)
        controles.addSpacing(10)
        controles.addWidget(QLabel("Mi nivel"))
        self.nivel = QComboBox()
        self.nivel.addItems(["A1", "A2", "B1", "B2", "C1"])
        self.nivel.setCurrentText(self._registro.nivel())
        self.nivel.setFixedWidth(78)
        controles.addWidget(self.nivel)
        controles.addSpacing(10)
        controles.addWidget(QLabel("Modelo IA"))
        self.selector_modelo = QComboBox()
        self.selector_modelo.setObjectName("selectorModelo")
        self.selector_modelo.setMinimumWidth(150)
        self.selector_modelo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.selector_modelo.setToolTip("Elige un modelo instalado en Ollama.")
        self.selector_modelo.currentIndexChanged.connect(self._cambio_modelo)
        controles.addWidget(self.selector_modelo)
        self.boton_modelos = QPushButton("Modelos…")
        self.boton_modelos.setObjectName("botonSecundario")
        self.boton_modelos.setToolTip(
            "Consulta, descarga y selecciona modelos locales de Ollama."
        )
        self.boton_modelos.clicked.connect(self._mostrar_modelos)
        controles.addWidget(self.boton_modelos)
        controles.addStretch(1)
        self.boton_ia = QPushButton("Preparar IA local")
        self.boton_ia.setObjectName("botonSecundario")
        self.boton_ia.setToolTip("Descarga el modelo local de Ollama una sola vez.")
        self.boton_ia.clicked.connect(self._instalar_ia)
        self.boton_ia.hide()
        controles.addWidget(self.boton_ia)
        self.boton_traducir = QPushButton("Traducir ahora")
        self.boton_traducir.setObjectName("botonSecundario")
        self.boton_traducir.setMinimumWidth(130)
        self.boton_traducir.setToolTip(
            "Envía el texto detectado o pegado al modelo elegido."
        )
        self.boton_traducir.clicked.connect(self._traducir_ahora)
        controles.addWidget(self.boton_traducir)
        self.boton_lectura = QPushButton("Iniciar lectura")
        self.boton_lectura.setObjectName("botonPrincipal")
        self.boton_lectura.setMinimumWidth(150)
        self.boton_lectura.setToolTip(
            "Mueve esta ventana a un borde libre; su zona se excluye del OCR."
        )
        self.boton_lectura.clicked.connect(self._alternar_lectura)
        controles.addWidget(self.boton_lectura)
        principal.addLayout(controles)

        fila = QGridLayout()
        fila.setHorizontalSpacing(14)
        fila.setVerticalSpacing(14)
        self.texto_origen = QPlainTextEdit()
        self.texto_origen.setPlaceholderText(
            "Al iniciar, aquí aparecerá el texto leído. También puedes pegar texto y pulsar Traducir ahora."
        )
        self.texto_origen.setMinimumHeight(170)
        self.texto_destino = QPlainTextEdit()
        self.texto_destino.setReadOnly(True)
        self.texto_destino.setPlaceholderText("La traducción aparecerá aquí.")
        self.texto_destino.setMinimumHeight(170)
        self.texto_destino.setObjectName("traduccion")
        self.selector_destino = QComboBox()
        self.selector_destino.setObjectName("selectorDestino")
        self.selector_destino.addItem("Inglés", "inglés")
        self.selector_destino.addItem("Español", "español")
        self.selector_destino.setCurrentIndex(0)
        self.selector_destino.setToolTip("Elige el idioma de la traducción.")
        self.selector_destino.currentIndexChanged.connect(
            self._cambio_configuracion
        )
        fila.addWidget(
            tarjeta("Texto para traducir", self.texto_origen),
            0,
            0,
        )
        fila.addWidget(
            tarjeta(
                "Traducción",
                self.texto_destino,
                "IA local",
                self.selector_destino,
            ),
            0,
            1,
        )
        fila.setColumnStretch(0, 1)
        fila.setColumnStretch(1, 1)
        principal.addLayout(fila)

        self.explicacion = QLabel("La explicación aparecerá aquí.")
        self.explicacion.setObjectName("textoAyuda")
        self.explicacion.setWordWrap(True)
        self.explicacion.setMinimumHeight(150)
        principal.addWidget(tarjeta("Explicación", self.explicacion))

        barra_inferior = QHBoxLayout()
        self.estado = QLabel(
            "OCR local. Mueve la ventana a un borde libre de la pantalla."
        )
        self.estado.setObjectName("nota")
        barra_inferior.addStretch(1)
        barra_inferior.addWidget(self.estado)
        principal.addLayout(barra_inferior)

        self.vista_previa = QLabel()
        self.vista_previa.setObjectName("vistaPrevia")
        self.vista_previa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.vista_previa.setMinimumHeight(74)
        self.vista_previa.hide()
        principal.addWidget(self.vista_previa)

        desplazable.setWidget(contenido)
        pestanas = QTabWidget()
        pestanas.addTab(desplazable, "Traducir y aprender")
        pestanas.addTab(self._crear_chat(), "Conversar")
        pestanas.addTab(self._crear_progreso(), "Mi progreso")
        self.setCentralWidget(pestanas)
        self.idioma.currentIndexChanged.connect(self._cambio_configuracion)
        self.nivel.currentTextChanged.connect(self._cambio_nivel)
        self._cambio_fuente()
        self._actualizar_progreso()

    def _crear_progreso(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(30, 24, 30, 24)
        caja.setSpacing(16)

        titulo = QLabel("Mi progreso")
        titulo.setObjectName("titulo")
        caja.addWidget(titulo)
        descripcion = QLabel(
            "LingoLens guarda señales de aprendizaje cifradas para adaptar las sugerencias. "
            "No guarda el texto completo de la pantalla ni de tus conversaciones."
        )
        descripcion.setObjectName("subtitulo")
        descripcion.setWordWrap(True)
        caja.addWidget(descripcion)

        self.progreso_resumen = QLabel()
        self.progreso_resumen.setObjectName("textoAyuda")
        self.progreso_resumen.setWordWrap(True)
        caja.addWidget(tarjeta("Resumen", self.progreso_resumen))

        self.progreso_dificultades = QLabel()
        self.progreso_dificultades.setObjectName("textoAyuda")
        self.progreso_dificultades.setWordWrap(True)
        caja.addWidget(tarjeta("Palabras para practicar", self.progreso_dificultades))

        self.progreso_historial = QLabel()
        self.progreso_historial.setObjectName("textoAyuda")
        self.progreso_historial.setWordWrap(True)
        caja.addWidget(tarjeta("Actividad reciente", self.progreso_historial))

        palabra = QLineEdit()
        palabra.setPlaceholderText("Palabra")
        significado = QLineEdit()
        significado.setPlaceholderText("Significado")
        boton_guardar = QPushButton("Guardar palabra")
        boton_guardar.setObjectName("botonPrincipal")
        boton_guardar.clicked.connect(self._guardar_palabra_desde_ui)
        palabra.returnPressed.connect(self._guardar_palabra_desde_ui)
        self.entrada_palabra = palabra
        self.entrada_significado = significado
        fila = QHBoxLayout()
        fila.addWidget(palabra)
        fila.addWidget(significado)
        fila.addWidget(boton_guardar)
        caja.addLayout(fila)

        self.estado_progreso = QLabel()
        self.estado_progreso.setObjectName("nota")
        caja.addWidget(self.estado_progreso)
        caja.addStretch(1)
        return pagina

    def _actualizar_progreso(self) -> None:
        if not hasattr(self, "progreso_resumen"):
            return
        resumen = self._registro.resumen_aprendizaje()
        self.progreso_resumen.setText(
            f"Nivel: {resumen['nivel']} · Idioma: {resumen['idioma']}\n"
            f"Actividades registradas: {resumen['interacciones']} · "
            f"Palabras practicadas: {resumen['palabras_practicadas']}"
        )
        dificultades = resumen["palabras_dificiles"]
        self.progreso_dificultades.setText(
            ", ".join(str(palabra) for palabra in dificultades)
            if dificultades
            else "Todavía no hay palabras suficientes para recomendar una práctica."
        )
        actividades = resumen["historial_reciente"]
        lineas = []
        for actividad in reversed(actividades):
            palabras = ", ".join(actividad.get("palabras", [])[:6]) or "sin palabras"
            lineas.append(
                f"{actividad.get('fecha', '')[:16]} · {actividad.get('tipo', '')} · {palabras}"
            )
        self.progreso_historial.setText("\n".join(lineas) or "No hay actividad registrada.")

    def _guardar_palabra_desde_ui(self) -> None:
        palabra = self.entrada_palabra.text().strip()
        significado = self.entrada_significado.text().strip()
        if not palabra or not significado:
            self.estado_progreso.setText("Escribe la palabra y su significado antes de guardar.")
            return
        self._registro.guardar_palabra(
            palabra,
            significado,
            "Palabra guardada por el estudiante.",
        )
        self.entrada_palabra.clear()
        self.entrada_significado.clear()
        self.estado_progreso.setText(f"«{palabra[:40]}» se añadió a tu vocabulario.")
        self._actualizar_progreso()

    def _actualizar_estado_chat_ia(self) -> None:
        if not hasattr(self, "estado_chat_ia"):
            return
        if self._ia_lista:
            tipo = "IA cloud" if self._es_modelo_cloud() else "IA local"
            self.estado_chat_ia.setText(f"{tipo} · {self._asistente.modelo}")
        else:
            self.estado_chat_ia.setText("IA local no disponible")

    def _actualizar_nivel_chat(self) -> None:
        if hasattr(self, "nivel_chat"):
            self.nivel_chat.blockSignals(True)
            self.nivel_chat.setCurrentText(self.nivel.currentText())
            self.nivel_chat.blockSignals(False)

    def _crear_chat(self) -> QWidget:
        pagina = QWidget()
        caja = QVBoxLayout(pagina)
        caja.setContentsMargins(30, 24, 30, 24)
        caja.setSpacing(16)

        encabezado = QHBoxLayout()
        titulos = QVBoxLayout()
        titulos.setSpacing(4)
        titulo = QLabel("Hablemos de idiomas")
        titulo.setObjectName("titulo")
        titulos.addWidget(titulo)
        subtitulo = QLabel(
            "Practica, pregunta tus dudas y recibe correcciones a tu nivel."
        )
        subtitulo.setObjectName("subtitulo")
        titulos.addWidget(subtitulo)
        encabezado.addLayout(titulos, 1)
        etiqueta_modelo = QLabel("Modelo")
        etiqueta_modelo.setObjectName("nota")
        encabezado.addWidget(etiqueta_modelo, 0, Qt.AlignmentFlag.AlignTop)
        self.selector_modelo_chat = QComboBox()
        self.selector_modelo_chat.setObjectName("selectorModeloChat")
        self.selector_modelo_chat.setMinimumWidth(150)
        self.selector_modelo_chat.setToolTip("Cambia el modelo para esta conversación.")
        self.selector_modelo_chat.currentIndexChanged.connect(
            self._cambio_modelo_chat
        )
        encabezado.addWidget(
            self.selector_modelo_chat, 0, Qt.AlignmentFlag.AlignTop
        )
        etiqueta_nivel = QLabel("Nivel de inglés")
        etiqueta_nivel.setObjectName("nota")
        encabezado.addWidget(etiqueta_nivel, 0, Qt.AlignmentFlag.AlignTop)
        self.nivel_chat = QComboBox()
        self.nivel_chat.setObjectName("nivelChat")
        self.nivel_chat.addItems(["A1", "A2", "B1", "B2", "C1"])
        self.nivel_chat.setCurrentText(self.nivel.currentText())
        self.nivel_chat.setToolTip(
            "Cambiar el nivel inicia un contexto nuevo para evitar arrastrar el nivel anterior."
        )
        self.nivel_chat.currentTextChanged.connect(self._cambio_nivel_chat)
        encabezado.addWidget(self.nivel_chat, 0, Qt.AlignmentFlag.AlignTop)
        self.estado_chat_ia = QLabel()
        self.estado_chat_ia.setObjectName("estadoChatIA")
        encabezado.addWidget(self.estado_chat_ia, 0, Qt.AlignmentFlag.AlignTop)
        self.boton_limpiar_chat = QPushButton("Nueva charla")
        self.boton_limpiar_chat.setObjectName("botonSecundario")
        self.boton_limpiar_chat.clicked.connect(self._limpiar_chat)
        encabezado.addWidget(self.boton_limpiar_chat, 0, Qt.AlignmentFlag.AlignTop)
        caja.addLayout(encabezado)

        sugerencias = QHBoxLayout()
        sugerencias.setSpacing(8)
        for texto in (
            "Corrige una frase",
            "Explícame una regla",
            "Enséñame una palabra",
        ):
            boton = QPushButton(texto)
            boton.setObjectName("sugerencia")
            boton.clicked.connect(
                lambda _, sugerencia=texto: self._usar_sugerencia_chat(sugerencia)
            )
            sugerencias.addWidget(boton)
        sugerencias.addStretch(1)
        caja.addLayout(sugerencias)

        panel = QFrame()
        panel.setObjectName("panelConversacion")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(10, 10, 10, 10)
        self.area_chat = QScrollArea()
        self.area_chat.setObjectName("areaChat")
        self.area_chat.setWidgetResizable(True)
        self.area_chat.setFrameShape(QFrame.Shape.NoFrame)
        self.contenido_chat = QWidget()
        self.contenido_chat.setObjectName("contenidoMensajes")
        self.lista_chat = QVBoxLayout(self.contenido_chat)
        self.lista_chat.setContentsMargins(18, 18, 18, 18)
        self.lista_chat.setSpacing(12)
        self.lista_chat.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.area_chat.setWidget(self.contenido_chat)
        panel_layout.addWidget(self.area_chat)
        caja.addWidget(panel, 1)

        entrada_fila = QHBoxLayout()
        entrada_fila.setSpacing(10)
        self.entrada_chat = EntradaChat()
        self.entrada_chat.setObjectName("entradaChat")
        self.entrada_chat.setPlaceholderText(
            "Escribe aquí… (Enter para enviar, Shift+Enter para una línea nueva)"
        )
        self.entrada_chat.setFixedHeight(76)
        self.entrada_chat.enviar.connect(self._enviar_mensaje_chat)
        entrada_fila.addWidget(self.entrada_chat, 1)
        self.boton_enviar_chat = QPushButton("Enviar")
        self.boton_enviar_chat.setObjectName("botonPrincipal")
        self.boton_enviar_chat.setMinimumWidth(104)
        self.boton_enviar_chat.setFixedHeight(48)
        self.boton_enviar_chat.clicked.connect(self._enviar_mensaje_chat)
        entrada_fila.addWidget(self.boton_enviar_chat, 0, Qt.AlignmentFlag.AlignBottom)
        caja.addLayout(entrada_fila)
        self.estado_chat = QLabel("Tu conversación se procesa en este PC.")
        self.estado_chat.setObjectName("nota")
        caja.addWidget(self.estado_chat)
        self._actualizar_estado_chat_ia()
        self._actualizar_nivel_chat()
        self._mensaje_bienvenida_chat()
        return pagina

    def _mensaje_bienvenida_chat(self) -> None:
        self._mostrar_mensaje_chat(
            "assistant",
            "¡Hola! Soy tu compañero para practicar el idioma que elegiste en «Leo en». "
            "Puedes preguntarme gramática, pedir una corrección o una palabra nueva en ese idioma.",
        )

    def _mostrar_mensaje_chat(self, rol: str, texto: str) -> None:
        fila = QWidget()
        distribucion = QHBoxLayout(fila)
        distribucion.setContentsMargins(0, 0, 0, 0)
        distribucion.setSpacing(0)
        burbuja = QFrame()
        es_usuario = rol == "user"
        burbuja.setObjectName("burbujaUsuario" if es_usuario else "burbujaAsistente")
        burbuja.setMaximumWidth(650)
        contenido = QVBoxLayout(burbuja)
        contenido.setContentsMargins(16, 11, 16, 12)
        contenido.setSpacing(5)
        autor = QLabel("TÚ" if es_usuario else "LINGOLENS")
        autor.setObjectName("autorUsuario" if es_usuario else "autorAsistente")
        contenido.addWidget(autor)
        mensaje = QLabel(texto)
        mensaje.setObjectName("textoUsuario" if es_usuario else "textoAsistente")
        mensaje.setTextFormat(Qt.TextFormat.PlainText)
        mensaje.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        mensaje.setWordWrap(True)
        contenido.addWidget(mensaje)
        if es_usuario:
            distribucion.addStretch(1)
            distribucion.addWidget(burbuja)
        else:
            distribucion.addWidget(burbuja)
            distribucion.addStretch(1)
        if self.lista_chat.count() >= 40:
            antiguo = self.lista_chat.takeAt(0)
            if antiguo.widget():
                antiguo.widget().deleteLater()
        self.lista_chat.addWidget(fila)
        QTimer.singleShot(
            0,
            lambda: self.area_chat.verticalScrollBar().setValue(
                self.area_chat.verticalScrollBar().maximum()
            ),
        )

    def _usar_sugerencia_chat(self, texto: str) -> None:
        idioma = str(self.idioma.currentData())
        indicaciones = {
            "Corrige una frase": "¿Puedes corregir esta frase y explicarme el cambio? ",
            "Explícame una regla": (
                f"Explícame una regla de gramática de {idioma} con un ejemplo en {idioma}."
            ),
            "Enséñame una palabra": (
                f"Enséñame una palabra nueva en {idioma} útil para mi nivel, "
                "con el significado en español y un ejemplo en ese idioma."
            ),
        }
        self.entrada_chat.setPlainText(indicaciones[texto])
        self.entrada_chat.setFocus()
        if texto != "Corrige una frase":
            self._enviar_mensaje_chat()

    def _enviar_mensaje_chat(self) -> None:
        texto = self.entrada_chat.toPlainText().strip()
        if not texto or self._chat_en_curso:
            return
        if not self._ia_lista:
            self.estado_chat.setText(
                "Prepara la IA local en la pestaña «Traducir y aprender» para conversar."
            )
            return
        self.entrada_chat.clear()
        self._ultimo_mensaje_chat = texto[:1400]
        self._historial_chat.append({"role": "user", "content": texto[:1400]})
        self._historial_chat = self._historial_chat[-16:]
        self._mostrar_mensaje_chat("user", texto[:1400])
        self._chat_en_curso = True
        self.boton_enviar_chat.setEnabled(False)
        self.entrada_chat.setEnabled(False)
        self.nivel_chat.setEnabled(False)
        self.estado_chat.setText("LingoLens está pensando…")
        historial = [dict(mensaje) for mensaje in self._historial_chat]
        nivel = self.nivel.currentText()
        conocidas = self._registro.palabras()
        idioma = str(self.idioma.currentData())
        self._registro.registrar_actividad(
            "conversacion",
            idioma,
            texto,
            dificultad=any(
                palabra in texto.casefold()
                for palabra in ("corrige", "corregir", "error", "incorrecta")
            ),
        )
        perfil = self._registro.resumen_aprendizaje()
        self._actualizar_progreso()
        texto_actual = self._texto_actual
        trabajo = Trabajo(
            lambda _: self._asistente.conversar(
                historial, nivel, conocidas, texto_actual, idioma, perfil
            )
        )
        trabajo.senales.terminado.connect(self._respuesta_chat_lista)
        trabajo.senales.fallo.connect(self._respuesta_chat_fallida)
        self._guardar_trabajo(trabajo)

    def _respuesta_chat_lista(self, respuesta: str) -> None:
        self._chat_en_curso = False
        self._historial_chat.append({"role": "assistant", "content": respuesta})
        self._historial_chat = self._historial_chat[-16:]
        self._mostrar_mensaje_chat("assistant", respuesta)
        self._activar_entrada_chat()
        self.estado_chat.setText("Respuesta lista · conversación procesada en este PC.")

    def _respuesta_chat_fallida(self, mensaje: str) -> None:
        self._chat_en_curso = False
        mensaje_visible = self._mensaje_error_modelo(mensaje)
        if self._historial_chat and self._historial_chat[-1].get("role") == "user":
            self._historial_chat.pop()
        self._mostrar_mensaje_chat(
            "assistant", f"No pude responder esta vez. {mensaje_visible}"
        )
        self._activar_entrada_chat()
        self.entrada_chat.setPlainText(self._ultimo_mensaje_chat)
        self.estado_chat.setText("Puedes volver a intentarlo.")

    def _mensaje_error_modelo(self, mensaje: str) -> str:
        detalle = mensaje.strip()
        modelo = self._asistente.modelo
        if "402" in detalle or "Payment Required" in detalle:
            return (
                f"{modelo} es un modelo cloud y requiere una cuenta con acceso de pago en Ollama. "
                "Elige un modelo local como gemma4:26b o qwen2.5:1.5b."
            )
        if "404" in detalle or "Not Found" in detalle:
            return (
                f"Ollama no encuentra {modelo}. Comprueba el nombre exacto con `ollama list` "
                "o instala el modelo antes de usarlo."
            )
        return detalle[:220]

    def _activar_entrada_chat(self) -> None:
        self.boton_enviar_chat.setEnabled(True)
        self.entrada_chat.setEnabled(True)
        self.nivel_chat.setEnabled(True)
        self.entrada_chat.setFocus()

    def _limpiar_chat(self) -> None:
        if self._chat_en_curso:
            self.estado_chat.setText("Espera a que termine la respuesta para iniciar otra charla.")
            return
        self._historial_chat.clear()
        while self.lista_chat.count():
            elemento = self.lista_chat.takeAt(0)
            if elemento.widget():
                elemento.widget().deleteLater()
        self._mensaje_bienvenida_chat()
        self.entrada_chat.clear()
        self.estado_chat.setText("Conversación nueva · tu vocabulario guardado sigue disponible.")

    def _guardar_trabajo(self, trabajo: Trabajo) -> Trabajo:
        if self._cerrando:
            trabajo.cancelar()
            return trabajo
        self._trabajos.add(trabajo)
        trabajo.senales.terminado.connect(lambda _: self._trabajos.discard(trabajo))
        trabajo.senales.fallo.connect(lambda _: self._trabajos.discard(trabajo))
        self._grupo.start(trabajo)
        return trabajo

    def _revisar_ia(self) -> None:
        self.estado_ia.setText("Comprobando entorno…")
        self.boton_diagnostico.setEnabled(False)

        def comprobar(_: Callable[[str], None]) -> dict[str, Any]:
            return {"resultados": comprobar_entorno(self._asistente)}

        trabajo = Trabajo(comprobar)
        trabajo.senales.terminado.connect(self._diagnostico_terminado)
        trabajo.senales.fallo.connect(self._ia_error)
        self._guardar_trabajo(trabajo)

    def _mostrar_diagnostico(self) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Diagnóstico de LingoLens")
        dialogo.setMinimumWidth(620)
        caja = QVBoxLayout(dialogo)
        caja.setContentsMargins(22, 20, 22, 20)
        caja.setSpacing(12)

        titulo = QLabel("Estado del equipo")
        titulo.setObjectName("titulo")
        caja.addWidget(titulo)
        descripcion = QLabel(
            "La aplicación puede seguir usando OCR aunque Ollama o el modelo no estén disponibles."
        )
        descripcion.setObjectName("subtitulo")
        descripcion.setWordWrap(True)
        caja.addWidget(descripcion)

        if not self._diagnostico:
            caja.addWidget(QLabel("El diagnóstico todavía está en curso."))
        else:
            simbolos = {"correcto": "✓", "advertencia": "!", "error": "×"}
            for chequeo in self._diagnostico:
                fila = QFrame()
                fila.setObjectName(f"diagnostico_{chequeo.estado}")
                horizontal = QHBoxLayout(fila)
                horizontal.setContentsMargins(12, 10, 12, 10)
                horizontal.setSpacing(10)
                icono = QLabel(simbolos.get(chequeo.estado, "!"))
                icono.setObjectName("diagnosticoIcono")
                icono.setFixedWidth(22)
                icono.setAlignment(Qt.AlignmentFlag.AlignCenter)
                horizontal.addWidget(icono)
                textos = QVBoxLayout()
                nombre = QLabel(chequeo.titulo)
                nombre.setObjectName("tituloTarjeta")
                textos.addWidget(nombre)
                detalle = QLabel(chequeo.detalle)
                detalle.setWordWrap(True)
                textos.addWidget(detalle)
                if chequeo.solucion:
                    solucion = QLabel(f"Siguiente paso: {chequeo.solucion}")
                    solucion.setObjectName("nota")
                    solucion.setWordWrap(True)
                    textos.addWidget(solucion)
                horizontal.addLayout(textos, 1)
                caja.addWidget(fila)

        botones = QDialogButtonBox()
        revisar = botones.addButton(
            "Volver a comprobar",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        cerrar = botones.addButton(QDialogButtonBox.StandardButton.Close)
        revisar.clicked.connect(lambda: (dialogo.accept(), self._revisar_ia()))
        cerrar.clicked.connect(dialogo.reject)
        caja.addWidget(botones)
        dialogo.exec()

    def _mostrar_modelos(self) -> None:
        dialogo = QDialog(self)
        dialogo.setWindowTitle("Modelos de IA local")
        dialogo.setMinimumWidth(700)
        caja = QVBoxLayout(dialogo)
        caja.setContentsMargins(22, 20, 22, 20)
        caja.setSpacing(12)

        titulo = QLabel("Elige el modelo que quieres usar")
        titulo.setObjectName("titulo")
        caja.addWidget(titulo)
        descripcion = QLabel(
            "Consulta el catálogo oficial de Ollama y descarga solo los modelos que quieras. "
            "También puedes escribir el nombre exacto de otro modelo compatible."
        )
        descripcion.setObjectName("subtitulo")
        descripcion.setWordWrap(True)
        caja.addWidget(descripcion)

        busqueda = QLineEdit()
        busqueda.setPlaceholderText("Buscar online: llama, qwen, gemma…")
        busqueda.setToolTip("La búsqueda se hace en el catálogo oficial; no envía el texto de tu pantalla.")
        caja.addWidget(busqueda)
        acciones_busqueda = QHBoxLayout()
        consultar = QPushButton("Buscar modelos online")
        consultar.setObjectName("botonSecundario")
        acciones_busqueda.addWidget(consultar)
        acciones_busqueda.addStretch(1)
        caja.addLayout(acciones_busqueda)

        selector = QComboBox()
        selector.setObjectName("selectorModeloDialogo")
        selector.setEditable(True)
        selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        selector.lineEdit().setPlaceholderText("Elige un modelo o escribe su nombre")
        catalogo_local = {modelo.nombre: modelo for modelo in MODELOS_RECOMENDADOS}
        catalogo = dict(catalogo_local)
        dialogo_cerrado = False
        trabajos_dialogo: set[Trabajo] = set()
        caja.addWidget(selector)

        detalle = QLabel()
        detalle.setObjectName("textoAyuda")
        detalle.setWordWrap(True)
        detalle.setMinimumHeight(68)
        caja.addWidget(detalle)

        estado = QLabel()
        estado.setObjectName("nota")
        estado.setWordWrap(True)
        caja.addWidget(estado)

        acciones = QHBoxLayout()
        descargar = QPushButton("Descargar modelo")
        descargar.setObjectName("botonPrincipal")
        usar = QPushButton("Usar este modelo")
        usar.setObjectName("botonSecundario")
        acciones.addWidget(descargar)
        acciones.addWidget(usar)
        acciones.addStretch(1)
        caja.addLayout(acciones)

        def modelo_seleccionado() -> str:
            return selector.currentText().strip()

        def actualizar_detalle() -> None:
            nombre = modelo_seleccionado()
            modelo = catalogo.get(nombre)
            instalado = self._modelo_en_lista(nombre, list(self._modelos_instalados))
            if modelo:
                detalle.setText(
                    f"{modelo.titulo} · {modelo.tamano}\n{modelo.descripcion}"
                )
            elif nombre:
                detalle.setText(
                    "Modelo escrito manualmente. Ollama comprobará si existe al descargarlo."
                )
            else:
                detalle.setText("Selecciona un modelo del catálogo o escribe un nombre compatible.")
            valido = nombre_modelo_valido(nombre)
            descargar.setEnabled(bool(nombre) and valido and not instalado)
            descargar.setText("Ya instalado" if instalado else "Descargar modelo")
            usar.setEnabled(instalado)
            if instalado:
                estado.setText("Disponible en este equipo.")
            elif nombre and not valido:
                estado.setText("El nombre solo puede contener letras, números, _, -, :, ., /.")
            else:
                estado.setText("Todavía no está instalado. La descarga puede ocupar varios GB.")

        def guardar_trabajo_dialogo(trabajo: Trabajo) -> None:
            trabajos_dialogo.add(trabajo)
            trabajo.senales.terminado.connect(
                lambda _: trabajos_dialogo.discard(trabajo)
            )
            trabajo.senales.fallo.connect(lambda _: trabajos_dialogo.discard(trabajo))
            self._guardar_trabajo(trabajo)

        def cancelar_trabajos_dialogo(_: int) -> None:
            nonlocal dialogo_cerrado
            dialogo_cerrado = True
            for trabajo in tuple(trabajos_dialogo):
                trabajo.cancelar()

        def rellenar_selector() -> None:
            elegido = modelo_seleccionado()
            selector.blockSignals(True)
            selector.clear()
            nombres = list(catalogo)
            for nombre in self._modelos_instalados:
                if nombre not in catalogo:
                    nombres.append(nombre)
            for nombre in nombres:
                modelo = catalogo.get(nombre)
                selector.addItem(nombre, nombre)
                if modelo:
                    indice_modelo = selector.count() - 1
                    selector.setItemData(
                        indice_modelo,
                        f"{modelo.titulo} · {modelo.tamano}",
                        Qt.ItemDataRole.ToolTipRole,
                    )
            indice = selector.findData(elegido)
            if indice >= 0:
                selector.setCurrentIndex(indice)
            elif elegido:
                selector.setEditText(elegido)
            selector.blockSignals(False)
            actualizar_detalle()

        def buscar_online() -> None:
            consulta = busqueda.text()
            consultar.setEnabled(False)
            busqueda.setEnabled(False)
            estado.setText("Consultando el catálogo oficial de Ollama…")

            def consultar_en_segundo_plano(_: Callable[[str], None]) -> object:
                return self._asistente.modelos_remotos(consulta)

            trabajo = Trabajo(consultar_en_segundo_plano)

            def catalogo_recibido(modelos: object) -> None:
                if dialogo_cerrado:
                    return
                encontrados = tuple(modelos) if isinstance(modelos, tuple) else ()
                catalogo.clear()
                catalogo.update(catalogo_local)
                catalogo.update(
                    {
                        modelo.nombre: modelo
                        for modelo in encontrados
                        if hasattr(modelo, "nombre")
                    }
                )
                rellenar_selector()
                consultar.setEnabled(True)
                busqueda.setEnabled(True)
                estado.setText(
                    f"Catálogo online actualizado: {len(encontrados)} modelo(s) encontrados."
                    if encontrados
                    else "No hubo coincidencias; se mantiene el catálogo recomendado."
                )

            def catalogo_fallido(mensaje: str) -> None:
                if dialogo_cerrado:
                    return
                consultar.setEnabled(True)
                busqueda.setEnabled(True)
                estado.setText(
                    "No se pudo consultar Internet; puedes usar el catálogo local "
                    f"o escribir un modelo exacto. {mensaje[:140]}"
                )

            trabajo.senales.terminado.connect(catalogo_recibido)
            trabajo.senales.fallo.connect(catalogo_fallido)
            guardar_trabajo_dialogo(trabajo)

        def usar_modelo() -> None:
            nombre = modelo_seleccionado()
            instalado = next(
                (
                    existente
                    for existente in self._modelos_instalados
                    if existente == nombre or existente.startswith(nombre + ":")
                ),
                nombre,
            )
            if instalado:
                self._seleccionar_modelo(instalado)
                estado.setText(f"Modelo seleccionado: {instalado}.")

        def descargar_modelo() -> None:
            nombre = modelo_seleccionado()
            if not nombre:
                return
            descargar.setEnabled(False)
            usar.setEnabled(False)
            selector.setEnabled(False)
            estado.setText(f"Preparando la descarga de {nombre}…")

            def descargar_en_segundo_plano(progreso: Callable[[str], None]) -> str:
                if not self._asistente.iniciar_servidor():
                    raise RuntimeError("No se pudo iniciar Ollama.")
                self._asistente.instalar_modelo(nombre, progreso=progreso)
                return nombre

            trabajo = Trabajo(descargar_en_segundo_plano)
            trabajo.senales.progreso.connect(estado.setText)

            def descarga_terminada(descargado: object) -> None:
                if not dialogo_cerrado:
                    self._modelo_descargado(
                        str(descargado), selector, detalle, estado, descargar, usar
                    )

            def descarga_fallida(mensaje: str) -> None:
                if not dialogo_cerrado:
                    self._modelo_descarga_fallida(
                        mensaje, selector, descargar, usar, estado
                    )

            trabajo.senales.terminado.connect(descarga_terminada)
            trabajo.senales.fallo.connect(descarga_fallida)
            guardar_trabajo_dialogo(trabajo)

        selector.currentIndexChanged.connect(actualizar_detalle)
        selector.editTextChanged.connect(actualizar_detalle)
        consultar.clicked.connect(buscar_online)
        busqueda.returnPressed.connect(buscar_online)
        descargar.clicked.connect(descargar_modelo)
        usar.clicked.connect(usar_modelo)
        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        botones.rejected.connect(dialogo.reject)
        caja.addWidget(botones)
        dialogo.finished.connect(cancelar_trabajos_dialogo)
        rellenar_selector()
        actualizar_detalle()
        buscar_online()
        dialogo.exec()

    def _modelo_descargado(
        self,
        nombre: str,
        selector: QComboBox,
        detalle: QLabel,
        estado: QLabel,
        descargar: QPushButton,
        usar: QPushButton,
    ) -> None:
        self._modelos_instalados = tuple(sorted(set(self._modelos_instalados) | {nombre}))
        self._rellenar_modelos(list(self._modelos_instalados))
        self.estado.setText(f"Modelo descargado: {nombre}. Puedes usarlo desde Modelos…")
        selector.setEnabled(True)
        indice = selector.findData(nombre)
        if indice < 0:
            selector.addItem(nombre, nombre)
            indice = selector.findData(nombre)
        selector.setCurrentIndex(indice)
        detalle.setText("Modelo descargado correctamente. Pulsa «Usar este modelo» para seleccionarlo.")
        estado.setText("Descarga terminada; el modelo está disponible en Ollama.")
        descargar.setText("Ya instalado")
        descargar.setEnabled(False)
        usar.setEnabled(True)

    def _modelo_descarga_fallida(
        self,
        mensaje: str,
        selector: QComboBox,
        descargar: QPushButton,
        usar: QPushButton,
        estado: QLabel,
    ) -> None:
        selector.setEnabled(True)
        descargar.setEnabled(True)
        usar.setEnabled(self._modelo_en_lista(str(selector.currentData() or ""), list(self._modelos_instalados)))
        estado.setText(f"No se pudo descargar el modelo: {mensaje[:220]}")

    def _modelo_en_lista(self, nombre: str, modelos: list[str]) -> bool:
        return any(
            modelo == nombre or modelo.startswith(nombre + ":")
            for modelo in modelos
        )

    def _rellenar_modelos(self, modelos: list[str]) -> None:
        elegido = self._asistente.modelo
        selectores = [self.selector_modelo]
        if hasattr(self, "selector_modelo_chat"):
            selectores.append(self.selector_modelo_chat)
        for selector in selectores:
            selector.blockSignals(True)
            selector.clear()
            for nombre in modelos:
                selector.addItem(nombre, nombre)
            selector.setEnabled(bool(modelos))

        if modelos:
            if not self._modelo_en_lista(elegido, modelos):
                elegido = modelos[0]
                self._asistente.modelo = elegido
                self._registro.guardar_modelo(elegido)
            for selector in selectores:
                indice = selector.findData(elegido)
                if indice < 0:
                    indice = next(
                        (
                            i
                            for i in range(selector.count())
                            if str(selector.itemText(i)).startswith(elegido)
                        ),
                        0,
                    )
                selector.setCurrentIndex(max(0, indice))

        for selector in selectores:
            selector.blockSignals(False)

    def _cambio_modelo(self) -> None:
        self._seleccionar_modelo(self.selector_modelo.currentData())

    def _cambio_modelo_chat(self) -> None:
        self._seleccionar_modelo(self.selector_modelo_chat.currentData())

    def _es_modelo_cloud(self) -> bool:
        return self._asistente.modelo.casefold().endswith(":cloud")

    def _seleccionar_modelo(self, valor: object) -> None:
        nombre = str(valor or "").strip()
        if not nombre:
            return
        self._asistente.modelo = nombre
        self._registro.guardar_modelo(nombre)
        self._ia_lista = True
        tipo = "IA cloud" if self._es_modelo_cloud() else "IA local"
        self.estado_ia.setText(f"{tipo} · {nombre}")
        selectores = [self.selector_modelo]
        if hasattr(self, "selector_modelo_chat"):
            selectores.append(self.selector_modelo_chat)
        for selector in selectores:
            selector.blockSignals(True)
            indice = selector.findData(nombre)
            if indice >= 0:
                selector.setCurrentIndex(indice)
            selector.blockSignals(False)
        self._actualizar_estado_chat_ia()

    def _cambio_fuente(self, *_: object) -> None:
        fuente = str(self.selector_fuente.currentData() or "pantalla")
        self._fuente_texto = fuente
        es_pantalla = fuente == "pantalla"
        self.texto_origen.clear()
        self._texto_actual = ""
        self._texto_pendiente = ""
        self.texto_origen.setReadOnly(es_pantalla)
        self.boton_lectura.setVisible(es_pantalla)
        self.vista_previa.hide()
        self._nucleo.reiniciar()
        if es_pantalla:
            self.texto_origen.setPlaceholderText(
                "Al iniciar, aquí aparecerá el texto leído de la pantalla."
            )
            self.estado.setText(
                "Texto de pantalla seleccionado. Mueve la ventana a un borde libre."
            )
        else:
            if self._captura_activa:
                self._reloj.stop()
                self._captura_activa = False
            self.boton_lectura.setText("Iniciar lectura")
            self.boton_lectura.setObjectName("botonPrincipal")
            self.boton_lectura.style().unpolish(self.boton_lectura)
            self.boton_lectura.style().polish(self.boton_lectura)
            self.texto_origen.setPlaceholderText(
                "Escribe o pega aquí el texto que quieres traducir."
            )
            self.estado.setText(
                "Texto propio seleccionado. Escribe o pega el texto y pulsa Traducir ahora."
            )

    def _diagnostico_terminado(self, resultado: object) -> None:
        datos = resultado if isinstance(resultado, dict) else {"resultados": []}
        resultados = [
            resultado
            for resultado in datos.get("resultados", [])
            if isinstance(resultado, ResultadoChequeo)
        ]
        self._diagnostico = resultados
        self.boton_diagnostico.setEnabled(True)
        por_clave = {resultado.clave: resultado for resultado in resultados}
        modelo = por_clave.get("modelo")
        modelos = list(modelo.modelos) if modelo else []
        self._modelos_instalados = tuple(modelos)
        self._rellenar_modelos(modelos)
        ollama = por_clave.get("ollama")
        hay_modelo = modelo is not None and modelo.estado == "correcto"
        servidor = ollama is not None and ollama.estado == "correcto"
        self._ia_lista = servidor and hay_modelo
        if self._ia_lista:
            actual = str(self.selector_modelo.currentData() or self._asistente.modelo)
            self._asistente.modelo = actual
            tipo = "IA cloud" if self._es_modelo_cloud() else "IA local"
            self.estado_ia.setText(f"{tipo} · {actual}")
            self.boton_ia.hide()
            if self._texto_actual:
                self._traducir(self._texto_actual)
        else:
            self.estado_ia.setText("OCR listo · IA pendiente")
            self.boton_ia.setText("Preparar IA local · ~1 GB")
            self.boton_ia.show()
        self._actualizar_estado_chat_ia()

    def _ia_error(self, mensaje: str) -> None:
        self._ia_lista = False
        self.boton_diagnostico.setEnabled(True)
        self.estado_ia.setText("IA local no disponible")
        self._actualizar_estado_chat_ia()
        self.boton_ia.show()
        if self._captura_activa:
            self.estado.setText(mensaje[:180])

    def _instalar_ia(self) -> None:
        self.boton_ia.setEnabled(False)
        self.boton_ia.setText("Preparando asistente…")
        self.estado.setText("Ollama descarga el modelo una sola vez.")

        def instalar(progreso: Callable[[str], None]) -> bool:
            if not self._asistente.iniciar_servidor():
                raise RuntimeError("No se pudo iniciar Ollama.")
            modelos = self._asistente.modelos_instalados()
            if not any(
                modelo == self._asistente.modelo
                or modelo.startswith(self._asistente.modelo + ":")
                for modelo in modelos
            ):
                self._asistente.instalar_modelo(progreso=progreso)
            return True

        trabajo = Trabajo(instalar)
        trabajo.senales.progreso.connect(self.estado.setText)
        trabajo.senales.terminado.connect(self._modelo_instalado)
        trabajo.senales.fallo.connect(self._instalacion_fallida)
        self._guardar_trabajo(trabajo)

    def _modelo_instalado(self, _: bool) -> None:
        self._ia_lista = True
        self._actualizar_estado_chat_ia()
        self.boton_ia.setEnabled(True)
        self.boton_ia.hide()
        self.estado.setText("Asistente listo. Las capturas y textos permanecen en este PC.")
        self._revisar_ia()

    def _instalacion_fallida(self, mensaje: str) -> None:
        self.boton_ia.setEnabled(True)
        self.boton_ia.setText("Reintentar preparación")
        self.estado.setText(mensaje[:180])

    def _alternar_lectura(self) -> None:
        if self._fuente_texto != "pantalla":
            return
        if self._captura_activa:
            self._reloj.stop()
            self._captura_activa = False
            self.boton_lectura.setText("Iniciar lectura")
            self.boton_lectura.setObjectName("botonPrincipal")
            self.boton_lectura.style().unpolish(self.boton_lectura)
            self.boton_lectura.style().polish(self.boton_lectura)
            self.estado.setText("Lectura pausada.")
        else:
            self._captura_activa = True
            self.boton_lectura.setText("Pausar lectura")
            self.boton_lectura.setObjectName("botonPausa")
            self.boton_lectura.style().unpolish(self.boton_lectura)
            self.boton_lectura.style().polish(self.boton_lectura)
            self.estado.setText("Leyendo la pantalla cada 1,7 segundos; OCR en este equipo.")
            self._leer_pantalla()
            self._reloj.start()

    def _geometria_ventana(self) -> tuple[int, int, int, int]:
        rect = self.frameGeometry()
        factor = self.devicePixelRatioF()
        return (
            round(rect.x() * factor),
            round(rect.y() * factor),
            round(rect.width() * factor),
            round(rect.height() * factor),
        )

    def _leer_pantalla(self) -> None:
        if (
            self._fuente_texto != "pantalla"
            or not self._captura_activa
            or self._captura_en_curso
        ):
            return
        self._captura_en_curso = True
        idioma = str(self.idioma.currentData())
        geometria = self._geometria_ventana()
        trabajo = Trabajo(
            lambda _: capturar_y_leer(self._nucleo, idioma, geometria)
        )
        trabajo.senales.terminado.connect(self._captura_lista)
        trabajo.senales.fallo.connect(self._captura_fallida)
        self._guardar_trabajo(trabajo)

    def _captura_lista(self, resultado: ResultadoPantalla) -> None:
        self._captura_en_curso = False
        if self._fuente_texto != "pantalla":
            return
        self._mostrar_vista(resultado.vista)
        if not resultado.hubo_cambios:
            return
        if not resultado.texto:
            self.estado.setText("Pantalla actualizada; no encontré texto legible.")
            return
        clave = re.sub(r"\s+", " ", resultado.texto).casefold()
        anterior = re.sub(r"\s+", " ", self._texto_actual).casefold()
        if clave == anterior:
            self.estado.setText("Texto sin cambios; no repito la traducción.")
            return
        self._texto_actual = resultado.texto
        self.texto_origen.setPlainText(resultado.texto)
        self.estado.setText("Texto nuevo detectado; preparando traducción y sugerencias…")
        if self._ia_lista:
            if self._asistencia_en_curso:
                self._texto_pendiente = resultado.texto
            else:
                self._traducir(resultado.texto)
        else:
            self.texto_destino.setPlainText(
                "Texto capturado. La IA no está disponible; puedes seguir usando el OCR "
                "o revisar el diagnóstico."
            )

    def _captura_fallida(self, mensaje: str) -> None:
        self._captura_en_curso = False
        self.estado.setText(mensaje[:200])

    def _mostrar_vista(self, imagen: Image.Image) -> None:
        rgb = imagen.convert("RGB")
        datos = rgb.tobytes()
        qimagen = QImage(
            datos,
            rgb.width,
            rgb.height,
            rgb.width * 3,
            QImage.Format.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(qimagen)
        self.vista_previa.setPixmap(
            pixmap.scaled(
                QSize(480, 270),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.vista_previa.setFixedHeight(230)
        self.vista_previa.show()

    def _traducir_ahora(self) -> None:
        texto = self.texto_origen.toPlainText().strip()
        if not texto:
            if self._fuente_texto == "pantalla":
                mensaje = "No hay texto detectado. Inicia la lectura o cambia a Texto propio."
            else:
                mensaje = "Escribe o pega un texto antes de pulsar Traducir ahora."
            self.estado.setText(mensaje)
            return
        self._texto_actual = texto
        if not self._ia_lista:
            self.estado.setText(
                "La IA no está disponible. Puedes seguir usando el OCR o revisar el diagnóstico."
            )
            return
        self._traducir(texto)

    def _traducir(self, texto: str) -> None:
        if not self._ia_lista or not texto:
            return
        if self._asistencia_en_curso:
            self._texto_pendiente = texto
            return
        self._asistencia_en_curso = True
        self.boton_traducir.setEnabled(False)
        idioma = str(self.idioma.currentData())
        nivel = self.nivel.currentText()
        idioma_destino = str(self.selector_destino.currentData())
        self._registro.registrar_actividad("traduccion", idioma, texto)
        self._actualizar_progreso()
        self.texto_destino.setPlainText("La IA está traduciendo…")
        self.estado.clear()
        trabajo = Trabajo(
            lambda _: self._asistente.traducir_y_ensenar(
                texto,
                idioma,
                nivel,
                idioma_destino,
            )
        )
        trabajo.senales.terminado.connect(self._traduccion_lista)
        trabajo.senales.fallo.connect(self._traduccion_fallida)
        self._guardar_trabajo(trabajo)

    def _traduccion_lista(self, resultado: dict[str, Any]) -> None:
        self._asistencia_en_curso = False
        self.boton_traducir.setEnabled(True)
        self.texto_destino.setPlainText(resultado["translation"])
        explicacion = resultado.get("explanation", "")
        self.explicacion.setText(
            explicacion or "No hay una explicación adicional para este texto."
        )
        self.estado.setText("Traducción lista.")
        if self._texto_pendiente:
            siguiente = self._texto_pendiente
            self._texto_pendiente = ""
            self._traducir(siguiente)

    def _traduccion_fallida(self, mensaje: str) -> None:
        self._asistencia_en_curso = False
        self.boton_traducir.setEnabled(True)
        detalle = self._mensaje_error_modelo(mensaje)
        self.texto_destino.setPlainText(f"No se pudo traducir.\n\n{detalle}")
        self.estado.setText("Falló la traducción.")
        if self._texto_pendiente:
            siguiente = self._texto_pendiente
            self._texto_pendiente = ""
            self._traducir(siguiente)

    def _cambio_nivel(self, nivel: str) -> None:
        if self._chat_en_curso and nivel != self._nivel_chat_contexto:
            self.nivel.blockSignals(True)
            self.nivel.setCurrentText(self._nivel_chat_contexto)
            self.nivel.blockSignals(False)
            self._actualizar_nivel_chat()
            self.estado_chat.setText(
                "Espera a que termine la respuesta para cambiar el nivel."
            )
            return
        self._registro.guardar_nivel(nivel)
        self._actualizar_progreso()
        self._actualizar_nivel_chat()
        if nivel != self._nivel_chat_contexto:
            self._nivel_chat_contexto = nivel
            self._reiniciar_chat_por_nivel(nivel)
        self._cambio_configuracion()

    def _cambio_nivel_chat(self, nivel: str) -> None:
        if self._chat_en_curso:
            self._actualizar_nivel_chat()
            self.estado_chat.setText(
                "Espera a que termine la respuesta para cambiar el nivel."
            )
            return
        if self.nivel.currentText() != nivel:
            self.nivel.setCurrentText(nivel)

    def _reiniciar_chat_por_nivel(self, nivel: str) -> None:
        self._historial_chat.clear()
        self._ultimo_mensaje_chat = ""
        while self.lista_chat.count():
            elemento = self.lista_chat.takeAt(0)
            if elemento.widget():
                elemento.widget().deleteLater()
        self._mensaje_bienvenida_chat()
        self.estado_chat.setText(
            f"Nivel cambiado a {nivel}. El contexto anterior se reinició."
        )

    def _cambio_configuracion(self, *_: object) -> None:
        self._registro.guardar_idioma(str(self.idioma.currentData()))
        texto = self.texto_origen.toPlainText().strip()
        if texto and self._ia_lista:
            self._texto_actual = texto
            self._traducir(texto)

    def closeEvent(self, evento: Any) -> None:
        self._cerrando = True
        self._reloj.stop()
        for trabajo in tuple(self._trabajos):
            trabajo.cancelar()
        self._grupo.clear()
        self._grupo.waitForDone(1000)
        if self._grupo.activeThreadCount() == 0:
            self._nucleo.cerrar()
        super().closeEvent(evento)


ESTILOS = """
QMainWindow, QWidget { color: #263A31; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow, QTabWidget::pane { background: #F5F8F5; }
QScrollArea { border: 0; background: transparent; }
QTabWidget::pane { border: 0; }
QTabBar { background: #F5F8F5; }
QTabBar::tab { background: transparent; color: #75837B; border: 0; border-bottom: 2px solid transparent; padding: 11px 17px; margin-right: 5px; font-size: 10pt; font-weight: 600; }
QTabBar::tab:selected { color: #176A4F; border-bottom: 2px solid #176A4F; }
QTabBar::tab:hover:!selected { color: #315E4B; background: #EBF2ED; border-radius: 8px 8px 0 0; }
QLabel#marca { background: #1B6A52; color: white; border-radius: 14px; font-size: 19pt; font-weight: 700; min-width: 38px; max-width: 38px; min-height: 38px; max-height: 38px; }
QLabel#marcaNombre { font-size: 16pt; font-weight: 650; color: #18382C; }
QLabel#notificacion { background: #FFF4D6; color: #806528; border: 1px solid #F0DFA8; border-radius: 10px; padding: 6px 10px; font-size: 8.5pt; }
QLabel#titulo { font-size: 24pt; font-weight: 650; color: #17382D; margin-top: 8px; }
QLabel#subtitulo { color: #68776F; font-size: 10.5pt; margin-bottom: 4px; }
QLabel#estado { background: #E5F1EB; color: #246448; border-radius: 12px; padding: 6px 11px; font-size: 9pt; }
QLabel#estadoChatIA { background: #E5F1EB; color: #246448; border-radius: 10px; padding: 6px 10px; font-size: 8.5pt; }
QComboBox#nivelChat { background: #FFF4D6; color: #806528; border-color: #F0DFA8; }
QFrame#tarjeta { background: #FFFFFF; border: 1px solid #E5EAE6; border-radius: 14px; }
QLabel#tituloTarjeta { color: #263C32; font-weight: 650; font-size: 10.5pt; }
QLabel#nota { color: #77847D; font-size: 9pt; }
QLabel#textoAyuda { color: #54645B; font-size: 11.5pt; }
QPlainTextEdit { background: #FAFBFA; color: #34473D; border: 1px solid #E8EDE9; border-radius: 10px; padding: 11px; selection-background-color: #B9DCCB; font-size: 10.5pt; }
QPlainTextEdit#traduccion { background: #F2F8F4; border-color: #DDEBE2; color: #173E2E; }
QComboBox { background: white; border: 1px solid #DDE5DF; border-radius: 8px; padding: 8px 10px; min-height: 20px; }
QComboBox::drop-down { border: 0; width: 24px; }
QPushButton { border: 0; border-radius: 9px; padding: 9px 13px; font-weight: 600; }
QPushButton#botonPrincipal { background: #176A4F; color: white; padding: 11px 16px; }
QPushButton#botonPrincipal:hover { background: #105B43; }
QPushButton#botonPausa { background: #E8EEE9; color: #385248; }
QPushButton#botonSecundario { background: #EAF1EC; color: #23523F; }
QPushButton#sugerencia { background: #EAF2EC; color: #3C6551; padding: 8px 12px; font-size: 9.5pt; }
QPushButton#sugerencia:hover { background: #DDEBE1; }
QPushButton:disabled { color: #7D8982; background: #EDF0ED; }
QLabel#vistaPrevia { background: #E9EEEA; border: 1px solid #DCE4DE; border-radius: 10px; padding: 4px; }
QFrame#panelConversacion { background: #FFFFFF; border: 1px solid #E5EAE6; border-radius: 18px; }
QScrollArea#areaChat, QWidget#contenidoMensajes { background: #F8FAF8; }
QFrame#burbujaAsistente { background: #FFFFFF; border: 1px solid #E6ECE7; border-radius: 15px; }
QFrame#burbujaUsuario { background: #E5F1E9; border: 1px solid #D8E9DE; border-radius: 15px; }
QFrame#diagnostico_correcto { background: #EAF5EE; border: 1px solid #CBE4D3; border-radius: 10px; }
QFrame#diagnostico_advertencia { background: #FFF7E1; border: 1px solid #F0DFA8; border-radius: 10px; }
QFrame#diagnostico_error { background: #FCEBED; border: 1px solid #F0C9CF; border-radius: 10px; }
QLabel#diagnosticoIcono { font-size: 14pt; font-weight: 700; color: #176A4F; }
QFrame#diagnostico_advertencia QLabel#diagnosticoIcono { color: #A47716; }
QFrame#diagnostico_error QLabel#diagnosticoIcono { color: #A23B4A; }
QLabel#autorAsistente, QLabel#autorUsuario { font-size: 8pt; font-weight: 700; color: #668073; }
QLabel#autorUsuario { color: #47715B; }
QLabel#textoAsistente, QLabel#textoUsuario { color: #34473D; font-size: 10.5pt; }
QLabel#textoUsuario { color: #244B37; }
QPlainTextEdit#entradaChat { background: #FFFFFF; border: 1px solid #DEE7E1; border-radius: 14px; color: #263A31; padding: 12px 14px; font-size: 10.5pt; }
QPlainTextEdit#entradaChat:focus { border: 1px solid #78A88C; }
"""
