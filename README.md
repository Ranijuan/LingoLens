# LingoLens

Aplicación de escritorio para leer texto en inglés o español desde la pantalla, traducirlo y aprender vocabulario a tu nivel. La interfaz está en español y es sencilla. La vista pequeña es una captura real del escritorio; no se usan imágenes generadas.

## Descargar y ejecutar la aplicación

La aplicación lista para usar se descarga desde la [Release más reciente](https://github.com/Ranijuan/LingoLens/releases/latest). Descarga el ZIP que aparece allí, extráelo y abre `LingoLens.exe`.

En la ventana:

1. Selecciona el idioma que aparece en pantalla y tu nivel.
2. Pulsa **Iniciar lectura**.
3. Elige el idioma de destino junto al título **Traducción**; empieza en inglés. Mientras trabaja, el aviso aparece dentro del cuadro y luego se reemplaza por el resultado.
4. Abre la pestaña **Conversar** para practicar o preguntar sobre gramática. Desde esa pestaña puedes cambiar el modelo y el nivel A1–C1; al cambiar el nivel, empieza un contexto nuevo para no arrastrar instrucciones anteriores. Escribe y pulsa **Enter** para enviar; usa **Shift+Enter** para dejar una línea nueva. La interfaz indica si el modelo es local o cloud.
5. Abre **Mi progreso** para consultar actividad, palabras que conviene practicar y guardar vocabulario manualmente.

Pulsa **Diagnóstico** junto al estado de la IA para comprobar Windows, el almacenamiento local, el perfil cifrado, la DLL C, Tesseract, Ollama y el modelo elegido. Si Ollama no está disponible, LingoLens conserva el OCR y muestra cómo resolver la conexión.

El OCR se realiza con Tesseract incluido en el ejecutable. Las capturas no se guardan en disco; una vista previa permanece visible mientras usas la app. El asistente se conecta al servicio local de Ollama; si eliges un modelo `:cloud`, Ollama puede enviarle el texto a su servicio cloud. El nivel y el vocabulario compatible se conservan en `%LOCALAPPDATA%\LingoLens\aprendizaje.sqlite3`. Las métricas de aprendizaje se guardan cifradas en `%LOCALAPPDATA%\LingoLens\perfil_aprendizaje.seguro` mediante DPAPI del usuario actual de Windows; el archivo no contiene el texto completo de la pantalla ni de las conversaciones.

## Preparar el código fuente en Windows

Necesitas Python 3.14, GCC de MinGW-w64, Tesseract instalado y Ollama. En PowerShell, desde la raíz del repositorio:

```powershell
cd codigo_fuente
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen2.5:1.5b
.\construir.ps1
.\empaquetar.ps1
.\distribuir.ps1
```

El resultado es `dist\LingoLens.exe`, un único archivo que contiene Python, PySide6, el núcleo C, Tesseract y los datos OCR en inglés y español. PyInstaller extrae sus componentes a una carpeta temporal al abrirse; por eso el primer inicio puede tardar más. Ollama y el modelo de IA permanecen instalados por separado para no añadir casi 1 GB al ejecutable. Si el modelo falta, la app muestra **Preparar IA local**.

## Ejecutar las pruebas

Las pruebas no necesitan abrir la interfaz ni conectarse a Ollama. Comprueban el almacenamiento local, la interpretación de respuestas de la IA y el núcleo C:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

Se usa `unittest`, incluido en Python, para mantener las pruebas ligeras y evitar otra dependencia. La suite actual contiene 22 pruebas.

## Qué hay en el código

- `nucleo/nucleo.c`: compara capturas en C y evita repetir OCR cuando la pantalla no cambió.
- `aplicacion/pantalla.py`: captura la pantalla, tapa la ventana propia y lee texto localmente.
- `aplicacion/ia/asistente.py`: pide al modelo seleccionado en Ollama una traducción, una explicación y respuestas para la conversación.
- `aplicacion/aprendizaje/registro.py`: conserva el nivel y el vocabulario local existente en SQLite.
- `aplicacion/aprendizaje/perfil_seguro.py`: cifra métricas de aprendizaje y actividad con DPAPI de Windows.
- `aplicacion/diagnostico.py`: comprueba las dependencias de primer arranque sin detener la aplicación.
- `aplicacion/interfaz/ventana.py`: muestra resultados y ejecuta el trabajo lento en segundo plano.
- `construir.ps1`, `empaquetar.ps1` y `distribuir.ps1`: compilan C, empaquetan la aplicación y crean una distribución limpia.
- `.github/workflows/pruebas.yml`: ejecuta las pruebas y comprobaciones en cada cambio de GitHub.

Los conceptos del código se explican con comentarios y en `documentacion/GUIA_DEL_CODIGO.md`.

## Documentación del proyecto

- [Estado, arquitectura, cronología, repositorios y fuentes técnicas](documentacion/ESTADO_Y_REFERENCIAS.md).
- [Librerías y herramientas](documentacion/DEPENDENCIAS.md).
- [Instalación](documentacion/INSTALACION.md) y [guía sencilla del código](documentacion/GUIA_DEL_CODIGO.md).
- [Registro de cambios con fecha, hora y resumen de cada entrega](documentacion/CAMBIOS.md).
