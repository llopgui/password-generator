"""Pruebas del motor de generación y control de repeticiones."""

from __future__ import annotations

from password_generator.core import ExhaustedCombinationsError, GenerationEngine
from password_generator.models import WordPools


def test_generate_without_repetition_exhausts_space() -> None:
    """Debe evitar duplicados y fallar al agotar el espacio combinatorio."""
    engine = GenerationEngine(seed="seed")
    pools = WordPools(
        santos=["S1"],
        senas=["E1"],
        contrasenyas=["C1", "C2"],
    )

    first = engine.generate(
        pools=pools,
        mode="memorable",
        case_mode="original",
        separator=" ",
        avoid_repetition=True,
        diceware_words=6,
    )
    second = engine.generate(
        pools=pools,
        mode="memorable",
        case_mode="original",
        separator=" ",
        avoid_repetition=True,
        diceware_words=6,
    )

    assert first.value != second.value

    try:
        engine.generate(
            pools=pools,
            mode="memorable",
            case_mode="original",
            separator=" ",
            avoid_repetition=True,
            diceware_words=6,
        )
    except ExhaustedCombinationsError:
        assert True
    else:
        assert False, "Se esperaba ExhaustedCombinationsError al agotar el espacio."


def test_secure_and_diceware_modes_generate_entropy() -> None:
    """Verifica que modos modernos generen salida y entropía positiva."""
    engine = GenerationEngine()
    pools = WordPools(
        santos=["SanA", "SanB"],
        senas=["ClaveA", "ClaveB"],
        contrasenyas=["ValorA", "ValorB"],
    )

    secure = engine.generate(
        pools=pools,
        mode="secure",
        case_mode="original",
        separator="-",
        avoid_repetition=False,
        diceware_words=6,
    )
    diceware = engine.generate(
        pools=pools,
        mode="diceware",
        case_mode="minusculas",
        separator="_",
        avoid_repetition=False,
        diceware_words=4,
    )

    assert secure.entropy_bits > 0
    assert diceware.entropy_bits > 0
    assert "-" in secure.value
    assert "_" in diceware.value
    assert len(diceware.tokens) == 4

