import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aplicacion.aprendizaje.registro import RegistroAprendizaje
from aplicacion.puente_nucleo import Nucleo


class ResistenciaTests(unittest.TestCase):
    def test_nucleo_procesa_capturas_repetidas(self) -> None:
        nucleo = Nucleo()
        nucleo.reiniciar()
        ancho, alto, paso = 64, 64, 64 * 4
        clara = bytes(paso * alto)
        oscura = bytes([255]) * (paso * alto)

        self.assertTrue(nucleo.cambio(clara, ancho, alto, paso))
        for _ in range(100):
            self.assertFalse(nucleo.cambio(clara, ancho, alto, paso))
            self.assertTrue(nucleo.cambio(oscura, ancho, alto, paso))
            self.assertFalse(nucleo.cambio(oscura, ancho, alto, paso))
            self.assertTrue(nucleo.cambio(clara, ancho, alto, paso))

    def test_sqlite_conserva_un_lote_grande_y_reabre(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            with patch(
                "aplicacion.aprendizaje.registro.carpeta_datos",
                return_value=Path(temporal),
            ):
                registro = RegistroAprendizaje()
                registro.guardar_palabra("x" * 200, "y" * 400, "z" * 400)
                self.assertEqual(len(registro.palabras(1)[0]), 80)
                for indice in range(200):
                    registro.guardar_palabra(
                        f"word-{indice}", "significado", "A short example."
                    )

                self.assertEqual(registro.cantidad(), 201)
                self.assertEqual(len(registro.palabras(1000)), 100)

                reabierto = RegistroAprendizaje()
                self.assertEqual(reabierto.cantidad(), 201)


if __name__ == "__main__":
    unittest.main()
