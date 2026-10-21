import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aplicacion.aprendizaje.registro import RegistroAprendizaje


class RegistroAprendizajeTests(unittest.TestCase):
    def test_guarda_actualiza_y_cuenta_palabras(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            with patch(
                "aplicacion.aprendizaje.registro.carpeta_datos",
                return_value=Path(temporal),
            ):
                registro = RegistroAprendizaje()
                self.assertEqual(registro.guardar_palabra(" book ", "libro", "A book"), 1)
                self.assertEqual(registro.guardar_palabra("BOOK", "libro actualizado", "The book"), 1)
                self.assertEqual(registro.cantidad(), 1)
                self.assertEqual(registro.palabras(), ["book"])

    def test_valida_nivel_y_guarda_modelo(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            with patch(
                "aplicacion.aprendizaje.registro.carpeta_datos",
                return_value=Path(temporal),
            ):
                registro = RegistroAprendizaje()
                self.assertEqual(registro.nivel(), "A2")
                registro.guardar_nivel("C1")
                self.assertEqual(registro.nivel(), "C1")
                registro.guardar_nivel("nivel-invalido")
                self.assertEqual(registro.nivel(), "A2")
                registro.guardar_modelo("qwen2.5:1.5b")
                self.assertEqual(registro.modelo(), "qwen2.5:1.5b")


if __name__ == "__main__":
    unittest.main()
