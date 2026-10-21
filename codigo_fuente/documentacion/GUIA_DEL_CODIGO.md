# Guía sencilla del código

## Cómo pasa el texto por la aplicación

1. `aplicacion/interfaz/ventana.py` inicia una captura cada 1,7 segundos. El trabajo se envía a otro hilo para que la ventana no se quede congelada.
2. `aplicacion/pantalla.py` toma una imagen real de los monitores y cubre la ventana de LingoLens. Así no intenta traducir su propio texto.
3. `aplicacion/puente_nucleo.py` entrega los píxeles a `nucleo/nucleo.c`. El núcleo recuerda la captura anterior y revisa una muestra de sus píxeles. Si casi todo sigue igual, no se ejecuta el OCR.
4. Tesseract convierte letras de la imagen en texto. Funciona dentro del equipo.
5. `aplicacion/ia/asistente.py` envía el texto al servicio de Ollama mediante su API local. El modelo devuelve la traducción y una explicación; los modelos `:cloud` pueden procesar el texto en Ollama Cloud.
6. `aplicacion/aprendizaje/registro.py` conserva el nivel y el vocabulario local para el contexto de conversación.
7. `aplicacion/aprendizaje/perfil_seguro.py` cifra las métricas de práctica, las palabras repetidas y el historial breve de actividad con DPAPI de Windows. Guarda señales resumidas, no el texto completo.

## Cómo funciona la conversación

La pestaña **Conversar** está construida en `ventana.py`. Cada mensaje se muestra como una burbuja y se procesa en segundo plano para que la ventana siga respondiendo. `asistente.py` manda a Ollama el mensaje reciente, una parte corta del historial, el nivel elegido, los registros de vocabulario y las palabras que el perfil seguro marca como difíciles. El nivel A1–C1 se puede cambiar desde esta pestaña. Al cambiarlo, se limpia el historial de la charla y se inicia un contexto nuevo para que el nivel anterior no condicione las respuestas. **Nueva charla** también borra el historial de la conversación sin borrar el vocabulario ni las métricas cifradas.

La pestaña **Mi progreso** muestra el resumen del perfil, las palabras que aparecen con más dificultad y la actividad reciente. Desde allí se puede guardar una palabra y su significado. El archivo `perfil_aprendizaje.seguro` está protegido por DPAPI para el usuario actual de Windows: otro usuario del equipo no puede descifrarlo sin sus credenciales. Un administrador del mismo equipo puede acceder a los archivos del usuario; ningún archivo local puede impedir eso por sí solo.

La pantalla principal permite elegir entre **Texto de pantalla** y **Texto propio**. El primer modo muestra la captura y activa **Iniciar lectura**; el segundo permite escribir o pegar texto, oculta esos controles y usa **Traducir ahora** para iniciar la petición.

El idioma de destino se elige en el control junto al título **Traducción** y comienza en inglés. Durante la petición, el mensaje de espera ocupa el cuadro de traducción; la respuesta lo reemplaza al terminar.

## Conceptos básicos

- **C y DLL**: `nucleo.c` es una parte pequeña compilada a código nativo. Una DLL permite que Python la use sin copiar el algoritmo en dos lenguajes.
- **Python**: organiza la captura, el OCR, la IA y la ventana.
- **Hilos de trabajo**: hacen que las tareas lentas ocurran fuera del hilo que dibuja la ventana.
- **SQLite**: guarda preferencias y vocabulario compatible en un archivo local sin instalar un servidor de base de datos.
- **DPAPI**: cifra el perfil de aprendizaje con la protección del usuario actual de Windows.
- **Caché de texto**: si el mismo texto sigue en pantalla, no se vuelve a pedir una traducción.
- **Límites de tamaño y tiempo**: se limitan el texto enviado al modelo y el tiempo de OCR para evitar trabajo infinito o consumo accidental.

## Dónde editar

- Apariencia y botones: `aplicacion/interfaz/ventana.py`.
- Captura y reconocimiento: `aplicacion/pantalla.py`.
- Traducciones y sugerencias: `aplicacion/ia/asistente.py`.
- Memoria de palabras y progreso: `aplicacion/aprendizaje/registro.py` y `aplicacion/aprendizaje/perfil_seguro.py`.
- Comparación rápida de pantalla: `nucleo/nucleo.c`.
- Cómo construir el `.exe`: `empaquetar.ps1`.

Después de editar C, ejecuta `construir.ps1`. Para crear una versión nueva del ejecutable, ejecuta `empaquetar.ps1`; para crear el ZIP sin `.venv`, cachés ni carpetas de compilación, ejecuta `distribuir.ps1`. Las pruebas automáticas también se ejecutan en `.github/workflows/pruebas.yml`.
