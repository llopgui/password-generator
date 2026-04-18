"""Utilidades de seguridad: entropía, clasificación y políticas mínimas."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

from .models import SecurityConfig

EntropyLabel = Literal["Muy baja", "Baja", "Media", "Alta", "Muy alta"]


@dataclass(slots=True)
class PolicyEvaluation:
    """Resultado de validar una contraseña contra una política."""

    is_valid: bool
    reasons: list[str]


def estimate_entropy_bits(pool_size: int, token_count: int) -> float:
    """Calcula la entropía estimada en bits para selecciones uniformes.

    Args:
        pool_size: Cantidad de opciones disponibles en cada selección.
        token_count: Número de tokens elegidos.

    Returns:
        Entropía estimada en bits. Devuelve 0.0 para entradas inválidas.
    """
    if pool_size <= 0 or token_count <= 0:
        return 0.0
    return token_count * math.log2(pool_size)


def classify_entropy(entropy_bits: float) -> EntropyLabel:
    """Convierte una entropía numérica en un nivel legible."""
    if entropy_bits < 35:
        return "Muy baja"
    if entropy_bits < 50:
        return "Baja"
    if entropy_bits < 65:
        return "Media"
    if entropy_bits < 80:
        return "Alta"
    return "Muy alta"


def validate_password_policy(
    *,
    password: str,
    tokens: Sequence[str],
    separator: str,
    policy: SecurityConfig,
) -> PolicyEvaluation:
    """Evalúa si una contraseña cumple política mínima configurada.

    La validación se aplica especialmente al modo de exportación por lote,
    donde interesa evitar salidas triviales por configuración débil.
    """
    reasons: list[str] = []
    stripped_tokens = [token.strip() for token in tokens if token.strip()]
    distinct_tokens = len(set(stripped_tokens))

    if len(password) < policy.longitud_minima:
        reasons.append(
            f"La longitud ({len(password)}) es menor que la mínima ({policy.longitud_minima})."
        )

    if distinct_tokens < policy.tokens_distintos_min:
        reasons.append(
            "La combinación no alcanza el mínimo de tokens distintos "
            f"({policy.tokens_distintos_min})."
        )

    if separator not in policy.separadores_permitidos:
        reasons.append(
            "El separador configurado no está dentro de la lista permitida."
        )

    return PolicyEvaluation(is_valid=not reasons, reasons=reasons)

