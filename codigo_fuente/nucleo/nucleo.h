#ifndef LINGOLENS_NUCLEO_H
#define LINGOLENS_NUCLEO_H

#include <stdint.h>

#ifdef _WIN32
#define TP_API __declspec(dllexport)
#else
#define TP_API
#endif

/*
 * Compara una imagen BGRA con la captura anterior.
 * Devuelve 1 si cambió la pantalla, 0 si sigue igual y -1 si hubo un error.
 * La memoria anterior pertenece al núcleo y se libera al cerrar la aplicación.
 */
TP_API int tp_detectar_cambio(const uint8_t *imagen, int ancho, int alto,
                              int paso_fila, int sensibilidad);

TP_API void tp_reiniciar(void);
TP_API const char *tp_version(void);

#endif
