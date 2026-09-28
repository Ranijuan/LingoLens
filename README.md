# LingoLens

Aplicación de escritorio para leer texto en inglés o español desde la pantalla, traducirlo y aprender vocabulario a tu nivel. La interfaz está en español y es sencilla. La vista pequeña es una captura real del escritorio; no se usan imágenes generadas.

## Ejecutar

Abre `..\LingoLens.exe`. En la ventana:

1. Selecciona el idioma que aparece en pantalla y tu nivel.
2. Pulsa **Iniciar lectura**.
3. La traducción, las correcciones y hasta dos palabras útiles aparecerán cuando cambie el texto.
4. Pulsa **Guardar** en una palabra para que LingoLens la recuerde en tu PC.
5. Abre la pestaña **Conversar** para practicar o preguntar sobre gramática. Escribe y pulsa **Enter** para enviar; usa **Shift+Enter** para dejar una línea nueva. La IA adapta sus respuestas a tu nivel y a las palabras que guardaste.

El OCR se realiza con Tesseract incluido en el ejecutable. Las capturas no se guardan en disco; una vista previa permanece visible mientras usas la app. El asistente funciona con Ollama local. El progreso de palabras se guarda en `%LOCALAPPDATA%\LingoLens\aprendizaje.sqlite3`.

## Preparar el proyecto en Windows

Necesitas Python 3.14, GCC de MinGW-w64, Tesseract instalado y Ollama. En PowerShell, desde esta carpeta:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen2.5:1.5b
.\construir.ps1
.\empaquetar.ps1
```

El resultado es `dist\LingoLens.exe`, un único archivo que contiene Python, PySide6, el núcleo C, Tesseract y los datos OCR en inglés y español. PyInstaller extrae sus componentes a una carpeta temporal al abrirse; por eso el primer inicio puede tardar más. Ollama y el modelo de IA permanecen instalados por separado para no añadir casi 1 GB al ejecutable. Si el modelo falta, la app muestra **Preparar IA local**.

## Qué hay en el código

- `nucleo/nucleo.c`: compara capturas en C y evita repetir OCR cuando la pantalla no cambió.
- `aplicacion/pantalla.py`: captura la pantalla, tapa la ventana propia y lee texto localmente.
- `aplicacion/ia/asistente.py`: pide al modelo local una traducción, una corrección, vocabulario y respuestas para la conversación.
- `aplicacion/aprendizaje/registro.py`: guarda nivel y palabras en una base SQLite pequeña.
- `aplicacion/interfaz/ventana.py`: muestra resultados y ejecuta el trabajo lento en segundo plano.
- `construir.ps1` y `empaquetar.ps1`: compilan C y empaquetan la aplicación en un ejecutable.

Los conceptos del código se explican con comentarios y en `documentacion/GUIA_DEL_CODIGO.md`.

## Documentación del proyecto

- [Estado, arquitectura, cronología, repositorios y fuentes técnicas](documentacion/ESTADO_Y_REFERENCIAS.md).
- [Librerías y herramientas](documentacion/DEPENDENCIAS.md).
- [Instalación](documentacion/INSTALACION.md) y [guía sencilla del código](documentacion/GUIA_DEL_CODIGO.md).
- [Registro de cambios con fecha, hora y resumen de cada entrega](documentacion/CAMBIOS.md).
