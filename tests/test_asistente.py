import json
import unittest
from unittest.mock import Mock, patch

from aplicacion.ia.asistente import (
    MODELOS_RECOMENDADOS,
    AsistenteLocal,
    nombre_modelo_valido,
)


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

    def test_catalogo_tiene_modelos_unicos_y_nombres_seguros(self) -> None:
        nombres = [modelo.nombre for modelo in MODELOS_RECOMENDADOS]
        self.assertEqual(len(nombres), len(set(nombres)))
        self.assertTrue(nombre_modelo_valido("qwen2.5:1.5b"))
        self.assertTrue(nombre_modelo_valido("org/modelo:latest"))
        self.assertFalse(nombre_modelo_valido("qwen; rm -rf /"))
        self.assertFalse(nombre_modelo_valido("modelo con espacios"))

    def test_descarga_rechaza_nombre_no_valido_antes_de_iniciar_ollama(self) -> None:
        asistente = AsistenteLocal()
        with patch("aplicacion.ia.asistente.buscar_ollama") as buscar:
            with self.assertRaises(ValueError):
                asistente.instalar_modelo("qwen; comando-no-deseado")
        buscar.assert_not_called()

    def test_descarga_usa_ollama_pull_sin_shell(self) -> None:
        class ProcesoFalso:
            args = ["ollama", "pull", "qwen3:8b"]
            stdout = iter(("pulling manifest\n",))

            def wait(self, timeout: float) -> int:
                return 0

        proceso = ProcesoFalso()
        progreso: list[str] = []
        with (
            patch("aplicacion.ia.asistente.buscar_ollama", return_value="ollama.exe"),
            patch.object(AsistenteLocal, "iniciar_servidor", return_value=True),
            patch("aplicacion.ia.asistente.subprocess.Popen", return_value=proceso) as popen,
        ):
            AsistenteLocal().instalar_modelo("qwen3:8b", progreso=progreso.append)

        self.assertEqual(popen.call_args.args[0], ["ollama.exe", "pull", "qwen3:8b"])
        self.assertFalse(popen.call_args.kwargs.get("shell", False))
        self.assertEqual(progreso, ["pulling manifest"])


if __name__ == "__main__":
    unittest.main()
