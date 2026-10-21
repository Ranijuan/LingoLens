import json
import unittest
from unittest.mock import Mock, patch

from aplicacion.ia.asistente import AsistenteLocal


class AsistenteTests(unittest.TestCase):
    def test_traduccion_interpreta_json_del_modelo(self) -> None:
        respuesta = Mock()
        respuesta.json.return_value = {
            "message": {
                "content": json.dumps(
                    {"translation": "I have a book.", "explanation": "Usa have con I."}
                )
            }
        }
        with patch("aplicacion.ia.asistente.requests.post", return_value=respuesta) as post:
            resultado = AsistenteLocal().traducir_y_ensenar(
                "I has a book.", "inglés", "A2", "español"
            )

        respuesta.raise_for_status.assert_called_once_with()
        self.assertEqual(resultado["translation"], "I have a book.")
        self.assertEqual(resultado["explanation"], "Usa have con I.")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["format"], "json")
        self.assertIn("I has a book.", payload["messages"][1]["content"])

    def test_rechaza_texto_vacio_e_idioma_no_permitido(self) -> None:
        asistente = AsistenteLocal()
        with self.assertRaises(ValueError):
            asistente.traducir_y_ensenar("   ", "inglés", "A2")
        with self.assertRaises(ValueError):
            asistente.traducir_y_ensenar("Hello", "inglés", "A2", "francés")

    def test_conversacion_exige_un_mensaje_del_usuario(self) -> None:
        with self.assertRaises(ValueError):
            AsistenteLocal().conversar(
                [{"role": "assistant", "content": "Hola"}], "A2", []
            )


if __name__ == "__main__":
    unittest.main()
