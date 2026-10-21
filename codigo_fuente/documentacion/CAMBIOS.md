# Registro de cambios

Las horas corresponden a America/Bogota (UTC−05:00). El historial y las etiquetas de versión están publicados en GitHub.

## 2026-10-21 13:39 · Cierre de Qt en CI

- GitHub Actions confirmó las 19 pruebas, pero la primera ejecución devolvía código 1 al terminar el proceso aunque todas las aserciones fueran correctas.
- `test_interfaz.py` ahora destruye explícitamente la ventana Qt después de probar el cierre; esto evita dejar objetos Qt vivos en Python 3.13 del runner.
- La ejecución del workflow en el commit `e59595e` terminó correctamente.

**Resumen del cambio:** las pruebas locales y las de GitHub terminan con código 0; la automatización queda estable también en Python 3.13.

## 2026-10-21 13:35 · Verificación de GitHub Actions

- La primera ejecución del workflow detectó que una prueba concurrente asumía que `reiniciar()` y `cambio()` eran una operación atómica entre hilos.
- Se corrigió la prueba para validar el contrato real del núcleo: acceso concurrente protegido, resultados booleanos y ausencia de corrupción o excepciones.
- La ejecución posterior de GitHub Actions terminó correctamente en el commit `e90eb2f`.

**Resumen del cambio:** la automatización de GitHub ya pasa después de corregir una prueba demasiado estricta.

## 2026-10-21 13:29 · Núcleo profundo, perfil seguro y automatización

- `nucleo.c` y `nucleo.h`: se reemplazó la imagen global por contextos independientes con creación, reinicio y destrucción explícitos. Esto evita que dos instancias compartan capturas y permite liberar la memoria nativa al cerrar.
- `puente_nucleo.py`: se configuraron las nuevas funciones C, se protegió cada contexto con un bloqueo y se añadió `cerrar()` para liberar la DLL de forma controlada.
- `test_nucleo_profundo.py`: se añadieron pruebas para padding, contextos independientes, reinicios concurrentes, límites de tamaño y ciclos repetidos.
- `perfil_seguro.py`: se añadió un archivo cifrado con DPAPI de Windows. Guarda nivel, idioma, palabras practicadas, dificultad y actividad resumida; no guarda el texto completo de pantalla o conversación.
- `registro.py` y `ventana.py`: el perfil se actualiza desde traducciones, conversación, cambios de nivel y vocabulario guardado. La pestaña **Mi progreso** muestra el resumen, dificultades, historial reciente y un formulario para guardar palabras.
- `Trabajo` y `closeEvent`: se cancelan señales pendientes, se limpian trabajos en cola y se espera brevemente a las tareas activas antes de liberar el núcleo.
- `test_interfaz.py` y `test_perfil_seguro.py`: se probaron la interfaz en modo `offscreen`, el guardado de vocabulario y la persistencia cifrada.
- `.github/workflows/pruebas.yml`: GitHub compila C, instala dependencias, ejecuta la suite, compila Python y revisa el parche en cada cambio.
- `distribuir.ps1`: automatiza el ZIP limpio excluyendo entorno virtual, compilaciones, Tesseract extraído y cachés; `LingoLens.exe` queda como primera entrada del archivo.
- La suite pasó 19 pruebas; también pasaron `compileall`, la compilación C y una prueba real del script de distribución con 41 archivos.

**Resumen del proyecto:** el núcleo tiene memoria aislada por instancia, el cierre libera recursos con más seguridad, el usuario dispone de un historial de aprendizaje cifrado y GitHub ya tiene una ruta automática para detectar regresiones.

## 2026-10-21 13:08 · Correcciones de resistencia y seguridad

