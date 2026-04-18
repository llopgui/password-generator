"""Pruebas para utilidades de entropía y políticas de seguridad."""

from __future__ import annotations

from password_generator.models import SecurityConfig
from password_generator.security import (
    classify_entropy,
    estimate_entropy_bits,
    validate_password_policy,
)


def test_entropy_helpers_classify_ranges() -> None:
    """Comprueba cálculo de entropía y su clasificación legible."""
    entropy = estimate_entropy_bits(20, 3)
    label = classify_entropy(entropy)

    assert entropy > 0
    assert label in {"Muy baja", "Baja", "Media", "Alta", "Muy alta"}


def test_policy_validator_reports_invalid_password() -> None:
    """Debe reportar incumplimientos cuando la contraseña es débil."""
    policy = SecurityConfig(
        longitud_minima=20,
        tokens_distintos_min=3,
        separadores_permitidos=("-",),
        palabras_diceware=6,
    )

    evaluation = validate_password_policy(
        password="a-a-a",
        tokens=("a", "a", "a"),
        separator="_",
        policy=policy,
    )

    assert evaluation.is_valid is False
    assert len(evaluation.reasons) >= 2

