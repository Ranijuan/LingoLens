from concurrent.futures import ThreadPoolExecutor
import unittest

from aplicacion.puente_nucleo import Nucleo


def captura(ancho: int, alto: int, paso: int, valores: list[tuple[int, int, int]]) -> bytes:
    datos = bytearray(paso * alto)
    for x, y, valor in valores:
        indice = y * paso + x * 4
        datos[indice : indice + 3] = bytes((valor, valor, valor))
    return bytes(datos)


class NucleoProfundoTests(unittest.TestCase):
    def test_las_instancias_conservan_contextos_independientes(self) -> None:
        primero = Nucleo()
        segundo = Nucleo()
        imagen = captura(64, 64, 64 * 4, [])

        self.assertTrue(primero.cambio(imagen, 64, 64, 64 * 4))
        self.assertTrue(segundo.cambio(imagen, 64, 64, 64 * 4))
        self.assertFalse(primero.cambio(imagen, 64, 64, 64 * 4))

        primero.cerrar()
        with self.assertRaises(RuntimeError):
            primero.cambio(imagen, 64, 64, 64 * 4)
        segundo.cerrar()

    def test_acepta_padding_y_detecta_cambios_muestreados(self) -> None:
        ancho, alto, paso = 100, 100, 100 * 4 + 12
        base = captura(ancho, alto, paso, [])
        cambios = [(indice * 2, 0, 255) for indice in range(20)]
        modificada = captura(ancho, alto, paso, cambios)
        nucleo = Nucleo()

        self.assertTrue(nucleo.cambio(base, ancho, alto, paso))
        self.assertFalse(nucleo.cambio(base, ancho, alto, paso))
        self.assertTrue(nucleo.cambio(modificada, ancho, alto, paso))

    def test_accesos_concurrentes_no_rompen_el_contexto(self) -> None:
        nucleo = Nucleo()
        imagen = captura(64, 64, 64 * 4, [])
        nucleo.reiniciar()

        def ciclo(_: int) -> bool:
            return nucleo.cambio(imagen, 64, 64, 64 * 4)

        with ThreadPoolExecutor(max_workers=4) as ejecutor:
            resultados = list(ejecutor.map(ciclo, range(40)))

        self.assertIn(True, resultados)
        self.assertTrue(all(isinstance(resultado, bool) for resultado in resultados))

    def test_rechaza_dimensiones_fuera_del_limite_sin_reservar(self) -> None:
        nucleo = Nucleo()
        with self.assertRaises(ValueError):
            nucleo.cambio(b"", 16385, 1, 16385 * 4)
        with self.assertRaises(ValueError):
            nucleo.cambio(b"", 1, 16385, 4)
        with self.assertRaises(ValueError):
            nucleo.cambio(b"", 4, 1, -1)


if __name__ == "__main__":
    unittest.main()
