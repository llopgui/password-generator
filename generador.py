"""Punto de entrada legado para mantener compatibilidad con scripts existentes."""

from password_generator.ui import run_app


if __name__ == "__main__":
    # Wrapper mínimo para conservar `python generador.py`.
    run_app()

