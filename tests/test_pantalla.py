import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from aplicacion.pantalla import _extraer_tesseract, _normalizar_texto


class PantallaTests(unittest.TestCase):
    def test_normaliza_texto_sin_repetir_lineas(self) -> None:
        texto = "Hello   world.\nHello world.\n\nThis is new."
        self.assertEqual(_normalizar_texto(texto), "Hello world. This is new.")

    def test_rechaza_ruta_insegura_en_paquete_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            archivo = Path(temporal) / "ocr.zip"
            with zipfile.ZipFile(archivo, "w") as comprimido:
                comprimido.writestr("../archivo-fuera.txt", "no")
            with patch("aplicacion.pantalla.tempfile.gettempdir", return_value=temporal):
                with self.assertRaises(ValueError):
                    _extraer_tesseract(archivo)
            self.assertFalse((Path(temporal) / "archivo-fuera.txt").exists())

    def test_reextrae_un_paquete_ocr_incompleto(self) -> None:
        with tempfile.TemporaryDirectory() as temporal:
            archivo = Path(temporal) / "ocr.zip"
            with zipfile.ZipFile(archivo, "w") as comprimido:
                comprimido.writestr("tesseract.exe", "ejecutable")
                comprimido.writestr("tessdata/eng.traineddata", "inglés")
                comprimido.writestr("tessdata/spa.traineddata", "español")
            destino = Path(temporal) / "LingoLens" / "tesseract"
            destino.mkdir(parents=True)
            (destino / "tesseract.exe").write_text("incompleto", encoding="utf-8")
            with patch("aplicacion.pantalla.tempfile.gettempdir", return_value=temporal):
                ejecutable, datos = _extraer_tesseract(archivo)
            self.assertEqual(ejecutable, destino / "tesseract.exe")
            self.assertEqual(datos, destino / "tessdata")
            self.assertTrue((datos / "eng.traineddata").is_file())
            self.assertTrue((datos / "spa.traineddata").is_file())


if __name__ == "__main__":
    unittest.main()
