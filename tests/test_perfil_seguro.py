import tempfile
import unittest
from pathlib import Path

from aplicacion.aprendizaje.perfil_seguro import PerfilSeguro


class PerfilSeguroTests(unittest.TestCase):
    def test_persiste_metricas_sin_guardar_texto_plano(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "perfil_aprendizaje.seguro"
            perfil = PerfilSeguro(ruta)
            perfil.establecer_contexto("B1", "inglés")
            perfil.registrar("correccion", "inglés", "I has a book", dificultad=True)
            perfil.registrar("traduccion", "inglés", "I have a book")

            datos = ruta.read_bytes()
            self.assertNotIn(b"book", datos)
            self.assertNotIn(b"I have", datos)

            reabierto = PerfilSeguro(ruta).resumen()
            self.assertEqual(reabierto["nivel"], "B1")
            self.assertEqual(reabierto["interacciones"], 2)
            self.assertIn("book", reabierto["palabras_dificiles"])
            self.assertEqual(len(reabierto["historial_reciente"]), 2)

    def test_limita_el_historial_y_las_palabras(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            perfil = PerfilSeguro(Path(temporal) / "perfil_aprendizaje.seguro")
            for indice in range(220):
                perfil.registrar("practica", "inglés", f"word-{indice}")

            resumen = perfil.resumen()
            self.assertEqual(resumen["interacciones"], 220)
            self.assertLessEqual(len(resumen["historial_reciente"]), 8)
            self.assertLessEqual(resumen["palabras_practicadas"], 500)


if __name__ == "__main__":
    unittest.main()
