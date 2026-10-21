"""Punto de entrada de LingoLens."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from aplicacion.interfaz.ventana import VentanaPrincipal


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LingoLens")
    app.setOrganizationName("LingoLens")
    try:
        ventana = VentanaPrincipal()
    except Exception as error:
        QMessageBox.critical(
            None,
            "No se pudo iniciar LingoLens",
            f"{error}\n\nRevisa la guía de solución de problemas.",
        )
        return 1
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
