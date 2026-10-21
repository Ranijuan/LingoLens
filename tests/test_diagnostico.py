import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from aplicacion.diagnostico import ResultadoChequeo, comprobar_entorno


class AsistenteFalso:
    def __init__(self, disponible: bool, modelos: set[str] | None = None) -> None:
        self.modelo = "qwen2.5:1.5b"
        self._disponible = disponible
        self._modelos = modelos or set()

    def disponible(self) -> bool:
        return self._disponible

    def modelos_instalados(self) -> set[str]:
        return self._modelos


class DiagnosticoTests(unittest.TestCase):
    @patch("aplicacion.diagnostico.PerfilSeguro.comprobar_proteccion", return_value=True)
    @patch("aplicacion.diagnostico._comprobar_ocr")
    @patch("aplicacion.diagnostico._comprobar_nucleo")
    def test_entorno_completo_con_ollama_y_modelo(
        self,
        nucleo,
        ocr,
        _proteccion,
    ) -> None:
        nucleo.return_value = ResultadoChequeo("nucleo", "Núcleo C", "correcto", "OK")
        ocr.return_value = ResultadoChequeo("ocr", "OCR", "correcto", "OK")
        with tempfile.TemporaryDirectory() as temporal:
            resultados = comprobar_entorno(
                AsistenteFalso(True, {"qwen2.5:1.5b"}),
                Path(temporal),
            )

        por_clave = {resultado.clave: resultado for resultado in resultados}
        self.assertEqual(por_clave["ollama"].estado, "correcto")
        self.assertEqual(por_clave["modelo"].estado, "correcto")
        self.assertEqual(por_clave["modelo"].modelos, ("qwen2.5:1.5b",))

    @patch("aplicacion.diagnostico.PerfilSeguro.comprobar_proteccion", return_value=True)
    @patch("aplicacion.diagnostico._comprobar_ocr")
    @patch("aplicacion.diagnostico._comprobar_nucleo")
    def test_ollama_ausente_no_impide_el_diagnostico(
        self,
        nucleo,
        ocr,
        _proteccion,
    ) -> None:
        nucleo.return_value = ResultadoChequeo("nucleo", "Núcleo C", "correcto", "OK")
        ocr.return_value = ResultadoChequeo("ocr", "OCR", "correcto", "OK")
        with tempfile.TemporaryDirectory() as temporal:
            resultados = comprobar_entorno(AsistenteFalso(False), Path(temporal))

        por_clave = {resultado.clave: resultado for resultado in resultados}
        self.assertEqual(por_clave["ollama"].estado, "advertencia")
        self.assertEqual(por_clave["modelo"].estado, "advertencia")
        self.assertIn("OCR seguirá funcionando", por_clave["ollama"].solucion)

    @patch("aplicacion.diagnostico.PerfilSeguro.comprobar_proteccion", return_value=True)
    @patch("aplicacion.diagnostico._comprobar_ocr")
    @patch("aplicacion.diagnostico._comprobar_nucleo")
    def test_modelo_ausente_indica_como_resolverlo(
        self,
        nucleo,
        ocr,
        _proteccion,
    ) -> None:
        nucleo.return_value = ResultadoChequeo("nucleo", "Núcleo C", "correcto", "OK")
        ocr.return_value = ResultadoChequeo("ocr", "OCR", "correcto", "OK")
        with tempfile.TemporaryDirectory() as temporal:
            resultados = comprobar_entorno(
                AsistenteFalso(True, {"otro:1b"}),
                Path(temporal),
            )

        modelo = next(resultado for resultado in resultados if resultado.clave == "modelo")
        self.assertEqual(modelo.estado, "advertencia")
        self.assertIn("Preparar IA local", modelo.solucion)


if __name__ == "__main__":
    unittest.main()
