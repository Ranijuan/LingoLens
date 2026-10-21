import unittest

from aplicacion.puente_nucleo import Nucleo


class NucleoTests(unittest.TestCase):
    def test_detecta_cambio_y_omite_captura_igual(self) -> None:
        nucleo = Nucleo()
        captura = bytes(4 * 10 * 10)
        self.assertTrue(nucleo.cambio(captura, 10, 10, 40))
        self.assertFalse(nucleo.cambio(captura, 10, 10, 40))

        modificada = bytes([255]) * len(captura)
        self.assertTrue(nucleo.cambio(modificada, 10, 10, 40))

    def test_rechaza_dimensiones_invalidas(self) -> None:
        nucleo = Nucleo()
        with self.assertRaises(ValueError):
            nucleo.cambio(b"", 0, 2, 8)
        with self.assertRaises(ValueError):
            nucleo.cambio(bytes(8), 2, 2, 4)


if __name__ == "__main__":
    unittest.main()
