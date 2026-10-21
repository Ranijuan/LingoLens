#include "nucleo.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define TP_MAX_ANCHO 16384
#define TP_MAX_ALTO 16384
#define TP_BYTES_POR_PIXEL 4
#define TP_SALTO_MUESTREO 2
#define TP_MAX_BYTES ((size_t)TP_MAX_ANCHO * (size_t)TP_MAX_ALTO * 4U)

struct tp_contexto {
    uint8_t *imagen_anterior;
    size_t bytes_anterior;
    int ancho_anterior;
    int alto_anterior;
    int paso_anterior;
};

static int guardar_imagen(TPContexto *contexto, const uint8_t *imagen,
                          size_t bytes, int ancho, int alto, int paso) {
    if (bytes != contexto->bytes_anterior) {
        uint8_t *nueva = (uint8_t *)realloc(contexto->imagen_anterior, bytes);
        if (nueva == NULL) {
            return 0;
        }
        contexto->imagen_anterior = nueva;
    }

    memcpy(contexto->imagen_anterior, imagen, bytes);
    contexto->bytes_anterior = bytes;
    contexto->ancho_anterior = ancho;
    contexto->alto_anterior = alto;
    contexto->paso_anterior = paso;
    return 1;
}

static int dimensiones_validas(int ancho, int alto, int paso_fila,
                               size_t *bytes) {
    if (ancho <= 0 || alto <= 0 || ancho > TP_MAX_ANCHO ||
        alto > TP_MAX_ALTO || paso_fila < ancho * TP_BYTES_POR_PIXEL) {
        return 0;
    }

    *bytes = (size_t)paso_fila * (size_t)alto;
    return *bytes > 0 && *bytes <= TP_MAX_BYTES;
}

TPContexto *tp_crear(void) {
    return (TPContexto *)calloc(1, sizeof(TPContexto));
}

void tp_destruir(TPContexto *contexto) {
    if (contexto == NULL) {
        return;
    }
    free(contexto->imagen_anterior);
    free(contexto);
}

int tp_detectar_cambio(TPContexto *contexto, const uint8_t *imagen, int ancho,
                       int alto, int paso_fila, int sensibilidad) {
    size_t bytes;
    unsigned int diferentes = 0;
    unsigned int limite;
    int x;
    int y;
    int distinto;

    if (contexto == NULL || imagen == NULL ||
        !dimensiones_validas(ancho, alto, paso_fila, &bytes)) {
        return -1;
    }

    if (contexto->imagen_anterior == NULL ||
        contexto->bytes_anterior != bytes ||
        contexto->ancho_anterior != ancho ||
        contexto->alto_anterior != alto ||
        contexto->paso_anterior != paso_fila) {
        if (!guardar_imagen(contexto, imagen, bytes, ancho, alto, paso_fila)) {
            return -1;
        }
        return 1;
    }

    if (sensibilidad < 1) {
        sensibilidad = 1;
    }
    if (sensibilidad > 255) {
        sensibilidad = 255;
    }

    /* Muestrear cada segundo píxel reduce el trabajo sin perder texto móvil. */
    for (y = 0; y < alto; y += TP_SALTO_MUESTREO) {
        const uint8_t *fila = imagen + (size_t)y * (size_t)paso_fila;
        const uint8_t *anterior = contexto->imagen_anterior +
                                  (size_t)y * (size_t)paso_fila;
        for (x = 0; x < ancho; x += TP_SALTO_MUESTREO) {
            size_t indice = (size_t)x * TP_BYTES_POR_PIXEL;
            int d0 = abs((int)fila[indice] - (int)anterior[indice]);
            int d1 = abs((int)fila[indice + 1] - (int)anterior[indice + 1]);
            int d2 = abs((int)fila[indice + 2] - (int)anterior[indice + 2]);
            if (d0 + d1 + d2 >= sensibilidad) {
                diferentes++;
            }
        }
    }

    /* Se pide una diferencia visible para ignorar parpadeos y cursor. */
    limite = (unsigned int)((ancho * alto) / 16000);
    if (limite < 20U) {
        limite = 20U;
    }

    distinto = diferentes >= limite;
    if (!guardar_imagen(contexto, imagen, bytes, ancho, alto, paso_fila)) {
        return -1;
    }
    return distinto;
}

void tp_reiniciar(TPContexto *contexto) {
    if (contexto == NULL) {
        return;
    }
    free(contexto->imagen_anterior);
    contexto->imagen_anterior = NULL;
    contexto->bytes_anterior = 0;
    contexto->ancho_anterior = 0;
    contexto->alto_anterior = 0;
    contexto->paso_anterior = 0;
}

const char *tp_version(void) {
    return "1.3.0";
}
