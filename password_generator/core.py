"""Motor de generación y formateo de contraseñas memorables."""

from __future__ import annotations

import random
import secrets
from itertools import product
from typing import Sequence

from .models import GeneratedSecret, GenerationMode, TextCaseMode, WordPools
from .security import estimate_entropy_bits


class ExhaustedCombinationsError(RuntimeError):
    """Error levantado cuando no quedan combinaciones únicas disponibles."""


class GenerationEngine:
    """Gestiona generación en modos memorable, secure y diceware."""

    def __init__(self, seed: str | None = None) -> None:
        """Inicializa los generadores y cache de combinaciones usadas."""
        self._seed: str | None = seed
        self._memorable_rng = random.Random(seed) if seed is not None else random.Random()
        self._secure_rng = secrets.SystemRandom()
        self._used_by_mode: dict[GenerationMode, set[tuple[str, ...]]] = {
            "memorable": set(),
            "secure": set(),
            "diceware": set(),
        }

    @property
    def seed(self) -> str | None:
        """Devuelve la semilla activa del modo memorable."""
        return self._seed

    def set_seed(self, seed: str | None) -> None:
        """Actualiza la semilla del modo memorable y reinicia el estado usado."""
        self._seed = seed
        self._memorable_rng = random.Random(seed) if seed is not None else random.Random()
        self.reset_used()

    def reset_used(self) -> None:
        """Vacía todas las combinaciones registradas como usadas."""
        for used_set in self._used_by_mode.values():
            used_set.clear()

    def snapshot_used(self) -> dict[GenerationMode, set[tuple[str, ...]]]:
        """Crea una copia profunda del estado interno de repeticiones."""
        return {mode: set(values) for mode, values in self._used_by_mode.items()}

    def restore_used(self, snapshot: dict[GenerationMode, set[tuple[str, ...]]]) -> None:
        """Restaura el estado de combinaciones usadas desde un snapshot."""
        self._used_by_mode = {mode: set(values) for mode, values in snapshot.items()}

    def generate(
        self,
        *,
        pools: WordPools,
        mode: GenerationMode,
        case_mode: TextCaseMode,
        separator: str,
        avoid_repetition: bool,
        diceware_words: int,
    ) -> GeneratedSecret:
        """Genera una contraseña usando el modo indicado."""
        if mode == "diceware":
            tokens = self._generate_diceware_tokens(
                pools=pools,
                avoid_repetition=avoid_repetition,
                words=max(4, diceware_words),
            )
            value = _format_tokens(tokens=tokens, case_mode=case_mode, separator=separator)
            merged_pool = len(set(pools.santos + pools.senas + pools.contrasenyas))
            entropy_bits = estimate_entropy_bits(merged_pool, len(tokens))
            return GeneratedSecret(
                value=value,
                tokens=tokens,
                mode=mode,
                entropy_bits=entropy_bits,
            )

        tokens = self._generate_three_tokens(
            pools=pools,
            mode=mode,
            avoid_repetition=avoid_repetition,
        )
        value = _format_tokens(tokens=tokens, case_mode=case_mode, separator=separator)
        entropy_bits = estimate_entropy_bits(len(pools.santos), 1)
        entropy_bits += estimate_entropy_bits(len(pools.senas), 1)
        entropy_bits += estimate_entropy_bits(len(pools.contrasenyas), 1)
        return GeneratedSecret(
            value=value,
            tokens=tokens,
            mode=mode,
            entropy_bits=entropy_bits,
        )

    def _generate_three_tokens(
        self,
        *,
        pools: WordPools,
        mode: GenerationMode,
        avoid_repetition: bool,
    ) -> tuple[str, ...]:
        """Genera `(santo, seña, contraseña)` usando un RNG por modo."""
        used = self._used_by_mode[mode]
        space = len(pools.santos) * len(pools.senas) * len(pools.contrasenyas)
        if space <= 0:
            raise ValueError("No hay datos suficientes para generar combinaciones.")

        if avoid_repetition and len(used) >= space:
            raise ExhaustedCombinationsError("Se agotaron las combinaciones únicas.")

        rng = self._select_rng(mode)
        attempts = min(20000, max(1000, space * 2))
        for _ in range(attempts):
            tokens = (
                rng.choice(pools.santos),
                rng.choice(pools.senas),
                rng.choice(pools.contrasenyas),
            )
            if not avoid_repetition or tokens not in used:
                if avoid_repetition:
                    used.add(tokens)
                return tokens

        # Fallback determinista: evita bloqueo cuando el espacio restante es pequeño.
        for santo, sena, contrasenya in product(
            pools.santos,
            pools.senas,
            pools.contrasenyas,
        ):
            tokens = (santo, sena, contrasenya)
            if not avoid_repetition or tokens not in used:
                if avoid_repetition:
                    used.add(tokens)
                return tokens

        raise ExhaustedCombinationsError("No se pudo obtener una combinación libre.")

    def _generate_diceware_tokens(
        self,
        *,
        pools: WordPools,
        avoid_repetition: bool,
        words: int,
    ) -> tuple[str, ...]:
        """Genera secuencias estilo diceware desde el pool combinado."""
        merged_pool = list(dict.fromkeys(pools.santos + pools.senas + pools.contrasenyas))
        if len(merged_pool) < 4:
            raise ValueError("No hay suficientes palabras para modo diceware.")

        used = self._used_by_mode["diceware"]
        rng = self._secure_rng
        attempts = 25000
        for _ in range(attempts):
            tokens = tuple(rng.choice(merged_pool) for _ in range(words))
            if not avoid_repetition or tokens not in used:
                if avoid_repetition:
                    used.add(tokens)
                return tokens

        raise ExhaustedCombinationsError(
            "No se pudo generar una combinación diceware sin repetir."
        )

    def _select_rng(self, mode: GenerationMode) -> random.Random | secrets.SystemRandom:
        """Elige el generador pseudoaleatorio según el modo."""
        if mode == "secure":
            return self._secure_rng
        return self._memorable_rng


def _normalize_case(value: str, case_mode: TextCaseMode) -> str:
    """Aplica la transformación de mayúsculas/minúsculas solicitada."""
    if case_mode == "minusculas":
        return value.lower()
    if case_mode == "MAYUSCULAS":
        return value.upper()
    if case_mode == "Titulo":
        return value.title()
    return value


def _format_tokens(
    *,
    tokens: Sequence[str],
    case_mode: TextCaseMode,
    separator: str,
) -> str:
    """Une tokens usando formato configurable de case y separador."""
    normalized = [_normalize_case(token, case_mode) for token in tokens]
    return separator.join(normalized)

