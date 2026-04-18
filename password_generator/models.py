"""Modelos tipados y contratos de configuración de la aplicación."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict

DataSourceMode = Literal["embebido", "archivos"]
GenerationMode = Literal["memorable", "secure", "diceware"]
TextCaseMode = Literal["original", "minusculas", "MAYUSCULAS", "Titulo"]

VALID_DATA_SOURCE_MODES: set[DataSourceMode] = {"embebido", "archivos"}
VALID_GENERATION_MODES: set[GenerationMode] = {"memorable", "secure", "diceware"}
VALID_CASE_MODES: set[TextCaseMode] = {
    "original",
    "minusculas",
    "MAYUSCULAS",
    "Titulo",
}

DEFAULT_ARCHIVOS_REL: dict[str, str] = {
    "santos": "dict/santos.dict",
    "senas": "dict/senas.dict",
    "contrasenyas": "dict/contrasenyas.dict",
}


class RawFormatConfig(TypedDict, total=False):
    """Contrato JSON para la sección `formato`."""

    case: str
    separador: str


class RawClipboardConfig(TypedDict, total=False):
    """Contrato JSON para la sección `clipboard`."""

    auto_copiar: bool
    limpiar_segundos: int


class RawSecurityConfig(TypedDict, total=False):
    """Contrato JSON para la sección `seguridad`."""

    longitud_minima: int
    tokens_distintos_min: int
    separadores_permitidos: list[str]
    palabras_diceware: int


class RawAppConfig(TypedDict, total=False):
    """Contrato JSON para `config.json` completo."""

    modo: str
    modo_generacion: str
    archivos: dict[str, str]
    formato: RawFormatConfig
    evitar_repeticiones: bool
    historial_max: int
    semilla: str | None
    clipboard: RawClipboardConfig
    seguridad: RawSecurityConfig


@dataclass(slots=True)
class FormatConfig:
    """Configuración de formato de salida."""

    case: TextCaseMode = "original"
    separador: str = " "


@dataclass(slots=True)
class ClipboardConfig:
    """Parámetros de copia y limpieza de portapapeles."""

    auto_copiar: bool = False
    limpiar_segundos: int = 30


@dataclass(slots=True)
class SecurityConfig:
    """Políticas mínimas de seguridad y modo diceware."""

    longitud_minima: int = 16
    tokens_distintos_min: int = 3
    separadores_permitidos: tuple[str, ...] = (" ", "-", "_", "|", ".", ":", "/")
    palabras_diceware: int = 6


@dataclass(slots=True)
class AppConfig:
    """Configuración normalizada de la aplicación."""

    modo: DataSourceMode = "embebido"
    modo_generacion: GenerationMode = "memorable"
    archivos: dict[str, str] = field(default_factory=lambda: DEFAULT_ARCHIVOS_REL.copy())
    formato: FormatConfig = field(default_factory=FormatConfig)
    evitar_repeticiones: bool = False
    historial_max: int = 50
    semilla: str | None = None
    clipboard: ClipboardConfig = field(default_factory=ClipboardConfig)
    seguridad: SecurityConfig = field(default_factory=SecurityConfig)

    def to_dict(self) -> RawAppConfig:
        """Serializa la configuración a un diccionario JSON-safe."""
        return {
            "modo": self.modo,
            "modo_generacion": self.modo_generacion,
            "archivos": self.archivos.copy(),
            "formato": {
                "case": self.formato.case,
                "separador": self.formato.separador,
            },
            "evitar_repeticiones": self.evitar_repeticiones,
            "historial_max": self.historial_max,
            "semilla": self.semilla,
            "clipboard": {
                "auto_copiar": self.clipboard.auto_copiar,
                "limpiar_segundos": self.clipboard.limpiar_segundos,
            },
            "seguridad": {
                "longitud_minima": self.seguridad.longitud_minima,
                "tokens_distintos_min": self.seguridad.tokens_distintos_min,
                "separadores_permitidos": list(self.seguridad.separadores_permitidos),
                "palabras_diceware": self.seguridad.palabras_diceware,
            },
        }


@dataclass(slots=True)
class WordPools:
    """Colección de listas fuente para generación."""

    santos: list[str]
    senas: list[str]
    contrasenyas: list[str]


@dataclass(slots=True)
class GeneratedSecret:
    """Resultado de una generación de contraseña memorable."""

    value: str
    tokens: tuple[str, ...]
    mode: GenerationMode
    entropy_bits: float

