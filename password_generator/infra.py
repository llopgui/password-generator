"""Capa de infraestructura: configuración JSON y lectura de diccionarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .defaults import DEFAULT_CONTRASENYAS, DEFAULT_SANTOS, DEFAULT_SENYAS
from .models import (
    AppConfig,
    ClipboardConfig,
    DataSourceMode,
    FormatConfig,
    GenerationMode,
    RawAppConfig,
    SecurityConfig,
    TextCaseMode,
    VALID_CASE_MODES,
    VALID_DATA_SOURCE_MODES,
    VALID_GENERATION_MODES,
    WordPools,
)


class ConfigRepository:
    """Gestiona carga, normalización y persistencia de `config.json`."""

    def __init__(self, config_path: Path) -> None:
        """Inicializa el repositorio con ruta explícita de configuración."""
        self.config_path = config_path
        self.base_dir = config_path.parent.resolve()

    def load(self) -> tuple[AppConfig, str | None]:
        """Carga la configuración desde disco y la normaliza.

        Returns:
            Tupla `(config, error)`, donde `error` contiene el motivo si hubo
            fallo al leer JSON o I/O y se aplicaron defaults.
        """
        raw_data: Any = {}
        read_error: str | None = None
        if self.config_path.exists():
            try:
                with self.config_path.open("r", encoding="utf-8") as file:
                    raw_data = json.load(file)
            except (json.JSONDecodeError, OSError) as exc:
                raw_data = {}
                read_error = str(exc)

        if not isinstance(raw_data, dict):
            raw_data = {}

        config = self._normalize_raw_config(raw_data)
        return config, read_error

    def save(self, config: AppConfig) -> None:
        """Guarda la configuración normalizada en formato JSON legible."""
        with self.config_path.open("w", encoding="utf-8") as file:
            json.dump(config.to_dict(), file, indent=4, ensure_ascii=False)

    def resolve_path(self, raw_path: str) -> Path:
        """Resuelve rutas relativas en base al directorio del proyecto.

        Este método corrige de forma definitiva el bug de `_BASE_DIR`
        inexistente, usando siempre `self.base_dir`.
        """
        path = Path(raw_path)
        if not path.is_absolute():
            return (self.base_dir / path).resolve()
        return path

    def _normalize_raw_config(self, raw: RawAppConfig) -> AppConfig:
        """Convierte un diccionario libre en `AppConfig` tipada."""
        mode = _normalize_data_source_mode(raw.get("modo"))
        generation_mode = _normalize_generation_mode(raw.get("modo_generacion"))

        archivos_raw = raw.get("archivos")
        archivos = _normalize_files_config(archivos_raw)
        archivos = {
            key: self._normalize_dictionary_path(value, fallback=value)
            for key, value in archivos.items()
        }

        format_raw = raw.get("formato")
        format_config = _normalize_format_config(format_raw)

        avoid_repetition = bool(raw.get("evitar_repeticiones", False))
        history_max = _normalize_positive_int(raw.get("historial_max"), fallback=50)
        seed = _normalize_seed(raw.get("semilla"))
        clipboard_config = _normalize_clipboard_config(raw.get("clipboard"))
        security_config = _normalize_security_config(raw.get("seguridad"))

        return AppConfig(
            modo=mode,
            modo_generacion=generation_mode,
            archivos=archivos,
            formato=format_config,
            evitar_repeticiones=avoid_repetition,
            historial_max=history_max,
            semilla=seed,
            clipboard=clipboard_config,
            seguridad=security_config,
        )

    def _normalize_dictionary_path(self, raw_path: Any, fallback: str) -> str:
        """Sanea una ruta de diccionario y evita rutas temporales `_MEI`."""
        if not isinstance(raw_path, str) or not raw_path.strip():
            return fallback

        clean_path = raw_path.strip()
        candidate = Path(clean_path)
        if not candidate.is_absolute():
            return clean_path

        parts = [part.lower() for part in candidate.parts]
        if any(part.startswith("_mei") for part in parts):
            return fallback
        return clean_path


class DictionaryRepository:
    """Acceso a listas de palabras desde archivos o datos embebidos."""

    def __init__(self, config_repository: ConfigRepository) -> None:
        """Recibe el repositorio de config para reutilizar resolución de rutas."""
        self.config_repository = config_repository

    def read_words(self, file_path: str) -> list[str]:
        """Lee un archivo `.dict` y devuelve líneas no vacías."""
        resolved_path = self.config_repository.resolve_path(file_path)
        with resolved_path.open("r", encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip()]

    def load_pools(self, config: AppConfig) -> tuple[WordPools, list[str]]:
        """Carga pools según el origen elegido y acumula errores legibles."""
        if config.modo == "embebido":
            return (
                WordPools(
                    santos=DEFAULT_SANTOS.copy(),
                    senas=DEFAULT_SENYAS.copy(),
                    contrasenyas=DEFAULT_CONTRASENYAS.copy(),
                ),
                [],
            )

        errors: list[str] = []
        santos = self._safe_read("santos", config.archivos.get("santos", ""), errors)
        senas = self._safe_read("senas", config.archivos.get("senas", ""), errors)
        contrasenyas = self._safe_read(
            "contrasenyas",
            config.archivos.get("contrasenyas", ""),
            errors,
        )
        return WordPools(santos=santos, senas=senas, contrasenyas=contrasenyas), errors

    def _safe_read(self, key: str, file_path: str, errors: list[str]) -> list[str]:
        """Lee un archivo de forma segura y registra errores en vez de fallar."""
        if not file_path:
            errors.append(f"No se configuró ruta para {key}.")
            return []
        try:
            values = self.read_words(file_path)
            if not values:
                errors.append(f"El archivo de {key} está vacío: {file_path}")
            return values
        except FileNotFoundError:
            errors.append(f"No se encontró el archivo de {key}: {file_path}")
            return []
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"No se pudo leer {key} ({file_path}): {exc}")
            return []


def _normalize_data_source_mode(value: Any) -> DataSourceMode:
    """Normaliza el modo de origen de datos a un valor soportado."""
    as_text = str(value or "embebido")
    if as_text in VALID_DATA_SOURCE_MODES:
        return as_text
    return "embebido"


def _normalize_generation_mode(value: Any) -> GenerationMode:
    """Normaliza el modo de generación a uno permitido."""
    as_text = str(value or "memorable")
    if as_text in VALID_GENERATION_MODES:
        return as_text
    return "memorable"


def _normalize_case_mode(value: Any) -> TextCaseMode:
    """Normaliza el tipo de capitalización para la salida."""
    as_text = str(value or "original")
    if as_text in VALID_CASE_MODES:
        return as_text
    return "original"


def _normalize_files_config(raw: Any) -> dict[str, str]:
    """Asegura que existan rutas para las tres listas principales."""
    defaults = {
        "santos": "dict/santos.dict",
        "senas": "dict/senas.dict",
        "contrasenyas": "dict/contrasenyas.dict",
    }
    if not isinstance(raw, dict):
        return defaults
    normalized: dict[str, str] = {}
    for key, fallback in defaults.items():
        value = raw.get(key, fallback)
        normalized[key] = value if isinstance(value, str) and value.strip() else fallback
    return normalized


def _normalize_format_config(raw: Any) -> FormatConfig:
    """Construye `FormatConfig` segura a partir de datos sin tipar."""
    if not isinstance(raw, dict):
        raw = {}
    case_mode = _normalize_case_mode(raw.get("case"))
    separator = raw.get("separador", " ")
    if not isinstance(separator, str):
        separator = " "
    return FormatConfig(case=case_mode, separador=separator)


def _normalize_clipboard_config(raw: Any) -> ClipboardConfig:
    """Sanea la configuración de copiado y limpieza de portapapeles."""
    if not isinstance(raw, dict):
        raw = {}
    auto_copy = bool(raw.get("auto_copiar", False))
    clear_seconds = _normalize_positive_int(raw.get("limpiar_segundos"), fallback=30)
    return ClipboardConfig(auto_copiar=auto_copy, limpiar_segundos=clear_seconds)


def _normalize_security_config(raw: Any) -> SecurityConfig:
    """Sanea la política de seguridad configurable por usuario."""
    if not isinstance(raw, dict):
        raw = {}
    min_length = _normalize_positive_int(raw.get("longitud_minima"), fallback=16)
    min_distinct = _normalize_positive_int(raw.get("tokens_distintos_min"), fallback=3)
    diceware_words = _normalize_positive_int(raw.get("palabras_diceware"), fallback=6)
    raw_allowed = raw.get("separadores_permitidos", [" ", "-", "_", "|", ".", ":", "/"])
    allowed: list[str] = []
    if isinstance(raw_allowed, list):
        for item in raw_allowed:
            if isinstance(item, str) and item:
                allowed.append(item)
    if not allowed:
        allowed = [" ", "-", "_", "|", ".", ":", "/"]
    return SecurityConfig(
        longitud_minima=min_length,
        tokens_distintos_min=min_distinct,
        separadores_permitidos=tuple(allowed),
        palabras_diceware=diceware_words,
    )


def _normalize_positive_int(value: Any, *, fallback: int) -> int:
    """Devuelve un entero positivo o un fallback seguro."""
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(1, normalized)


def _normalize_seed(value: Any) -> str | None:
    """Normaliza la semilla de PRNG para modo memorable."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None