- `pantalla.py`: la extracción temporal de Tesseract ahora valida cada ruta del ZIP antes de escribirla y comprueba `tesseract.exe`, `eng.traineddata` y `spa.traineddata` antes de reutilizar una extracción anterior.
- `asistente.py`: se evita iniciar servidores Ollama duplicados, se detiene el proceso que la aplicación inició si no queda disponible y el límite de 15 minutos para descargar modelos cubre también una salida sin actividad.
- `puente_nucleo.py`: se añadió un bloqueo por instancia para proteger el estado estático del núcleo C si llegan capturas y reinicios desde hilos distintos.
- `nucleo.c`: la versión expuesta por la DLL pasa a `1.0.1`.
- `tests/test_pantalla.py`: se probaron deduplicación de OCR, rutas inseguras y recuperación de una extracción incompleta.
- La suite con el entorno virtual del proyecto pasó 12 pruebas y cinco pasadas consecutivas, 60 ejecuciones en total durante esta ronda; también se comprobó `compileall` y `git diff --check`.
- Se reconstruyó el ejecutable único: 122.759.996 bytes, SHA-256 `51AA2A86BD6083F8CE1EE798E51DDC76454CE93AF8169B79D701CDC2B3EA11A8`.
- Se publicó [LingoLens v1.0.1](https://github.com/Ranijuan/LingoLens/releases/tag/v1.0.1); GitHub expone allí el tamaño y el SHA-256 verificables del asset descargable.

**Resumen del proyecto:** se corrigieron riesgos de concurrencia, extracción incompleta, rutas no seguras y procesos Ollama abandonados. La aplicación `v1.0.1` está publicada, probada y lista para descargar.

## 2026-10-21 · README de GitHub y primeras pruebas automáticas

- Se actualizó el README principal para separar la descarga de la aplicación desde Releases de la preparación del código fuente.
- Se documentó el comando de pruebas y se explicó que el ejecutable no forma parte del historial normal del repositorio.
- Se añadieron siete pruebas con `unittest` para SQLite, respuestas JSON de Ollama, validaciones del asistente y detección de cambios del núcleo C.
- La prueba del núcleo C compila automáticamente `nucleo.dll` si el repositorio recién clonado todavía no tiene la DLL.
- Se añadieron pruebas de resistencia para 100 ciclos de capturas alternas y para un lote de 201 palabras con reapertura de SQLite.
- Se corrigió el cierre de conexiones SQLite con un gestor de contexto; esto evita dejar el archivo de aprendizaje bloqueado en Windows.
- Las pruebas pasan sin abrir la interfaz ni conectarse a Ollama.

**Resumen del proyecto:** el repositorio ya explica cómo descargar la aplicación y cómo preparar el código. Las funciones principales tienen una primera comprobación automática y el almacenamiento local cierra sus conexiones correctamente.

## 2026-10-21 · Pruebas intensivas de la aplicación

- Se ejecutaron las nueve pruebas automáticas y después cinco pasadas consecutivas, 45 ejecuciones en total, sin fallos intermitentes.
- La prueba de resistencia procesó 100 ciclos de capturas alternas en el núcleo C y comprobó que las capturas iguales se omiten.
- SQLite conservó un lote de 201 palabras, limitó entradas largas y permitió reabrir la base sin bloqueo.
- Se compiló el código Python con `compileall` sin errores.
- Se abrió el ejecutable real y Windows mostró `LingoLens · Aprende mientras lees`.
- Ollama respondió con los tres modelos instalados; una traducción y una corrección gramatical reales pasaron por el modelo `qwen2.5:1.5b`.

**Resumen del proyecto:** las rutas principales de código, almacenamiento, núcleo C, ejecutable e IA local respondieron correctamente en esta ronda. Falta automatizar la comprobación del ejecutable y del OCR dentro de GitHub Actions.

## 2026-09-30 · Revisión de cierre y limpieza de residuos

- Se revisaron todos los módulos, scripts, recursos de construcción, README y documentos técnicos para sincronizar la descripción con el comportamiento actual.
- Se retiraron un parámetro y una consulta SQLite sin uso en traducción, un cálculo y un import huérfanos, y estilos asociados a controles retirados.
- Se conservó el historial y almacenamiento SQLite de vocabulario para no perder datos previos; la interfaz actual no permite añadir palabras nuevas.
- Se corrigió el aviso superior para no afirmar que toda IA se ejecuta localmente; los modelos `:cloud` pueden enviar texto a Ollama Cloud.
- Se localizaron cuatro carpetas `__pycache__` antes del empaquetado; la comprobación final encontró cero. Ya no estaban presentes al ejecutar la limpieza manual. Se conservaron `.venv`, `build` (incluye informes de diagnóstico), `dist`, OCR, DLL y metadatos `.git`.
- Se actualizaron README, guía, instalación, dependencias, estado técnico y este registro.
- Se reconstruyó y abrió el ejecutable final; `LingoLens.exe` y `codigo_fuente\dist\LingoLens.exe` son idénticos, de 119.909.405 bytes.
- SHA-256 del ejecutable final: `AC78F080BF8CDE9A911589B0A38B3714A136952FDBBAC0E0F34D27D664621683`.

**Conteo de esta limpieza:** 2 módulos de código modificados, 7 documentos actualizados, 0 carpetas de caché eliminadas manualmente (4 localizadas antes y 0 restantes al cierre), y 0 datos de usuario, modelos, recursos o artefactos de distribución eliminados.

**Resumen:** documentación y código quedaron alineados; se eliminó solo código/estilo sin referencias y cachés regenerables, preservando datos y artefactos útiles.

## 2026-09-30 · Traducción de Gemma y cambio de nivel en chat

- Se comprobó que Qwen2.5 1.5B y Qwen3 8B traducen correctamente; Gemma 4 26B también traduce, pero una solicitud inicial tardó 151 s y excedía el timeout anterior de 45 s.
- Se compactó la respuesta JSON de traducción a los campos que muestra la interfaz, se delimitó explícitamente el texto fuente y se amplió el timeout a 180 s. Gemma respondió con la traducción correcta en la prueba final.
- El timeout de conversación ahora usa el mismo límite ampliado para cubrir la carga en frío de modelos grandes.
- El selector A1–C1 está en **Conversar** y sincronizado con el nivel principal. Cambiar el nivel limpia historial y mensaje de reintento, e inicia un contexto nuevo; el selector se bloquea mientras una respuesta está en curso.
- No existe suite de pruebas automatizada en el proyecto. Se validaron las tres traducciones reales disponibles y el cambio de nivel A1→A2→B1 mediante pruebas manuales controladas.
- Se reconstruyó y abrió el ejecutable final; ambas copias son idénticas, de 119.910.523 bytes.
- SHA-256 del ejecutable final: `17013C62962B884CAD97794E6183D3455ECB53565CAD0690698D9C05C3B7C5B4`.

**Conteo de esta modificación:** 2 archivos de código modificados, 6 documentos actualizados, 3 modelos locales verificados, 1 prueba de cambio de nivel y 0 archivos eliminados.

**Resumen del cambio:** los timeouts ya no interrumpen a Gemma durante su generación lenta, las traducciones contienen solo el texto fuente y cambiar el nivel ya no conserva el contexto anterior.

## 2026-09-30 · Idioma destino y estado de traducción

- Se añadió una lista de idioma destino junto al título de traducción, con inglés seleccionado inicialmente y español como alternativa.
- El idioma elegido se envía explícitamente al asistente, que ahora instruye al modelo a producir la traducción en ese destino.
- El cuadro de resultado muestra `La IA está traduciendo…` durante la petición y sustituye el aviso por la traducción o por el error al finalizar.
- Se comprobó una traducción real de español a inglés con Qwen3 y una prueba de interfaz de los estados de espera/resultado.
- Se reconstruyó y abrió el ejecutable final; `LingoLens.exe` y `codigo_fuente\dist\LingoLens.exe` son idénticos, de 119.910.725 bytes.
- SHA-256 del ejecutable final: `9CF8282791EFDA2DA627B691ABBCC7F973E2FC0F904B7DAAE23B0D53BE37C974`.

**Conteo de esta modificación:** 2 archivos de código modificados, 4 documentos actualizados, 1 traducción real verificada y 1 prueba de interfaz superada.

**Resumen del cambio:** el destino se puede elegir, empieza en inglés y la salida queda validada en inglés; el aviso de actividad ahora ocupa el cuadro de traducción mientras trabaja la IA.

## 2026-09-30 · Rendimiento de conversación y limpieza de modelos

- Se eliminó `kimi-k3:cloud` de Ollama y se restauró `qwen2.5:1.5b` como modelo guardado en las preferencias.
- Se confirmó que `gemma4:26b` y `qwen3:8b` sí responden, pero sus respuestas tardaban más que el timeout porque generaban razonamiento extendido.
- Se añadió `think: false` a las peticiones de traducción y conversación. Las pruebas reales respondieron en aproximadamente 14,3 s con Gemma y 4,2 s con Qwen3.
- Se añadió en **Conversar** el indicador `Nivel de inglés · A1–C1`, sincronizado con el nivel principal.
- Se regeneró el ejecutable final de 119.910.202 bytes y se verificó su arranque; la copia de la raíz y la de `codigo_fuente\dist` son idénticas.
- SHA-256 del ejecutable final: `7C0EC67AB0594DB2468984263D7F3E97C9EE129F483CDDBA0FBF624C607D735B`.

**Conteo de esta modificación:** 2 archivos de código modificados, 2 documentos actualizados, 1 modelo eliminado, 2 modelos verificados y 0 modelos locales eliminados.

**Resumen del cambio:** Gemma y Qwen3 ya responden sin agotar el timeout, Kimi fue retirado y el nivel activo queda visible durante la conversación.

## 2026-09-30 · Modelos cloud, selector de conversación y traducción

- Se verificó que `kimi-k3:cloud` devuelve `402 Payment Required`: es un modelo remoto de Ollama Cloud y requiere autenticación con acceso de pago.
- Se verificó que `gemma4:25b` devuelve `404 Not Found`; el nombre instalado en este equipo es `gemma4:26b`, que sí respondió correctamente.
- Se añadió un selector de modelo dentro de **Conversar**, sincronizado con el selector de traducción y persistente entre sesiones.
- La interfaz distingue `IA local` de `IA cloud` y muestra instrucciones específicas para errores `402` y `404`.
- Se corrigió el texto auxiliar de la tarjeta de entrada y se comprobó una traducción real con `qwen2.5:1.5b`.

**Conteo de esta modificación:** 2 archivos de código modificados, 5 documentos actualizados, 2 pruebas directas de modelos, 1 prueba real de traducción y 0 cambios en el formato de los modelos instalados.

**Resumen del cambio:** los modelos problemáticos ahora tienen una explicación precisa, se puede cambiar de modelo desde el chat y el modelo local funcional queda validado.

## 2026-09-30 · Traducción manual y ajuste de interfaz

- Se corrigió el flujo de **Traducir ahora** para que envíe el texto actual del editor cuando la IA está disponible.
- Se añadió el selector **Texto de pantalla** / **Texto propio**. El modo propio permite escribir o pegar texto, oculta la captura y el botón de lectura, y el modo pantalla restaura esos controles.
- Se retiraron de la pantalla principal los paneles de corrección y palabras para aprender; queda una explicación amplia para mostrar el resultado didáctico.
- Se trasladó el mensaje introductorio a una notificación superior izquierda y se añadió en **Conversar** el modelo activo con la indicación de que la IA es local.
- Se validaron el clic del botón y el cambio de modos con una prueba de interfaz `offscreen`.
- Se regeneró el ejecutable final y se probó su arranque. `LingoLens.exe` y `codigo_fuente\dist\LingoLens.exe` son idénticos, de 119.907.490 bytes.
- SHA-256 del ejecutable final: `9772D2D6AF964EE45B517943E23D72663EC3926496D3EB918902C495447606E7`.

**Conteo de esta modificación:** 1 archivo de código modificado, 3 documentos actualizados, 1 ejecutable regenerado y 0 archivos de funcionalidad eliminados fuera de la interfaz solicitada.

**Resumen del cambio:** ahora se puede traducir texto propio con el botón, alternar entre pantalla y entrada manual, y ver claramente qué modelo local atiende la conversación.

## 2026-09-30 · Limpieza de instrumentación temporal

- Se eliminaron los registros de depuración temporales de `aplicacion\ia\asistente.py` y `aplicacion\interfaz\ventana.py`.
- Se retiraron las rutas absolutas del equipo y los imports que solo servían para escribir esos registros.
- No se modificaron la captura, el OCR, la traducción, la conversación, la persistencia ni el empaquetado.
- `compileall` terminó sin errores después de la limpieza.
- Se creó `codigo_fuente\.venv` y se instalaron las dependencias declaradas en `requirements.txt`.
- `construir.ps1` y `empaquetar.ps1` terminaron correctamente; se generó `codigo_fuente\dist\LingoLens.exe` de 119.908.025 bytes.
- El ejecutable empaquetado arrancó correctamente en una prueba controlada y la copia de `LingoLens.exe` en la raíz quedó sincronizada.
- SHA-256 del ejecutable final: `87255CD1110FC5FCE37E466823B5D0947876A55C54E3EBDF5FC1A2D052CA2A56`.

**Resumen del cambio:** se retiró código de diagnóstico que no era necesario para ejecutar LingoLens y que podía escribir datos de la conversación en una ruta específica del equipo.

## 2026-09-28 12:45–12:51 · Organización y traslado de la carpeta de entrega

- Se preparó `proyectos\LingoLens` con `LingoLens.exe` en la raíz para abrirlo rápidamente.
- Se agrupó el código C y Python, los scripts, los requisitos, el núcleo C y toda la documentación en `codigo_fuente`.
- Se conservaron el archivo OCR comprimido y los idiomas inglés y español; se omitieron el entorno virtual, cachés, archivos temporales de compilación, el ejecutable duplicado de `dist` y la copia descomprimida de Tesseract.
- Se ajustaron los README con instrucciones sencillas y con la nueva ubicación del ejecutable.
- Se verificó que el SHA-256 del ejecutable nuevo coincide con el ejecutable funcional verificado anteriormente: `3CCC0161C52E600794A524EE99BB4F339DF1C6F418EE6BC6BE2CE6707FFFF273`.
- Se compararon los hashes de los 37 archivos fuente y recursos sin cambios; no hubo diferencias.
- Se abrió `LingoLens.exe` desde la carpeta nueva y apareció la ventana `LingoLens · Aprende mientras lees`.
- Tras confirmar que no quedaban procesos usando la ruta anterior, se retiró `proyectos\traductor-pantalla`; se liberaron aproximadamente 1.148,2 MB de duplicados, entorno virtual y artefactos temporales.

**Resumen del proyecto:** el proyecto queda en `proyectos\LingoLens`, con el ejecutable listo en la raíz y el código y la documentación organizados debajo. Se comprobó que la nueva copia abre correctamente y se retiró la carpeta duplicada anterior.

## 2026-09-28 12:28–12:33 · Corrección de arranque del ejecutable y pruebas funcionales

- Se diagnosticó el cierre del `.exe`: PyInstaller estaba empaquetando una copia incompleta de ICU y QtWidgets fallaba con `DLL load failed`.
- Se añadió `aplicacion\qt_runtime_hook.py` para registrar las rutas nativas de Qt antes de iniciar la interfaz.
- Se actualizó `LingoLens.spec` para excluir las DLL ICU incompatibles del entorno de construcción y se mantuvo Tesseract dentro de `recursos\tesseract.zip`.
- Se regeneró `dist\LingoLens.exe` como ejecutable único de 117,1 MB.
- Se ejecutó el archivo final y Windows mostró la ventana `LingoLens · Aprende mientras lees` sin el diálogo de excepción.
- Se probó el núcleo C: la primera captura devolvió cambio, la misma captura repetida no volvió a procesarse y después de reiniciar volvió a detectar cambio.
- Se probó OCR con una captura real del escritorio; Tesseract devolvió texto y una vista de 480 × 270 píxeles.
- Se probó la conversación real con Ollama; el asistente corrigió `I has a book.` a `I have a book.`.
- `compileall` terminó sin errores.

**Resumen del proyecto:** el ejecutable final arranca y sus rutas principales funcionan en este PC: interfaz, núcleo C, OCR y asistente local. La prueba visual automatizada no pudo hacer clic en los controles porque el adaptador de ventanas de esta sesión solo expuso el inventario básico, pero la ventana real quedó abierta y las funciones internas se ejecutaron con datos reales.

## 2026-09-28 11:26–11:30 · Instalación final y verificación local

- Se comprobaron las dependencias Python del entorno `.venv`; `PySide6`, `mss`, `Pillow`, `requests` y `PyInstaller` ya estaban instaladas y cumplen `requirements.txt`.
- Se inició Ollama en segundo plano y se descargó el modelo local `qwen2.5:1.5b` (986 MB).
- Se confirmó una respuesta real de la API local: `asistente listo`.
- Se recompiló `nucleo.dll` con GCC y se regeneró `dist\LingoLens.exe` como archivo único de 178 MB.
- Se confirmó que el ejecutable contiene Tesseract 5.4.0.20240606 y los datos OCR en inglés y español.

**Resumen del proyecto:** LingoLens queda instalado y listo para traducir, enseñar y conversar en este PC. El ejecutable está en `dist\LingoLens.exe`; Ollama y `qwen2.5:1.5b` quedan instalados como servicio y modelo local para que la IA no se incluya dentro del archivo de 178 MB.

## 2026-09-28 10:14–10:16 · Documentación de arquitectura y referencias

- Se documentaron la estructura local, las ideas principales, el recorrido del texto y el estado de la aplicación.
- Se registraron librerías, versiones observadas, repositorios y documentación oficial.
- Se anotó que el servidor Ollama no estaba activo durante la comprobación y que el modelo no pudo confirmarse.

**Resumen del proyecto:** fuente Python compilable y ejecutable único generado. La charla real debe confirmarse cuando Ollama esté activo con el modelo esperado.

## 2026-09-28 09:59–10:04 · Conversación y mejora visual

- Se añadió una pestaña para conversar con el tutor local, con historial breve, accesos rápidos y envío con Enter.
- Las respuestas se ajustan al nivel de estudio y al vocabulario guardado en este PC; se incluye el texto leído en pantalla cuando existe.
- Se mejoraron tamaños de letra, contraste, espacios, pestañas y burbujas de conversación usando la fuente del sistema.
- Se limitó el historial que recibe la IA para que cada consulta tenga un tamaño controlado. Si falla una respuesta, el mensaje queda listo para reintentar.
- Se actualizó la guía y el README con instrucciones básicas de uso.
- Se recompiló el núcleo C y se empaquetó `dist\LingoLens.exe` con fecha 10:04:24.

**Resumen del proyecto:** traducción y conversación están integradas en el ejecutable. El servicio local de IA sigue siendo un requisito separado.

## 2026-09-27 21:51–22:03 · Primera versión funcional

- Se creó una interfaz de escritorio en español con idioma de origen, nivel de estudio, captura, traducción y vocabulario.
- Se añadió un núcleo C que detecta cambios visibles y evita ejecutar OCR repetidamente sobre una pantalla quieta.
- Se añadió OCR local con Tesseract para inglés y español.
- Se conectó el asistente local a Ollama, con traducción, corrección gramatical y sugerencias de palabras.
- Se guardan palabras elegidas y nivel de estudio en SQLite local.
- Se añadió compilación C y empaquetado PyInstaller en un solo `.exe`.
- Se usa una vista previa tomada de la pantalla real; no se generan imágenes artificiales.

**Resumen del proyecto:** quedó la base para leer, traducir y guardar vocabulario localmente con C, Python y Tesseract.
