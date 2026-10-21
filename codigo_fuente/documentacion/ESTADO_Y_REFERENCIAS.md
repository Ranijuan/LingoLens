# LingoLens: documentación técnica y estado

**Corte de la información:** 2026-10-21, zona horaria America/Bogota (UTC−05:00).
**Actualización:** 2026-10-21; núcleo C, perfil cifrado, interfaz, distribución y pruebas automatizadas revisados contra el código actual.

## 1. Proyecto y repositorio

LingoLens lee texto visible en la pantalla, lo traduce, explica errores de gramática y ayuda a aprender vocabulario. La pestaña **Conversar** permite practicar con un tutor de IA local.

- **Carpeta del proyecto:** `C:\Users\PC_Juancho\proyectos\LingoLens`.
- **Repositorio de LingoLens:** [github.com/Ranijuan/LingoLens](https://github.com/Ranijuan/LingoLens), con código fuente y workflow de pruebas.
- **Release distribuida actualmente:** [LingoLens v1.0.1](https://github.com/Ranijuan/LingoLens/releases/tag/v1.0.1), con `LingoLens.exe` y el ZIP de distribución.
- **Sistema de construcción observado:** Windows 11, Python 3.14.7 y MinGW-w64 GCC 16.1.0.

Las primeras fechas históricas de este documento provienen de las fechas de modificación de los archivos; las entregas posteriores se relacionan con commits y releases publicados.

## 2. Ideas principales y recorrido del programa

1. **Capturar:** cada 1,7 segundos, `mss` obtiene una imagen de los monitores. La ventana de LingoLens se tapa en la imagen para evitar que la aplicación intente leer sus propios botones.
2. **Evitar OCR repetido:** el núcleo en C conserva una captura anterior y compara una muestra de píxeles. Solo solicita reconocimiento cuando encuentra suficientes diferencias. El paso de muestreo y el umbral son una regla sencilla del proyecto; no se han comparado con un benchmark.
3. **Leer el texto:** Pillow prepara la imagen en memoria y Tesseract la convierte en texto. Se usan los datos OCR en inglés (`eng`) o español (`spa`), según el idioma elegido. La imagen se entrega a Tesseract por entrada estándar; el programa no guarda capturas en archivos.
4. **Enseñar:** Python envía el texto reconocido a Ollama, que se comunica por `http://127.0.0.1:11434`. Para traducir, la respuesta estructurada incluye traducción y explicación; el idioma de destino se elige en la interfaz.
5. **Conversar:** el tutor recibe el nivel, hasta 50 registros de vocabulario existentes, el texto reconocido más reciente y hasta 16 mensajes. Cambiar el nivel A1–C1 desde la pestaña limpia el historial y comienza un contexto nuevo. Los mensajes tienen límites de tamaño; cada llamada permite hasta 180 segundos para responder.
6. **Recordar lo aprendido:** SQLite conserva preferencias y vocabulario compatible. La pestaña **Mi progreso** permite guardar palabras nuevas. `perfil_aprendizaje.seguro` conserva métricas, palabras practicadas y actividad resumida cifradas con DPAPI; no guarda el texto completo de la pantalla ni de las conversaciones.
7. **Mantener la ventana ágil:** captura, OCR y peticiones a la IA se ejecutan como trabajos de `QRunnable` dentro de un `QThreadPool` propio; al cerrar se cancelan las señales pendientes, se limpian los trabajos en cola y se espera brevemente a los trabajos rápidos.

La interfaz usa la fuente del sistema **Segoe UI**, pestañas, tarjetas y burbujas de conversación. No requiere fuentes ni imágenes añadidas.

## 3. Librerías y herramientas

Las versiones de la tabla son las encontradas en este PC al preparar este documento. `requirements.txt` fija versiones mínimas, no una lista cerrada de versiones; al reinstalar podrían instalarse versiones posteriores.

| Componente | Versión observada o requisito | Para qué se usa | Repositorio o documentación |
|---|---:|---|---|
| Python | 3.14.7 | Lenguaje principal de la interfaz y la lógica. | [Documentación de Python](https://docs.python.org/3/) |
| PySide6 / Qt for Python | 6.11.2; requisito `>=6.8` | Ventanas, controles, pestañas, temporizador, señales y trabajos en segundo plano. | [Repositorio](https://github.com/pyside/pyside-setup) · [Documentación](https://doc.qt.io/qtforpython-6/) |
| MSS | 10.2.0; requisito `>=10.0` | Captura de los monitores. | [Repositorio](https://github.com/BoboTiG/python-mss) · [Documentación](https://python-mss.readthedocs.io/latest/) |
| Pillow | 12.3.0; requisito `>=11.0` | Convierte, ajusta contraste, reduce tamaño y prepara imágenes para el OCR. | [Repositorio](https://github.com/python-pillow/Pillow) · [Documentación](https://pillow.readthedocs.io/en/stable/) |
| Requests | 2.34.2; requisito `>=2.32` | Envía y recibe JSON por HTTP desde la API local de Ollama. | [Repositorio](https://github.com/psf/requests) · [Guía](https://requests.readthedocs.io/en/latest/user/quickstart/) |
| PyInstaller | 6.22.3; requisito `>=6.12` | Empaqueta la aplicación y sus recursos en `LingoLens.exe`. Se usa al construir, no como servicio separado al ejecutar. | [Repositorio](https://github.com/pyinstaller/pyinstaller) · [Guía de uso](https://pyinstaller.org/en/stable/usage.html) |
| Tesseract OCR | 5.4.0.20240606 | Reconoce texto en inglés o español. El ejecutable y sus datos de idioma se copian dentro del paquete. | [Repositorio](https://github.com/tesseract-ocr/tesseract) · [Guía de línea de comandos](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html) |
| Ollama | Cliente 0.34.0; API local verificada el 2026-09-30 | La app llama a la API local. Los modelos `:cloud` pueden enrutar texto al servicio de Ollama Cloud; Ollama no está incluido en el `.exe`. | [Repositorio](https://github.com/ollama/ollama) · [API de chat](https://docs.ollama.com/api/chat) |
| Qwen2.5 1.5B | `qwen2.5:1.5b`, 986 MB | Modelo local predeterminado, probado para conversación y traducción. No se integra al `.exe`. | [Biblioteca oficial de Ollama](https://registry.ollama.com/library/qwen2.5) |
| Gemma 4 26B | `gemma4:26b`, aproximadamente 18 GB | Modelo local probado. Su primera solicitud puede tardar más de 150 segundos al cargar; el timeout es 180 segundos. | [Biblioteca de modelos de Ollama](https://ollama.com/search) |
| Qwen3 8B | `qwen3:8b`, aproximadamente 5,2 GB | Modelo local probado para conversación y traducción. | [Biblioteca de modelos de Ollama](https://ollama.com/search) |
| MinGW-w64 GCC | 16.1.0 | Compila el comparador C como `nucleo.dll`. | [Proyecto MinGW-w64](https://github.com/mingw-w64/mingw-w64) · [Opciones de optimización GCC](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html) |
| `ctypes`, `sqlite3`, `json`, `subprocess`, `pathlib` | Incluidas con Python | Conecta Python con la DLL C, guarda preferencias y palabras, procesa JSON, inicia Tesseract/Ollama y resuelve rutas. No se instalan con `pip`. | [SQLite en Python](https://docs.python.org/3/library/sqlite3.html) |

La línea `-std=c11 -O3 -Wall -Wextra -Werror` de `construir.ps1` selecciona C11, solicita optimización al compilador y trata los avisos como errores. `-O3` no garantiza por sí solo que una aplicación sea más rápida en todos los equipos; aquí la comparación C está pensada para saltarse OCR cuando la pantalla casi no cambió.

## 4. Archivos principales

| Archivo o carpeta | Explicación breve |
|---|---|
| `aplicacion/main.py` | Inicia Qt y abre la ventana principal. |
| `aplicacion/interfaz/ventana.py` | Traducción, conversación, progreso, historial temporal y conexión de los trabajos de fondo. |
| `aplicacion/ia/asistente.py` | Cliente de Ollama; interpreta resultados de traducción y conserva el contexto breve de la conversación. |
| `aplicacion/pantalla.py` | Captura, procesa la imagen y ejecuta Tesseract. |
| `aplicacion/qt_runtime_hook.py` | Registra las carpetas nativas de Qt antes de importar la interfaz empaquetada. |
| `aplicacion/puente_nucleo.py` | Llama desde Python a las funciones exportadas por la DLL C mediante `ctypes`. |
| `nucleo/nucleo.c` y `nucleo/nucleo.h` | Comparan las muestras de píxeles y administran la imagen anterior. |
| `aplicacion/aprendizaje/registro.py` | Guarda nivel, idioma y vocabulario en SQLite; conecta el perfil seguro con la aplicación. |
| `aplicacion/aprendizaje/perfil_seguro.py` | Cifra métricas y actividad resumida con DPAPI de Windows. |
| `construir.ps1` | Compila el núcleo C. |
| `empaquetar.ps1` | Copia OCR, compila C y genera el ejecutable único. |
| `distribuir.ps1` | Crea un ZIP limpio sin entorno virtual ni artefactos temporales. |
| `.github/workflows/pruebas.yml` | Ejecuta compilación C, pruebas Python, compilación Python y `git diff --check` en GitHub. |
| `LingoLens.spec` | Define el ejecutable onefile, conserva el ZIP OCR y filtra DLL ICU incompatibles. |
| `requirements.txt` | Lista dependencias Python y sus versiones mínimas. |

## 5. Cronología y resultado de cada cambio

### 2026-10-21 — Núcleo aislado, perfil cifrado, cierre y pruebas en GitHub

- El núcleo C dejó de usar una imagen estática global y ahora crea un contexto independiente por instancia. La DLL valida dimensiones y tiene funciones explícitas de creación, reinicio y destrucción.
- Se añadieron pruebas profundas para contextos independientes, padding por fila, reinicios concurrentes, límites de tamaño y 100 ciclos de capturas alternas.
- La ventana usa un `QThreadPool` propio. Al cerrar, detiene el temporizador, cancela señales pendientes, limpia trabajos en cola y libera el contexto nativo cuando ya no hay tareas activas.
- Se añadió `perfil_aprendizaje.seguro`, cifrado con DPAPI del usuario actual de Windows. Guarda métricas de palabras y actividad resumida sin copiar el texto completo de la pantalla o del chat.
- Se añadió **Mi progreso**, con palabras difíciles, actividad reciente y guardado manual de vocabulario.
- Se añadió `.github/workflows/pruebas.yml` para instalar dependencias, compilar C, ejecutar la suite, compilar Python y revisar el parche en cada cambio.
- Se añadió `distribuir.ps1` para crear una distribución limpia sin `.venv`, `build`, `dist`, Tesseract extraído ni cachés.
- La suite pasó 19 pruebas en Windows con Qt en modo `offscreen`; también pasaron `compileall` y la compilación C.

**Resumen al terminar este cambio:** el núcleo ya soporta instancias aisladas y libera su memoria; la aplicación conserva un perfil de aprendizaje cifrado, tiene una vista de progreso, cierra las tareas pendientes con más control y cuenta con pruebas automáticas en GitHub.

### 2026-09-30 — Estado actual, modelos y limpieza

- La traducción tiene idioma destino seleccionable, inglés por defecto, respuesta compacta y timeout de 180 s. Qwen2.5 1.5B, Qwen3 8B y Gemma 4 26B se comprobaron con una frase real; Gemma puede tardar más de 150 s al iniciar en frío.
- En **Conversar**, cambiar el nivel A1–C1 sincroniza el control principal e inicia un contexto nuevo. El contenido completo de la conversación sigue siendo temporal; el perfil seguro conserva únicamente métricas y palabras resumidas.
- El ejecutable final se reconstruyó y abrió el 2026-09-30; su huella se conserva en `documentacion/CAMBIOS.md`.
- Se retiraron referencias de código y estilos sin uso. Se localizaron cachés Python antes del empaquetado final, pero al cierre no quedaba ninguna; no fue necesario borrarlas manualmente. Se conservaron los registros SQLite, informes `build`, entorno virtual, OCR, DLL y ejecutables.

### 2026-09-27, 21:51–22:03, America/Bogota — Primera versión funcional

La hora es el rango de modificación de los primeros archivos fuente observados; no existe un commit Git que confirme la hora exacta.

- Se creó la ventana de traducción y aprendizaje en español.
- Se conectaron captura de pantalla, OCR local inglés/español y el comparador rápido en C.
- Se añadió la integración con Ollama, correcciones, vocabulario guardado en SQLite y los scripts de compilación y empaquetado.
- Se preparó PyInstaller para producir un único `.exe` con Qt, Python, núcleo C y Tesseract. Ollama y el modelo quedan aparte.

**Resumen al terminar este cambio:** quedó la base funcional de LingoLens para traducir y aprender desde la pantalla. La IA y el modelo necesitan estar instalados por separado.

### 2026-09-28, 09:59–10:04, America/Bogota — Chat e interfaz más amigable

El rango corresponde a las fechas de modificación de `ventana.py`, `asistente.py` y al `.exe` generado.

- Se creó una pestaña **Conversar**, con burbujas, preguntas sugeridas, envío con Enter y salto de línea con Shift+Enter.
- El tutor adapta las respuestas al nivel, al vocabulario guardado y a las palabras difíciles del perfil seguro. El contenido completo del historial corto se conserva solo en memoria; un fallo deja el mensaje listo para reintentar.
- Se suavizaron los colores, el espaciado y los tamaños de letra usando Segoe UI del sistema.
- Se recompiló `nucleo.dll` y se generó `dist\LingoLens.exe` (186.614.300 bytes). `compileall` y el empaquetado finalizaron sin errores.

**Resumen al terminar este cambio:** el ejecutable incluye la pestaña de conversación y la interfaz renovada. En la revisión del 2026-09-28 a las 10:08, el cliente Ollama informó que no podía conectar con un servidor activo; por eso la conversación con el modelo no se volvió a confirmar en ejecución en esa revisión.

### 2026-09-28, 12:28–12:33, America/Bogota — Corrección del ejecutable y pruebas funcionales

- Se aisló un error nativo de QtWidgets causado por DLL ICU incompletas incluidas por PyInstaller. `LingoLens.spec` ahora las excluye y el runtime hook registra las carpetas de Qt.
- Se regeneró el archivo único `dist\LingoLens.exe`, de aproximadamente 117,1 MiB.
- El ejecutable se abrió y mantuvo la ventana `LingoLens · Aprende mientras lees` sin mostrar una excepción.
- El núcleo C, el OCR real de pantalla y la conversación con Ollama pasaron comprobaciones funcionales. La conversación devolvió una corrección gramatical válida.
- `compileall` no encontró errores de sintaxis.

**Resumen al terminar este cambio:** la entrega actual arranca y ejecuta las funciones principales en este PC. La ventana quedó abierta después de la prueba.

### 2026-09-28, 11:26–11:30, America/Bogota — Instalación de dependencias y verificación de la IA

- Se comprobaron el entorno virtual, Tesseract, GCC y PyInstaller. Las dependencias Python declaradas en `requirements.txt` ya estaban satisfechas.
- Se inició Ollama y se instaló `qwen2.5:1.5b`; la API local respondió correctamente a una conversación de prueba.
- Se recompiló el núcleo C y se creó `dist\LingoLens.exe` con 186.614.300 bytes, aproximadamente 178 MB.
- Se confirmó que Tesseract está incluido en `recursos\tesseract` junto con `eng.traineddata` y `spa.traineddata`.

**Resumen al terminar este cambio:** la aplicación está preparada para ejecutarse en este equipo con traducción OCR y tutor local disponibles. El ejecutable sigue necesitando Ollama instalado en equipos adicionales porque el modelo no se incorpora al archivo único.

### 2026-09-28, 10:11, America/Bogota — Documentación y referencias

- Se reunió el estado del proyecto, su estructura, el recorrido de datos, las decisiones de diseño y las versiones de herramientas y bibliotecas.
- Se añadieron enlaces a la documentación oficial y a los repositorios de los componentes externos.
- Se aclaró que la carpeta del proyecto no tiene Git remoto y que las horas antiguas vienen de fechas de archivos.

**Resumen al terminar este cambio:** la documentación describe qué está construido y qué falta comprobar en el equipo. El `.exe` se generó correctamente; para verificar el chat en uso, Ollama debe estar ejecutándose con el modelo configurado.

## 6. Estado, verificación y requisitos restantes

- **Compilación:** el ejecutable final se reconstruyó el 2026-09-30 y se verificó su arranque desde la raíz.
- **Ejecución con IA:** Ollama 0.34.0 y los modelos locales Qwen2.5 1.5B, Gemma 4 26B y Qwen3 8B se verificaron el 2026-09-30. Los tres produjeron traducciones correctas.
- **Interfaz:** se probaron el destino configurable de traducción, el estado de espera dentro del cuadro y los cambios A1→A2→B1 con reinicio de contexto.
- **Imágenes:** el OCR usa una captura real del escritorio procesada en memoria; no se crean imágenes artificiales ni se guarda la captura como archivo.
- **Aprendizaje guardado:** nivel y palabras guardadas están en `%LOCALAPPDATA%\LingoLens\aprendizaje.sqlite3`. El chat no persiste.
- **Límite de verificación:** la suite automatizada cubre el núcleo C, SQLite, perfil seguro, OCR, Ollama simulado e interfaz en modo `offscreen`. La conexión real con Ollama y la captura de escritorio se verifican aparte porque requieren servicios y una sesión de Windows activos.

## 7. Fuentes técnicas consultadas

Estas referencias oficiales describen las interfaces y herramientas elegidas. Sirven para verificar el modo de uso técnico; el umbral de comparación de píxeles y el límite del historial son decisiones concretas del código de LingoLens, no valores que se presenten como óptimos por una fuente externa.

1. [Qt for Python: `QRunnable`](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QRunnable.html) y [`QThreadPool`](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThreadPool.html): tareas fuera de la interfaz y reutilización de hilos.
2. [Qt for Python: `QTabWidget`](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QTabWidget.html): pestañas para separar traducción y conversación.
3. [Ollama: API `POST /api/chat`](https://docs.ollama.com/api/chat): mensajes con roles, historial, respuesta y opciones de generación.
4. [Ollama: modelo Qwen2.5](https://registry.ollama.com/library/qwen2.5): catálogo y etiquetas del modelo configurado.
5. [Tesseract: uso por línea de comandos](https://tesseract-ocr.github.io/tessdoc/Command-Line-Usage.html): ejecución local, opciones OCR y datos de idiomas.
6. [MSS: documentación](https://python-mss.readthedocs.io/latest/) y [Pillow: documentación](https://pillow.readthedocs.io/en/stable/): captura y preparación de imágenes.
7. [Requests: guía rápida](https://requests.readthedocs.io/en/latest/user/quickstart/): solicitudes HTTP, JSON y manejo de errores.
8. [Python: `sqlite3`](https://docs.python.org/3/library/sqlite3.html): acceso a SQLite desde la biblioteca estándar.
9. [PyInstaller: opciones de empaquetado](https://pyinstaller.org/en/stable/usage.html): ejecutable de un archivo, incorporación de recursos y opciones de Windows.
10. [GCC: opciones de optimización](https://gcc.gnu.org/onlinedocs/gcc/Optimize-Options.html): significado de las opciones de optimización del compilador.
