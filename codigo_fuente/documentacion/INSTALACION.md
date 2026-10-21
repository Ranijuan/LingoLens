# Instalación y creación del ejecutable

## Para construir la aplicación

1. Instala Python 3.14, GCC de MinGW-w64, Tesseract y Ollama.
2. Abre PowerShell en la carpeta `LingoLens\codigo_fuente`.
3. Crea un espacio separado para los paquetes y descarga las dependencias:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Prepara el asistente local. Este modelo ocupa cerca de 1 GB y se guarda una sola vez:

   ```powershell
   ollama pull qwen2.5:1.5b
   ```

5. Compila el núcleo en C y luego crea el único ejecutable:

   ```powershell
   .\construir.ps1
   .\empaquetar.ps1
   ```

6. Ejecuta `dist\LingoLens.exe`.

La primera ejecución puede tardar más porque Windows extrae los componentes de la aplicación a una carpeta temporal. El programa no necesita privilegios de administrador.

## En otro PC

Solo se copia `dist\LingoLens.exe`. El equipo destino necesita Ollama instalado y el modelo `qwen2.5:1.5b`. Si Ollama está instalado pero no tiene ese modelo, el botón **Preparar IA local** lo descarga. El archivo único contiene el intérprete de Python, la interfaz, Tesseract y las bibliotecas OCR en inglés y español; Ollama y el modelo se instalan aparte. Los modelos con etiqueta `:cloud` requieren autenticación y acceso en Ollama Cloud, y sus solicitudes se procesan fuera del equipo.

## Errores comunes

- **No se pudo iniciar la IA**: abre Ollama una vez o ejecuta `ollama serve` en una terminal; luego vuelve a pulsar **Preparar IA local**.
- **Gemma tarda en responder la primera vez**: `gemma4:26b` ocupa unos 18 GB y en este equipo su primera traducción tardó hasta 151 segundos. Espera a que aparezca el resultado; evita volver a pulsar el botón mientras la solicitud sigue activa.
- **La conversación falla después de cambiar A1/A2**: cambiar el nivel inicia una charla nueva automáticamente; vuelve a enviar el mensaje dentro del contexto nuevo.
- **La ventana no reconoce texto**: elige el idioma correcto y aumenta el tamaño del texto de la aplicación que quieres leer.
- **Windows SmartScreen muestra un aviso**: el ejecutable no está firmado digitalmente. Descárgalo o créalo desde esta carpeta de confianza.
