# Componentes externos

- **Python 3.14.7**: lenguaje de la interfaz y la lógica.
- **PySide6 6.11.2** (`requirements.txt`: `>=6.8`): ventana, controles, pestañas y tareas en segundo plano.
- **MSS 10.2.0** (`>=10.0`) y **Pillow 12.3.0** (`>=11.0`): captura, conversión y preparación de imágenes.
- **Tesseract OCR 5.4.0.20240606**: reconocimiento local. El ejecutable y los datos `eng`/`spa` se incluyen en el archivo final.
- **Requests 2.34.2** (`>=2.32`): comunicación HTTP con Ollama en el mismo equipo.
- **MinGW-w64 GCC 16.1.0**: compila el comparador de pantalla en C11 con `-O3` y avisos tratados como errores.
- **PyInstaller 6.22.3** (`>=6.12`): empaqueta Python, Qt, el núcleo C y OCR en un ejecutable único.
- **Ollama 0.34.0 y los modelos instalados**: asistente de idioma. `qwen2.5:1.5b`, `gemma4:26b` y `qwen3:8b` se ejecutan localmente; un modelo con sufijo `:cloud` necesita autenticación y acceso de pago en Ollama Cloud. Gemma 4 26B puede tardar más de dos minutos en frío; la aplicación permite hasta 180 segundos por respuesta.

Los números indicados son una captura de versiones de este PC, no versiones bloqueadas. `requirements.txt` establece mínimos; no hay un archivo de bloqueo (`lock`) en el proyecto.

La aplicación se comunica con `http://127.0.0.1:11434`, el servicio de Ollama del propio equipo. No guarda claves de API; si se selecciona un modelo `:cloud`, Ollama puede reenviar la solicitud a Ollama Cloud y aplican sus requisitos de cuenta y pago.

Consulta [Estado del proyecto y referencias](ESTADO_Y_REFERENCIAS.md) para ver las funciones, los repositorios oficiales, la cronología y las fuentes técnicas.
