import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget

from aplicacion.diagnostico import ResultadoChequeo
from aplicacion.interfaz.ventana import VentanaPrincipal


class InterfazTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aplicacion = QApplication.instance() or QApplication([])

    def test_carga_tres_pestanas_y_guarda_palabra_en_progreso(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            with patch(
                "aplicacion.aprendizaje.registro.carpeta_datos",
                return_value=Path(temporal),
            ):
                ventana = VentanaPrincipal()
                pestanas = ventana.centralWidget()
                self.assertIsInstance(pestanas, QTabWidget)
                self.assertEqual(pestanas.count(), 3)
                self.assertEqual(ventana.boton_diagnostico.text(), "Diagnóstico")
                self.assertEqual(ventana.boton_modelos.text(), "Modelos…")

                ventana._diagnostico_terminado(
                    {
                        "resultados": [
                            ResultadoChequeo(
                                "ollama",
                                "Ollama",
                                "advertencia",
                                "Ollama no responde.",
                                "Abre Ollama.",
                            ),
                            ResultadoChequeo(
                                "modelo",
                                "Modelo de IA",
                                "advertencia",
                                "Falta el modelo.",
                                "Prepara la IA.",
                            ),
                        ]
                    }
                )
                self.assertFalse(ventana._ia_lista)
                self.assertTrue(ventana.boton_diagnostico.isEnabled())

                ventana.selector_fuente.setCurrentIndex(1)
                self.assertFalse(ventana.texto_origen.isReadOnly())
                ventana.entrada_palabra.setText("book")
                ventana.entrada_significado.setText("libro")
                ventana._guardar_palabra_desde_ui()
                self.assertEqual(ventana._registro.palabras(), ["book"])

                ventana.close()
                ventana.deleteLater()
                self.aplicacion.processEvents()


if __name__ == "__main__":
    unittest.main()
