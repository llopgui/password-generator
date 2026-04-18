"""Pruebas de infraestructura: config y lectura de diccionarios."""

from __future__ import annotations

import json
from pathlib import Path

from password_generator.infra import ConfigRepository, DictionaryRepository


def test_load_normalizes_invalid_config_values(tmp_path: Path) -> None:
    """Valida defaults seguros cuando `config.json` trae datos inválidos."""
    config_path = tmp_path / "config.json"
    raw_config = {
        "modo": "desconocido",
        "modo_generacion": "otro",
        "archivos": {"santos": "", "senas": 1, "contrasenyas": None},
        "formato": {"case": "x", "separador": 123},
        "evitar_repeticiones": "si",
        "historial_max": "0",
        "semilla": "",
        "clipboard": {"auto_copiar": "ok", "limpiar_segundos": "0"},
        "seguridad": {
            "longitud_minima": "4",
            "tokens_distintos_min": "0",
            "separadores_permitidos": [1, "", "-"],
            "palabras_diceware": "0",
        },
    }
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    repository = ConfigRepository(config_path)
    config, read_error = repository.load()

    assert read_error is None
    assert config.modo == "embebido"
    assert config.modo_generacion == "memorable"
    assert config.archivos["santos"] == "dict/santos.dict"
    assert config.formato.case == "original"
    assert config.formato.separador == " "
    assert config.evitar_repeticiones is True
    assert config.historial_max == 1
    assert config.semilla is None
    assert config.clipboard.auto_copiar is True
    assert config.clipboard.limpiar_segundos == 1
    assert config.seguridad.longitud_minima == 4
    assert config.seguridad.tokens_distintos_min == 1
    assert config.seguridad.separadores_permitidos == ("-",)
    assert config.seguridad.palabras_diceware == 1


def test_resolve_relative_and_absolute_paths(tmp_path: Path) -> None:
    """Confirma resolución correcta de rutas sin depender de `_BASE_DIR`."""
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    repository = ConfigRepository(config_path)

    relative = repository.resolve_path("dict/santos.dict")
    absolute = repository.resolve_path(str(tmp_path / "x.dict"))

    assert relative == (tmp_path / "dict" / "santos.dict").resolve()
    assert absolute == (tmp_path / "x.dict").resolve()


def test_dictionary_repository_reads_relative_and_absolute(tmp_path: Path) -> None:
    """Comprueba lectura de diccionarios tanto relativa como absoluta."""
    dict_dir = tmp_path / "dict"
    dict_dir.mkdir()
    words_path = dict_dir / "santos.dict"
    words_path.write_text("Uno\n\nDos\n Tres \n", encoding="utf-8")

    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")

    config_repository = ConfigRepository(config_path)
    dictionary_repository = DictionaryRepository(config_repository)

    values_relative = dictionary_repository.read_words("dict/santos.dict")
    values_absolute = dictionary_repository.read_words(str(words_path))

    assert values_relative == ["Uno", "Dos", "Tres"]
    assert values_absolute == ["Uno", "Dos", "Tres"]

