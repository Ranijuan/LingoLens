#ifndef LINGOLENS_NUCLEO_H
#define LINGOLENS_NUCLEO_H

#include <stdint.h>

#ifdef _WIN32
#define TP_API __declspec(dllexport)
#else
#define TP_API
#endif

typedef struct tp_contexto TPContexto;

/* Cada contexto conserva su propia captura anterior. */
TP_API TPContexto *tp_crear(void);
TP_API void tp_destruir(TPContexto *contexto);

/*
 * Compara una imagen BGRA con la captura anterior del contexto.
 * Devuelve 1 si cambió la pantalla, 0 si sigue igual y -1 si hubo un error.
 */
TP_API int tp_detectar_cambio(TPContexto *contexto, const uint8_t *imagen,
                              int ancho, int alto, int paso_fila,
                              int sensibilidad);

TP_API void tp_reiniciar(TPContexto *contexto);
TP_API const char *tp_version(void);

#endif
