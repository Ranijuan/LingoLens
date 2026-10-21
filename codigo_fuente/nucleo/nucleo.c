#include "nucleo.h"

#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#define TP_MAX_ANCHO 16384
#define TP_MAX_ALTO 16384
#define TP_BYTES_POR_PIXEL 4
#define TP_SALTO_MUESTREO 2

static uint8_t *imagen_anterior = NULL;
static size_t bytes_anterior = 0;
static int ancho_anterior = 0;
static int alto_anterior = 0;
static int paso_anterior = 0;

static int guardar_imagen(const uint8_t *imagen, size_t bytes,
                          int ancho, int alto, int paso) {
    if (bytes != bytes_anterior) {
        uint8_t *nueva = (uint8_t *)realloc(imagen_anterior, bytes);
        if (nueva == NULL) {
            return 0;
        }
        imagen_anterior = nueva;
    }

    memcpy(imagen_anterior, imagen, bytes);
    bytes_anterior = bytes;
    ancho_anterior = ancho;
    alto_anterior = alto;
    paso_anterior = paso;
    return 1;
}

int tp_detectar_cambio(const uint8_t *imagen, int ancho, int alto,
                       int paso_fila, int sensibilidad) {
    size_t bytes;
    unsigned int diferentes = 0;
    unsigned int limite;
    int x;
    int y;
    int distinto;

    if (imagen == NULL || ancho <= 0 || alto <= 0 ||
        ancho > TP_MAX_ANCHO || alto > TP_MAX_ALTO ||
        paso_fila < ancho * TP_BYTES_POR_PIXEL) {
        return -1;
    }

    bytes = (size_t)paso_fila * (size_t)alto;
    if (bytes == 0 || bytes > (size_t)TP_MAX_ANCHO * TP_MAX_ALTO * 4U) {
        return -1;
    }

    if (imagen_anterior == NULL || bytes_anterior != bytes ||
        ancho_anterior != ancho || alto_anterior != alto ||
        paso_anterior != paso_fila) {
        if (!guardar_imagen(imagen, bytes, ancho, alto, paso_fila)) {
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
        const uint8_t *anterior = imagen_anterior + (size_t)y * (size_t)paso_fila;
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
    if (!guardar_imagen(imagen, bytes, ancho, alto, paso_fila)) {
        return -1;
    }
    return distinto;
}

void tp_reiniciar(void) {
    free(imagen_anterior);
    imagen_anterior = NULL;
    bytes_anterior = 0;
    ancho_anterior = 0;
    alto_anterior = 0;
    paso_anterior = 0;
}

const char *tp_version(void) {
    return "1.0.1";
}
