"""Interfaz Tkinter para el Password Generator modernizado."""

from __future__ import annotations

import sys
import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Final, cast

from .clipboard import ClipboardManager, show_copy_feedback
from .core import ExhaustedCombinationsError, GenerationEngine
from .infra import ConfigRepository, DictionaryRepository
from .models import (
    AppConfig,
    DataSourceMode,
    GenerationMode,
    TextCaseMode,
    VALID_GENERATION_MODES,
)
from .security import classify_entropy, validate_password_policy

CASE_LABEL_TO_VALUE: Final[dict[str, TextCaseMode]] = {
    "Original": "original",
    "Minúsculas": "minusculas",
    "MAYÚSCULAS": "MAYUSCULAS",
    "Título": "Titulo",
}
CASE_VALUE_TO_LABEL: Final[dict[TextCaseMode, str]] = {
    "original": "Original",
    "minusculas": "Minúsculas",
    "MAYUSCULAS": "MAYÚSCULAS",
    "Titulo": "Título",
}
SEPARATOR_LABEL_TO_VALUE: Final[dict[str, str]] = {
    "Espacio": " ",
    "Guion (-)": "-",
    "Guion bajo (_)": "_",
    "Barra vertical (|)": "|",
    "Punto (.)": ".",
    "Slash (/)": "/",
}
GENERATION_MODE_CHOICES: Final[tuple[tuple[GenerationMode, str], ...]] = (
    ("memorable", "Memorable (PRNG)"),
    ("secure", "Secure (SystemRandom)"),
    ("diceware", "Diceware"),
)
DATA_SOURCE_CHOICES: Final[tuple[tuple[DataSourceMode, str], ...]] = (
    ("embebido", "Listas embebidas"),
    ("archivos", "Archivos (*.dict)"),
)
WINDOW_WIDTH: Final[int] = 960
WINDOW_HEIGHT: Final[int] = 720
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"


class PasswordGeneratorApp:
    """Controlador de la aplicación de escritorio."""

    def __init__(self, master: tk.Tk) -> None:
        """Inicializa servicios, estado y widgets principales."""
        self.master = master
        self.master.title("Password Generator")
        self.master.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        # Ventana fija para mantener una experiencia visual consistente.
        self.master.resizable(False, False)
        # Tamaño fijo validado visualmente para evitar recorte inferior.
        self.master.minsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.master.maxsize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._window_icon_image: tk.PhotoImage | None = None
        self._set_window_icon()

        self._config_repository = ConfigRepository(PROJECT_ROOT / "config.json")
        self._dictionary_repository = DictionaryRepository(self._config_repository)
        self.config, self._config_read_error = self._config_repository.load()

        self._engine = GenerationEngine(seed=self.config.semilla)
        self._clipboard = ClipboardManager(master)
        self.historial: deque[str] = deque(maxlen=self.config.historial_max)
        self._last_generated_value = ""

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        self.data_source_var = tk.StringVar(value=self.config.modo)
        self.case_var = tk.StringVar(value=self.config.formato.case)
        self.separator_var = tk.StringVar(value=self.config.formato.separador)
        self.avoid_repetition_var = tk.BooleanVar(value=self.config.evitar_repeticiones)
        self.generation_mode_var = tk.StringVar(value=self.config.modo_generacion)
        self.auto_copy_var = tk.BooleanVar(value=self.config.clipboard.auto_copiar)

        self.case_display_var = tk.StringVar(
            value=self._case_value_to_label(self.case_var.get())
        )
        self.separator_display_var = tk.StringVar(
            value=self._separator_value_to_label(self.separator_var.get())
        )

        self.clipboard_seconds_var = tk.IntVar(
            value=self.config.clipboard.limpiar_segundos
        )
        self.minimum_length_var = tk.IntVar(value=self.config.seguridad.longitud_minima)
        self.minimum_tokens_var = tk.IntVar(
            value=self.config.seguridad.tokens_distintos_min
        )
        self.diceware_words_var = tk.IntVar(value=self.config.seguridad.palabras_diceware)

        self.entropy_var = tk.StringVar(value="Entropía estimada: --")
        self.seed_warning_var = tk.StringVar(value="")
        self._default_status_message = "Listo. Pulsa Generar combinación para empezar."
        self.status_var = tk.StringVar(value=self._default_status_message)
        self._persistent_status = self._default_status_message
        self._status_after_id: str | None = None
        self._button_restore_jobs: dict[int, str] = {}
        self._button_original_labels: dict[int, str] = {}
        self.last_result_var = tk.StringVar(
            value="Aún no hay una contraseña generada en esta sesión."
        )
        self.mode_chip_var = tk.StringVar()
        self.source_chip_var = tk.StringVar()
        self.clipboard_chip_var = tk.StringVar()
        self.policy_chip_var = tk.StringVar()

        self._build_layout()
        self._build_menu()
        self._register_shortcuts()
        self._bind_microinteractions()
        self._refresh_seed_warning()
        self._refresh_overview_chips()
        self.master.after(100, self._show_config_error_if_needed)

    def _set_window_icon(self) -> None:
        """Configura el icono de la ventana con fallback multiplataforma.

        Prioridad:
        1) `assets/icon.ico` (y alias) en Windows.
        2) `assets/icon.png` / `assets/banner.png` con `iconphoto`.
        3) Compatibilidad retro: busca en raíz del proyecto si faltan assets.
        """
        search_roots = (ASSETS_DIR, PROJECT_ROOT)

        # En Windows, un `.ico` suele integrarse mejor en barra de título y taskbar.
        if sys.platform.startswith("win"):
            ico_candidates = ("icon.ico", "app.ico", "favicon.ico")
            for root in search_roots:
                for file_name in ico_candidates:
                    candidate = root / file_name
                    if not candidate.exists():
                        continue
                    try:
                        self.master.iconbitmap(default=str(candidate))
                        return
                    except tk.TclError:
                        # Si el recurso es inválido, intentamos el siguiente candidato.
                        continue

        # Fallback universal con PNG.
        png_candidates = ("icon.png", "banner.png")
        for root in search_roots:
            for file_name in png_candidates:
                candidate = root / file_name
                if not candidate.exists():
                    continue
                try:
                    self._window_icon_image = tk.PhotoImage(file=str(candidate))
                    self.master.iconphoto(True, self._window_icon_image)
                    return
                except tk.TclError:
                    # Si falla la carga, continuamos con el siguiente recurso.
                    continue

    def _configure_styles(self) -> None:
        """Configura estilos visuales para una UI más moderna."""
        self.master.configure(background="#0b1220")
        self.style.configure("App.TFrame", background="#0b1220")
        self.style.configure("Card.TFrame", background="#111827")
        self.style.configure(
            "Title.TLabel",
            background="#0b1220",
            foreground="#e2e8f0",
            font=("Segoe UI", 22, "bold"),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background="#0b1220",
            foreground="#94a3b8",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "CardText.TLabel",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Muted.TLabel",
            background="#111827",
            foreground="#9ca3af",
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Warning.TLabel",
            background="#111827",
            foreground="#f59e0b",
            font=("Segoe UI", 9, "bold"),
        )
        self.style.configure(
            "Chip.TLabel",
            background="#1e293b",
            foreground="#93c5fd",
            font=("Segoe UI", 9, "bold"),
            padding=(8, 5),
        )
        self.style.configure(
            "Status.TLabel",
            background="#0b1220",
            foreground="#cbd5e1",
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(14, 9),
            foreground="#f8fafc",
            background="#2563eb",
        )
        self.style.map(
            "Primary.TButton",
            background=[
                ("disabled", "#1f2937"),
                ("pressed", "#1d4ed8"),
                ("active", "#3b82f6"),
            ],
            foreground=[("disabled", "#94a3b8"), ("active", "#ffffff")],
        )
        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", 10),
            padding=(12, 8),
            foreground="#e2e8f0",
            background="#1e293b",
        )
        self.style.map(
            "Secondary.TButton",
            background=[
                ("disabled", "#111827"),
                ("pressed", "#334155"),
                ("active", "#475569"),
            ],
            foreground=[("disabled", "#64748b"), ("active", "#f8fafc")],
        )
        self.style.configure(
            "Card.TLabelframe",
            background="#111827",
            foreground="#e2e8f0",
            borderwidth=1,
            relief="solid",
            padding=12,
        )
        self.style.configure(
            "Card.TLabelframe.Label",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 10, "bold"),
        )
        self.style.configure(
            "Modern.TCheckbutton",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "Toggle.TRadiobutton",
            background="#111827",
            foreground="#e2e8f0",
            font=("Segoe UI", 10),
        )

    def _build_layout(self) -> None:
        """Construye el layout principal con jerarquía visual moderna."""
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        container = ttk.Frame(self.master, style="App.TFrame", padding=(24, 20, 24, 18))
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        self._build_header(container)
        self._build_output_card(container)
        self._build_overview_chips(container)
        self._build_quick_controls(container)
        self._build_action_bar(container)
        self._build_status_bar(container)

    def _build_header(self, container: ttk.Frame) -> None:
        """Construye el encabezado con título y texto guía."""
        header = ttk.Frame(container, style="App.TFrame")
        header.grid(row=0, column=0, sticky="we", pady=(0, 14))
        header.grid_columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Password Generator",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "Genera contraseñas memorables, secure o diceware "
                "con controles rápidos de seguridad."
            ),
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_output_card(self, container: ttk.Frame) -> None:
        """Construye la tarjeta central para mostrar el resultado generado."""
        result_card = ttk.LabelFrame(
            container,
            text="Resultado",
            style="Card.TLabelframe",
        )
        result_card.grid(row=1, column=0, sticky="we", pady=(0, 12))
        result_card.grid_columnconfigure(0, weight=1)

        ttk.Label(
            result_card,
            text="Contraseña generada",
            style="CardText.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))

        output_row = ttk.Frame(result_card, style="Card.TFrame")
        output_row.grid(row=1, column=0, sticky="we")
        output_row.grid_columnconfigure(0, weight=1)

        self.combination_entry = ttk.Entry(
            output_row,
            font=("Consolas", 13),
            state="readonly",
            width=72,
        )
        self.combination_entry.grid(row=0, column=0, sticky="we", padx=(0, 8))
        self.copy_output_button = ttk.Button(
            output_row,
            text="Copiar",
            style="Secondary.TButton",
            command=self.copy_current_password,
        )
        self.copy_output_button.grid(row=0, column=1, sticky="e")

        ttk.Label(
            result_card,
            textvariable=self.entropy_var,
            style="CardText.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(8, 2))
        ttk.Label(
            result_card,
            textvariable=self.seed_warning_var,
            style="Warning.TLabel",
        ).grid(row=3, column=0, sticky="w", pady=(0, 2))
        ttk.Label(
            result_card,
            textvariable=self.last_result_var,
            style="Muted.TLabel",
        ).grid(row=4, column=0, sticky="w")

    def _build_overview_chips(self, container: ttk.Frame) -> None:
        """Construye indicadores rápidos del estado de configuración."""
        chips_frame = ttk.Frame(container, style="App.TFrame")
        chips_frame.grid(row=2, column=0, sticky="we", pady=(0, 12))
        chips_frame.grid_columnconfigure(0, weight=1)
        chips_frame.grid_columnconfigure(1, weight=1)
        chips_frame.grid_columnconfigure(2, weight=1)
        chips_frame.grid_columnconfigure(3, weight=1)

        ttk.Label(chips_frame, textvariable=self.mode_chip_var, style="Chip.TLabel").grid(
            row=0, column=0, sticky="we", padx=(0, 6)
        )
        ttk.Label(
            chips_frame,
            textvariable=self.source_chip_var,
            style="Chip.TLabel",
        ).grid(row=0, column=1, sticky="we", padx=6)
        ttk.Label(
            chips_frame,
            textvariable=self.clipboard_chip_var,
            style="Chip.TLabel",
        ).grid(row=0, column=2, sticky="we", padx=6)
        ttk.Label(chips_frame, textvariable=self.policy_chip_var, style="Chip.TLabel").grid(
            row=0, column=3, sticky="we", padx=(6, 0)
        )

    def _build_quick_controls(self, container: ttk.Frame) -> None:
        """Construye controles visibles para editar ajustes sin abrir menús."""
        controls_card = ttk.LabelFrame(
            container,
            text="Controles rápidos",
            style="Card.TLabelframe",
        )
        controls_card.grid(row=3, column=0, sticky="we", pady=(0, 12))
        controls_card.grid_columnconfigure(1, weight=1)
        controls_card.grid_columnconfigure(3, weight=1)

        ttk.Label(
            controls_card,
            text="Modo de generación",
            style="CardText.TLabel",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8), padx=(0, 10))
        generation_frame = ttk.Frame(controls_card, style="Card.TFrame")
        generation_frame.grid(row=0, column=1, columnspan=3, sticky="we", pady=(0, 8))
        for index, (generation_value, generation_label) in enumerate(
            GENERATION_MODE_CHOICES
        ):
            ttk.Radiobutton(
                generation_frame,
                text=generation_label,
                style="Toggle.TRadiobutton",
                variable=self.generation_mode_var,
                value=generation_value,
                command=self._on_change_generation_mode,
            ).grid(row=0, column=index, sticky="w", padx=(0, 12))

        ttk.Label(
            controls_card,
            text="Origen de datos",
            style="CardText.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8), padx=(0, 10))
        source_frame = ttk.Frame(controls_card, style="Card.TFrame")
        source_frame.grid(row=1, column=1, columnspan=3, sticky="we", pady=(0, 8))
        for index, (source_value, source_label) in enumerate(DATA_SOURCE_CHOICES):
            ttk.Radiobutton(
                source_frame,
                text=source_label,
                style="Toggle.TRadiobutton",
                variable=self.data_source_var,
                value=source_value,
                command=self._on_change_data_source,
            ).grid(row=0, column=index, sticky="w", padx=(0, 12))

        ttk.Label(
            controls_card,
            text="Capitalización",
            style="CardText.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(0, 8), padx=(0, 10))
        self.case_combo = ttk.Combobox(
            controls_card,
            textvariable=self.case_display_var,
            values=list(CASE_LABEL_TO_VALUE.keys()),
            state="readonly",
            width=20,
        )
        self.case_combo.grid(row=2, column=1, sticky="we", padx=(0, 10), pady=(0, 8))
        self.case_combo.bind("<<ComboboxSelected>>", self._on_quick_case_selected)

        ttk.Label(
            controls_card,
            text="Separador",
            style="CardText.TLabel",
        ).grid(row=2, column=2, sticky="w", pady=(0, 8), padx=(0, 10))
        self.separator_combo = ttk.Combobox(
            controls_card,
            textvariable=self.separator_display_var,
            values=list(SEPARATOR_LABEL_TO_VALUE.keys()),
            state="readonly",
            width=18,
        )
        self.separator_combo.grid(row=2, column=3, sticky="we", pady=(0, 8))
        self.separator_combo.bind("<<ComboboxSelected>>", self._on_quick_separator_selected)

        ttk.Checkbutton(
            controls_card,
            text="Evitar repeticiones",
            style="Modern.TCheckbutton",
            variable=self.avoid_repetition_var,
            command=self._on_toggle_avoid_repetition,
        ).grid(row=3, column=0, sticky="w", pady=(0, 8))
        ttk.Checkbutton(
            controls_card,
            text="Copiar automáticamente al generar",
            style="Modern.TCheckbutton",
            variable=self.auto_copy_var,
            command=self._on_toggle_auto_copy,
        ).grid(row=3, column=1, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(
            controls_card,
            text="Limpieza portapapeles (s)",
            style="CardText.TLabel",
        ).grid(row=4, column=0, sticky="w", padx=(0, 10))
        self.clipboard_seconds_spinbox = ttk.Spinbox(
            controls_card,
            from_=0,
            to=3600,
            textvariable=self.clipboard_seconds_var,
            width=8,
        )
        self.clipboard_seconds_spinbox.grid(
            row=4,
            column=1,
            sticky="w",
            padx=(0, 10),
        )

        ttk.Label(
            controls_card,
            text="Longitud mínima",
            style="CardText.TLabel",
        ).grid(row=4, column=2, sticky="w", padx=(0, 10))
        self.minimum_length_spinbox = ttk.Spinbox(
            controls_card,
            from_=8,
            to=256,
            textvariable=self.minimum_length_var,
            width=8,
        )
        self.minimum_length_spinbox.grid(row=4, column=3, sticky="w")

        ttk.Label(
            controls_card,
            text="Mínimo tokens distintos",
            style="CardText.TLabel",
        ).grid(row=5, column=0, sticky="w", padx=(0, 10), pady=(8, 0))
        self.minimum_tokens_spinbox = ttk.Spinbox(
            controls_card,
            from_=1,
            to=20,
            textvariable=self.minimum_tokens_var,
            width=8,
        )
        self.minimum_tokens_spinbox.grid(row=5, column=1, sticky="w", pady=(8, 0))

        ttk.Label(
            controls_card,
            text="Palabras diceware",
            style="CardText.TLabel",
        ).grid(row=5, column=2, sticky="w", padx=(0, 10), pady=(8, 0))
        self.diceware_words_spinbox = ttk.Spinbox(
            controls_card,
            from_=4,
            to=12,
            textvariable=self.diceware_words_var,
            width=8,
        )
        self.diceware_words_spinbox.grid(row=5, column=3, sticky="w", pady=(8, 0))

        self.apply_quick_button = ttk.Button(
            controls_card,
            text="Aplicar ajustes rápidos",
            style="Secondary.TButton",
            command=self._apply_quick_security_settings,
        )
        self.apply_quick_button.grid(
            row=6,
            column=0,
            columnspan=4,
            sticky="e",
            pady=(12, 0),
        )

    def _build_action_bar(self, container: ttk.Frame) -> None:
        """Construye botones primarios de uso frecuente."""
        actions = ttk.Frame(container, style="App.TFrame")
        actions.grid(row=4, column=0, sticky="we", pady=(0, 10))
        actions.grid_columnconfigure(0, weight=2)
        actions.grid_columnconfigure(1, weight=1)
        actions.grid_columnconfigure(2, weight=1)
        actions.grid_columnconfigure(3, weight=1)
        actions.grid_columnconfigure(4, weight=1)

        self.generate_button = ttk.Button(
            actions,
            text="Generar combinación",
            style="Primary.TButton",
            command=self.generate_combination,
        )
        self.generate_button.grid(row=0, column=0, sticky="we", padx=(0, 8))
        self.copy_action_button = ttk.Button(
            actions,
            text="Copiar actual",
            style="Secondary.TButton",
            command=self.copy_current_password,
        )
        self.copy_action_button.grid(row=0, column=1, sticky="we", padx=4)
        self.batch_button = ttk.Button(
            actions,
            text="Generar lote...",
            style="Secondary.TButton",
            command=self.generate_batch,
        )
        self.batch_button.grid(row=0, column=2, sticky="we", padx=4)
        self.history_button = ttk.Button(
            actions,
            text="Historial...",
            style="Secondary.TButton",
            command=self.show_history,
        )
        self.history_button.grid(row=0, column=3, sticky="we", padx=4)
        self.reset_button = ttk.Button(
            actions,
            text="Resetear usadas",
            style="Secondary.TButton",
            command=self.reset_used_combinations,
        )
        self.reset_button.grid(row=0, column=4, sticky="we", padx=(4, 0))

    def _build_status_bar(self, container: ttk.Frame) -> None:
        """Construye barra de estado persistente de la interfaz."""
        ttk.Separator(container, orient=tk.HORIZONTAL).grid(
            row=5, column=0, sticky="we", pady=(0, 8)
        )
        ttk.Label(
            container,
            textvariable=self.status_var,
            style="Status.TLabel",
            anchor="w",
        ).grid(row=6, column=0, sticky="we")

    def _build_menu(self) -> None:
        """Define menús de configuración, seguridad y herramientas."""
        menu = tk.Menu(self.master)
        self.master.config(menu=menu)

        config_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Configuración", menu=config_menu)
        config_menu.add_command(
            label="Cambiar santos",
            command=lambda: self.change_file("santos"),
        )
        config_menu.add_command(
            label="Cambiar señas",
            command=lambda: self.change_file("senas"),
        )
        config_menu.add_command(
            label="Cambiar contraseñas",
            command=lambda: self.change_file("contrasenyas"),
        )
        config_menu.add_separator()
        config_menu.add_command(label="Salir", command=self.master.quit)

        source_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Origen de datos", menu=source_menu)
        for source_value, source_label in DATA_SOURCE_CHOICES:
            source_menu.add_radiobutton(
                label=source_label,
                variable=self.data_source_var,
                value=source_value,
                command=self._on_change_data_source,
            )

        options_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Opciones", menu=options_menu)
        format_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="Formato", menu=format_menu)
        for case_label, case_value in CASE_LABEL_TO_VALUE.items():
            format_menu.add_radiobutton(
                label=case_label,
                variable=self.case_var,
                value=case_value,
                command=self._on_change_case,
            )

        separator_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="Separador", menu=separator_menu)
        for separator_label, separator_value in SEPARATOR_LABEL_TO_VALUE.items():
            separator_menu.add_radiobutton(
                label=separator_label,
                variable=self.separator_var,
                value=separator_value,
                command=self._on_change_separator,
            )

        options_menu.add_checkbutton(
            label="Evitar repeticiones",
            variable=self.avoid_repetition_var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle_avoid_repetition,
        )
        options_menu.add_command(label="Usar semilla...", command=self._set_seed)

        security_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Seguridad", menu=security_menu)
        generation_mode_menu = tk.Menu(security_menu, tearoff=0)
        security_menu.add_cascade(label="Modo de generación", menu=generation_mode_menu)
        for generation_value, generation_label in GENERATION_MODE_CHOICES:
            generation_mode_menu.add_radiobutton(
                label=generation_label,
                variable=self.generation_mode_var,
                value=generation_value,
                command=self._on_change_generation_mode,
            )
        security_menu.add_checkbutton(
            label="Copiar automáticamente al generar",
            variable=self.auto_copy_var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle_auto_copy,
        )
        security_menu.add_command(
            label="Configurar limpieza de portapapeles...",
            command=self._configure_clipboard_clear_seconds,
        )
        security_menu.add_command(
            label="Longitud mínima de política...",
            command=self._configure_minimum_length,
        )
        security_menu.add_command(
            label="Mínimo tokens distintos...",
            command=self._configure_minimum_distinct_tokens,
        )
        security_menu.add_command(
            label="Palabras diceware...",
            command=self._configure_diceware_words,
        )

        tools_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Herramientas", menu=tools_menu)
        tools_menu.add_command(label="Generar lote...", command=self.generate_batch)
        tools_menu.add_command(label="Ver historial...", command=self.show_history)
        tools_menu.add_command(
            label="Resetear combinaciones usadas",
            command=self.reset_used_combinations,
        )
        tools_menu.add_command(label="Limpiar campo", command=self.clear_output)

        help_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Ayuda", menu=help_menu)
        help_menu.add_command(label="Acerca de...", command=self.show_about_dialog)

    def _register_shortcuts(self) -> None:
        """Registra atajos de teclado comunes para acciones frecuentes."""
        self.master.bind("<F5>", lambda _event: self.generate_combination())
        self.master.bind("<Control-g>", lambda _event: self.generate_combination())
        self.master.bind("<Control-c>", lambda _event: self.copy_current_password())

    def _bind_microinteractions(self) -> None:
        """Asocia microinteracciones visuales y de ayuda contextual."""
        self._bind_hover_hint(
            self.generate_button,
            "Genera una contraseña con la configuración actual.",
        )
        self._bind_hover_hint(
            self.copy_output_button,
            "Copia el resultado visible al portapapeles.",
        )
        self._bind_hover_hint(
            self.copy_action_button,
            "Copia rápidamente la contraseña generada.",
        )
        self._bind_hover_hint(
            self.batch_button,
            "Genera múltiples combinaciones y guarda en archivo.",
        )
        self._bind_hover_hint(
            self.history_button,
            "Abre el historial de contraseñas recientes.",
        )
        self._bind_hover_hint(
            self.reset_button,
            "Limpia el registro de combinaciones ya usadas.",
        )
        self._bind_hover_hint(
            self.apply_quick_button,
            "Aplica los cambios rápidos de seguridad y formato.",
        )
        self._bind_hover_hint(
            self.case_combo,
            "Elige cómo capitalizar la contraseña final.",
        )
        self._bind_hover_hint(
            self.separator_combo,
            "Selecciona el separador entre palabras.",
        )
        self.combination_entry.bind(
            "<FocusIn>",
            self._on_result_focus,
            add="+",
        )
        self.combination_entry.bind(
            "<Button-1>",
            self._on_result_focus,
            add="+",
        )

    def _bind_hover_hint(self, widget: tk.Misc, message: str) -> None:
        """Muestra ayuda en la barra de estado al pasar el cursor."""
        def on_enter(_event: tk.Event[tk.Misc]) -> None:
            """Muestra el hint cuando el cursor entra al widget."""
            self._show_hover_hint(message)

        def on_leave(_event: tk.Event[tk.Misc]) -> None:
            """Restaura estado al salir del widget."""
            self._clear_hover_hint()

        widget.bind("<Enter>", on_enter, add="+")
        widget.bind("<Leave>", on_leave, add="+")

    def _show_hover_hint(self, message: str) -> None:
        """Muestra una pista temporal sin cambiar el estado persistente."""
        if self._status_after_id is not None:
            try:
                self.master.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
            self._status_after_id = None
        self.status_var.set(message)

    def _clear_hover_hint(self) -> None:
        """Restaura en la barra el último estado persistente."""
        self.status_var.set(self._persistent_status)

    def _on_result_focus(self, _event: tk.Event[tk.Misc]) -> None:
        """Selecciona el resultado completo al enfocar el campo."""
        if not self.combination_entry.get():
            return
        self.combination_entry.selection_range(0, tk.END)
        self._set_transient_status(
            "Resultado seleccionado. Usa Ctrl+C para copiar.",
            duration_ms=1200,
        )

    def _show_config_error_if_needed(self) -> None:
        """Muestra aviso diferido si la carga de `config.json` falló."""
        if not self._config_read_error:
            return
        messagebox.showwarning(
            "Configuración",
            "No se pudo cargar config.json correctamente.\n"
            f"Detalle: {self._config_read_error}\n"
            "Se aplicaron valores por defecto seguros.",
            parent=self.master,
        )
        self._set_status("Se cargaron valores por defecto por error de configuración.")
        self._config_read_error = None

    def _collect_config_from_state(self) -> AppConfig:
        """Construye `AppConfig` a partir del estado de la UI."""
        mode = self._as_data_source_mode(self.data_source_var.get())
        generation_mode = self._as_generation_mode(self.generation_mode_var.get())
        case_mode = self._as_case_mode(self.case_var.get())

        self.config.modo = mode
        self.config.modo_generacion = generation_mode
        self.config.formato.case = case_mode
        self.config.formato.separador = self.separator_var.get()
        self.config.evitar_repeticiones = bool(self.avoid_repetition_var.get())
        self.config.clipboard.auto_copiar = bool(self.auto_copy_var.get())
        self.config.clipboard.limpiar_segundos = self._safe_int_var_value(
            self.clipboard_seconds_var,
            fallback=self.config.clipboard.limpiar_segundos,
            min_value=0,
            max_value=3600,
        )
        self.config.seguridad.longitud_minima = self._safe_int_var_value(
            self.minimum_length_var,
            fallback=self.config.seguridad.longitud_minima,
            min_value=8,
            max_value=256,
        )
        self.config.seguridad.tokens_distintos_min = self._safe_int_var_value(
            self.minimum_tokens_var,
            fallback=self.config.seguridad.tokens_distintos_min,
            min_value=1,
            max_value=20,
        )
        self.config.seguridad.palabras_diceware = self._safe_int_var_value(
            self.diceware_words_var,
            fallback=self.config.seguridad.palabras_diceware,
            min_value=4,
            max_value=12,
        )
        return self.config

    def _persist_config(self) -> None:
        """Persiste configuración y maneja errores de escritura."""
        config = self._collect_config_from_state()
        try:
            self._config_repository.save(config)
        except OSError as exc:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar configuración:\n{exc}",
                parent=self.master,
            )
            self._set_status("Error guardando configuración.")
            return
        self._refresh_overview_chips()

    def generate_combination(self) -> None:
        """Genera una combinación con feedback de entropía y nivel."""
        self._flash_button_text(self.generate_button, "Generando...", duration_ms=700)
        pools, errors = self._dictionary_repository.load_pools(self.config)
        if errors and self.config.modo == "archivos":
            messagebox.showerror(
                "Error de origen de datos",
                "\n".join(errors),
                parent=self.master,
            )
            self._set_status("No se pudo leer el origen de datos configurado.")
            return

        if not pools.santos or not pools.senas or not pools.contrasenyas:
            messagebox.showerror(
                "Error",
                "No hay suficientes datos para generar combinaciones.",
                parent=self.master,
            )
            self._set_status("No hay datos válidos para generar.")
            return

        try:
            generated = self._engine.generate(
                pools=pools,
                mode=self.config.modo_generacion,
                case_mode=self.config.formato.case,
                separator=self.config.formato.separador,
                avoid_repetition=self.config.evitar_repeticiones,
                diceware_words=self.config.seguridad.palabras_diceware,
            )
        except ExhaustedCombinationsError:
            messagebox.showwarning(
                "Sin combinaciones",
                "Se agotaron las combinaciones únicas con la configuración actual.",
                parent=self.master,
            )
            self._set_status("Se agotó el espacio de combinaciones únicas.")
            return
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self.master)
            self._set_status("No se pudo generar por datos insuficientes.")
            return

        self._set_output(generated.value)
        self.historial.appendleft(generated.value)
        entropy_label = classify_entropy(generated.entropy_bits)
        self.entropy_var.set(
            f"Entropía estimada: {generated.entropy_bits:.2f} bits ({entropy_label})"
        )
        self.last_result_var.set(
            "Última generación: "
            f"{self._generation_mode_label(self.config.modo_generacion)} · "
            f"{self._data_source_label(self.config.modo)}"
        )

        if self.config.clipboard.auto_copiar:
            self._clipboard.copy(
                generated.value,
                clear_after_seconds=self.config.clipboard.limpiar_segundos,
            )
            self._set_status("Contraseña generada y copiada automáticamente.")
        else:
            self._set_status("Contraseña generada correctamente.")

    def copy_current_password(self) -> None:
        """Copia la contraseña actual al portapapeles con limpieza opcional."""
        value = self.combination_entry.get()
        if not value:
            messagebox.showwarning(
                "Advertencia",
                "No hay combinación para copiar.",
                parent=self.master,
            )
            self._set_status("No hay texto para copiar.")
            return
        self._clipboard.copy(
            value,
            clear_after_seconds=self.config.clipboard.limpiar_segundos,
        )
        show_copy_feedback(self.master)
        self._flash_button_text(self.copy_output_button, "Copiado ✓")
        self._flash_button_text(self.copy_action_button, "Copiado ✓")
        self._set_status("Contraseña copiada al portapapeles.")

    def change_file(self, key: str) -> None:
        """Permite elegir nuevos archivos `.dict` en caliente."""
        selected = filedialog.askopenfilename(
            title=f"Seleccionar archivo para {key}",
            filetypes=[("Archivos de diccionario", "*.dict")],
        )
        if not selected:
            return
        self.config.archivos[key] = selected
        self._persist_config()
        self._set_status(f"Archivo de {key} actualizado.")
        messagebox.showinfo(
            "Actualización",
            f"Archivo de {key} actualizado.",
            parent=self.master,
        )

    def generate_batch(self) -> None:
        """Genera un lote aplicando política mínima de seguridad."""
        amount = simpledialog.askinteger(
            "Generar lote",
            "¿Cuántas combinaciones deseas generar?",
            minvalue=1,
            maxvalue=10000,
            parent=self.master,
        )
        if not amount:
            return

        save_path = filedialog.asksaveasfilename(
            title="Guardar lote",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not save_path:
            return

        pools, errors = self._dictionary_repository.load_pools(self.config)
        if errors and self.config.modo == "archivos":
            messagebox.showerror(
                "Error de origen de datos",
                "\n".join(errors),
                parent=self.master,
            )
            self._set_status("Error de origen de datos durante lote.")
            return

        if not pools.santos or not pools.senas or not pools.contrasenyas:
            messagebox.showerror(
                "Error",
                "No se pueden generar combinaciones sin listas válidas.",
                parent=self.master,
            )
            self._set_status("No hay listas válidas para generar lote.")
            return

        snapshot_used = self._engine.snapshot_used()
        generated_values: list[str] = []
        policy_failures = 0
        max_attempts = amount * 30
        attempts = 0

        while len(generated_values) < amount and attempts < max_attempts:
            attempts += 1
            try:
                generated = self._engine.generate(
                    pools=pools,
                    mode=self.config.modo_generacion,
                    case_mode=self.config.formato.case,
                    separator=self.config.formato.separador,
                    avoid_repetition=self.config.evitar_repeticiones,
                    diceware_words=self.config.seguridad.palabras_diceware,
                )
            except ExhaustedCombinationsError:
                break

            evaluation = validate_password_policy(
                password=generated.value,
                tokens=generated.tokens,
                separator=self.config.formato.separador,
                policy=self.config.seguridad,
            )
            if not evaluation.is_valid:
                policy_failures += 1
                continue
            generated_values.append(generated.value)

        # Restauramos para que el lote no altere el estado interactivo.
        self._engine.restore_used(snapshot_used)

        if not generated_values:
            messagebox.showwarning(
                "Lote vacío",
                "No se pudo generar ninguna combinación que cumpla la política.",
                parent=self.master,
            )
            self._set_status("Lote cancelado: política demasiado restrictiva.")
            return

        try:
            with Path(save_path).open("w", encoding="utf-8") as output_file:
                for line in generated_values:
                    output_file.write(line + "\n")
        except OSError as exc:
            messagebox.showerror(
                "Error",
                f"No se pudo escribir el lote:\n{exc}",
                parent=self.master,
            )
            self._set_status("Error al escribir el archivo de lote.")
            return

        details = (
            f"Se generaron {len(generated_values)} combinaciones válidas."
            f"\nDescartadas por política: {policy_failures}."
        )
        if len(generated_values) < amount:
            details += (
                "\nNo se alcanzó la cantidad solicitada por límites de política "
                "o por agotamiento de combinaciones."
            )
        self._set_status(
            f"Lote generado con {len(generated_values)} combinaciones válidas."
        )
        messagebox.showinfo("Lote generado", details, parent=self.master)

    def show_history(self) -> None:
        """Muestra historial de combinaciones recientes."""
        if not self.historial:
            messagebox.showinfo(
                "Historial",
                "Aún no hay combinaciones generadas.",
                parent=self.master,
            )
            self._set_status("No hay historial para mostrar.")
            return

        top = tk.Toplevel(self.master)
        top.title("Historial de combinaciones")
        top.geometry("620x360")
        top.minsize(580, 320)

        container = ttk.Frame(top, padding=12)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(1, weight=1)

        ttk.Label(
            container,
            text="Historial reciente",
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        listbox = tk.Listbox(container, font=("Consolas", 10))
        listbox.grid(row=1, column=0, sticky="nsew")
        for item in self.historial:
            listbox.insert(tk.END, item)

        button_bar = ttk.Frame(container)
        button_bar.grid(row=2, column=0, sticky="we", pady=(10, 0))
        ttk.Button(
            button_bar,
            text="Copiar seleccionado",
            command=lambda: self._copy_from_listbox(listbox),
        ).pack(side=tk.LEFT)
        ttk.Button(
            button_bar,
            text="Copiar todos",
            command=lambda: self._copy_text("\n".join(self.historial), with_feedback=True),
        ).pack(side=tk.LEFT, padx=(10, 0))

        listbox.bind("<Double-1>", lambda _event: self._copy_from_listbox(listbox))
        self._set_status("Historial abierto.")

    def clear_output(self) -> None:
        """Limpia campo de salida y reinicia métrica de entropía."""
        self._set_output("")
        self.entropy_var.set("Entropía estimada: --")
        self.last_result_var.set("Salida limpiada. Lista para una nueva generación.")
        self._set_status("Campo de salida limpiado.")

    def reset_used_combinations(self) -> None:
        """Resetea combinaciones usadas para opción `evitar repeticiones`."""
        self._engine.reset_used()
        self._set_status("Se resetearon las combinaciones usadas.")
        messagebox.showinfo(
            "Resetear",
            "Se han reseteado las combinaciones usadas.",
            parent=self.master,
        )

    def show_about_dialog(self) -> None:
        """Muestra información general y advertencias de seguridad."""
        messagebox.showinfo(
            "Acerca de",
            "Password Generator moderno\n\n"
            "- Interfaz moderna con controles rápidos.\n"
            "- Modos: memorable, secure y diceware.\n"
            "- Feedback de entropía estimada.\n"
            "- Política mínima de seguridad para lotes.\n"
            "- Portapapeles con limpieza automática opcional.",
            parent=self.master,
        )

    def _copy_from_listbox(self, listbox: tk.Listbox) -> None:
        """Copia el elemento seleccionado de un `Listbox`."""
        if not listbox.curselection():
            messagebox.showwarning(
                "Advertencia",
                "Selecciona una combinación del historial para copiar.",
                parent=self.master,
            )
            self._set_status("No se seleccionó una entrada del historial.")
            return
        value = str(listbox.get(listbox.curselection()[0]))
        self._copy_text(value, with_feedback=True)

    def _copy_text(self, text: str, *, with_feedback: bool) -> None:
        """Copia texto arbitrario respetando limpieza configurada."""
        self._clipboard.copy(
            text,
            clear_after_seconds=self.config.clipboard.limpiar_segundos,
        )
        if with_feedback:
            show_copy_feedback(self.master)
            self._flash_button_text(self.copy_output_button, "Copiado ✓")
            self._flash_button_text(self.copy_action_button, "Copiado ✓")
        self._set_status("Texto copiado al portapapeles.")

    def _set_seed(self) -> None:
        """Define semilla para modo memorable y advierte impacto de seguridad."""
        value = simpledialog.askstring(
            "Semilla",
            "Introduce una semilla (texto o número).\n"
            "Dejar vacío para generación no determinista.",
            parent=self.master,
        )
        if value is None:
            return
        normalized = value.strip() or None
        self.config.semilla = normalized
        self._engine.set_seed(normalized)
        self._persist_config()
        self._refresh_seed_warning()
        if normalized is not None:
            messagebox.showwarning(
                "Advertencia de seguridad",
                "Una semilla fija vuelve predecible el modo memorable.\n"
                "Evítala para contraseñas críticas.",
                parent=self.master,
            )
            self._set_status("Semilla fija establecida: modo memorable reproducible.")
        else:
            self._set_status("Semilla eliminada. Modo memorable no determinista.")

    def _configure_clipboard_clear_seconds(self) -> None:
        """Configura tiempo de autolimpieza del portapapeles."""
        value = simpledialog.askinteger(
            "Limpieza del portapapeles",
            "Segundos antes de limpiar automáticamente (0 para desactivar):",
            minvalue=0,
            maxvalue=3600,
            parent=self.master,
        )
        if value is None:
            return
        self.config.clipboard.limpiar_segundos = int(value)
        self.clipboard_seconds_var.set(int(value))
        self._persist_config()
        self._set_status("Tiempo de limpieza del portapapeles actualizado.")

    def _configure_minimum_length(self) -> None:
        """Ajusta longitud mínima requerida por la política de seguridad."""
        value = simpledialog.askinteger(
            "Longitud mínima",
            "Longitud mínima exigida para exportes por lote:",
            minvalue=8,
            maxvalue=256,
            parent=self.master,
        )
        if value is None:
            return
        self.config.seguridad.longitud_minima = int(value)
        self.minimum_length_var.set(int(value))
        self._persist_config()
        self._set_status("Longitud mínima de política actualizada.")

    def _configure_minimum_distinct_tokens(self) -> None:
        """Ajusta mínimo de tokens distintos en política de lote."""
        value = simpledialog.askinteger(
            "Tokens distintos",
            "Número mínimo de tokens distintos:",
            minvalue=1,
            maxvalue=20,
            parent=self.master,
        )
        if value is None:
            return
        self.config.seguridad.tokens_distintos_min = int(value)
        self.minimum_tokens_var.set(int(value))
        self._persist_config()
        self._set_status("Mínimo de tokens distintos actualizado.")

    def _configure_diceware_words(self) -> None:
        """Ajusta cantidad de palabras usadas en modo diceware."""
        value = simpledialog.askinteger(
            "Modo diceware",
            "Cantidad de palabras para modo diceware:",
            minvalue=4,
            maxvalue=12,
            parent=self.master,
        )
        if value is None:
            return
        self.config.seguridad.palabras_diceware = int(value)
        self.diceware_words_var.set(int(value))
        self._persist_config()
        self._set_status("Cantidad de palabras diceware actualizada.")

    def _apply_quick_security_settings(self) -> None:
        """Aplica desde la UI rápida los ajustes numéricos de seguridad."""
        self._persist_config()
        self._flash_button_text(self.apply_quick_button, "Aplicado ✓", duration_ms=950)
        self._set_status("Ajustes rápidos de seguridad aplicados.")

    def _on_quick_case_selected(self, _event: tk.Event[tk.Misc]) -> None:
        """Sincroniza selección del combo de capitalización con la configuración."""
        selected_label = self.case_display_var.get()
        mapped_value = CASE_LABEL_TO_VALUE.get(selected_label, "original")
        self.case_var.set(mapped_value)
        self._on_change_case()

    def _on_quick_separator_selected(self, _event: tk.Event[tk.Misc]) -> None:
        """Sincroniza selección del combo de separador con la configuración."""
        selected_label = self.separator_display_var.get()
        mapped_value = SEPARATOR_LABEL_TO_VALUE.get(selected_label, " ")
        self.separator_var.set(mapped_value)
        self._on_change_separator()

    def _on_change_data_source(self) -> None:
        """Sincroniza modo de origen cuando cambia en UI."""
        self._persist_config()
        self._set_status(f"Origen activo: {self._data_source_label(self.config.modo)}.")

    def _on_change_case(self) -> None:
        """Persiste cambio de capitalización."""
        self.case_display_var.set(self._case_value_to_label(self.case_var.get()))
        self._persist_config()
        self._set_status("Capitalización actualizada.")

    def _on_change_separator(self) -> None:
        """Persiste cambio de separador."""
        self.separator_display_var.set(
            self._separator_value_to_label(self.separator_var.get())
        )
        self._persist_config()
        self._set_status("Separador actualizado.")

    def _on_toggle_avoid_repetition(self) -> None:
        """Persiste cambio de opción evitar repeticiones."""
        self._persist_config()
        enabled = "activado" if self.config.evitar_repeticiones else "desactivado"
        self._set_status(f"Evitar repeticiones {enabled}.")

    def _on_change_generation_mode(self) -> None:
        """Persiste modo de generación y actualiza advertencias."""
        self._persist_config()
        self._refresh_seed_warning()
        self._set_status(
            f"Modo activo: {self._generation_mode_label(self.config.modo_generacion)}."
        )

    def _on_toggle_auto_copy(self) -> None:
        """Persiste preferencia de copiado automático."""
        self._persist_config()
        status = "activado" if self.config.clipboard.auto_copiar else "desactivado"
        self._set_status(f"Copiado automático {status}.")

    def _refresh_seed_warning(self) -> None:
        """Actualiza mensaje visible cuando hay semilla fija activa."""
        if self.config.semilla:
            mode = self.config.modo_generacion
            if mode == "memorable":
                self.seed_warning_var.set(
                    "Aviso: semilla fija activa (modo memorable reproducible)."
                )
            else:
                self.seed_warning_var.set(
                    "Aviso: hay semilla guardada; no aplica en este modo."
                )
            return
        self.seed_warning_var.set("")

    def _refresh_overview_chips(self) -> None:
        """Sincroniza los chips de resumen con la configuración activa."""
        self.mode_chip_var.set(
            f"Modo: {self._generation_mode_label(self.config.modo_generacion)}"
        )
        self.source_chip_var.set(f"Origen: {self._data_source_label(self.config.modo)}")

        if self.config.clipboard.auto_copiar:
            if self.config.clipboard.limpiar_segundos > 0:
                clipboard_text = (
                    "Portapapeles: auto-copia · "
                    f"limpieza {self.config.clipboard.limpiar_segundos}s"
                )
            else:
                clipboard_text = "Portapapeles: auto-copia · sin limpieza"
        else:
            clipboard_text = "Portapapeles: manual"
        self.clipboard_chip_var.set(clipboard_text)

        self.policy_chip_var.set(
            "Política: "
            f"{self.config.seguridad.longitud_minima}+ chars · "
            f"{self.config.seguridad.tokens_distintos_min}+ tokens"
        )

    def _set_output(self, value: str) -> None:
        """Escribe valor en el `Entry` readonly de salida."""
        self._last_generated_value = value
        self.combination_entry.config(state="normal")
        self.combination_entry.delete(0, tk.END)
        self.combination_entry.insert(0, value)
        self.combination_entry.selection_range(0, tk.END)
        self.combination_entry.config(state="readonly")

    def _set_status(self, message: str) -> None:
        """Actualiza texto de barra de estado inferior."""
        if self._status_after_id is not None:
            try:
                self.master.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
            self._status_after_id = None
        self._persistent_status = message
        self.status_var.set(message)

    def _set_transient_status(self, message: str, *, duration_ms: int = 1500) -> None:
        """Muestra un mensaje temporal y luego restaura el estado persistente."""
        if self._status_after_id is not None:
            try:
                self.master.after_cancel(self._status_after_id)
            except tk.TclError:
                pass
            self._status_after_id = None
        self.status_var.set(message)
        self._status_after_id = self.master.after(
            duration_ms,
            self._clear_hover_hint,
        )

    def _flash_button_text(
        self,
        button: ttk.Button,
        temporary_text: str,
        *,
        duration_ms: int = 900,
    ) -> None:
        """Cambia temporalmente el texto del botón como feedback visual."""
        widget_id = button.winfo_id()
        existing_job = self._button_restore_jobs.get(widget_id)
        if existing_job is not None:
            try:
                self.master.after_cancel(existing_job)
            except tk.TclError:
                pass
        if widget_id not in self._button_original_labels:
            self._button_original_labels[widget_id] = str(button.cget("text"))
        button.configure(text=temporary_text)

        def restore_callback() -> None:
            """Restaura texto original tras la espera programada."""
            self._restore_button_text(button, widget_id)

        self._button_restore_jobs[widget_id] = self.master.after(
            duration_ms,
            restore_callback,
        )

    def _restore_button_text(self, button: ttk.Button, widget_id: int) -> None:
        """Restaura texto original de un botón tras un feedback temporal."""
        self._button_restore_jobs.pop(widget_id, None)
        original_text = self._button_original_labels.get(widget_id)
        if original_text and button.winfo_exists():
            button.configure(text=original_text)

    @staticmethod
    def _safe_int_var_value(
        var: tk.IntVar,
        *,
        fallback: int,
        min_value: int,
        max_value: int,
    ) -> int:
        """Lee un `IntVar` de forma segura y acota su valor."""
        try:
            value = int(var.get())
        except (TypeError, ValueError, tk.TclError):
            return fallback
        return max(min_value, min(max_value, value))

    @staticmethod
    def _data_source_label(mode: DataSourceMode) -> str:
        """Devuelve etiqueta amigable para el modo de origen."""
        for value, label in DATA_SOURCE_CHOICES:
            if value == mode:
                return label
        return "Listas embebidas"

    @staticmethod
    def _generation_mode_label(mode: GenerationMode) -> str:
        """Devuelve etiqueta amigable para modo de generación."""
        for value, label in GENERATION_MODE_CHOICES:
            if value == mode:
                return label
        return "Memorable (PRNG)"

    @staticmethod
    def _case_value_to_label(case_value: str) -> str:
        """Mapea valor interno de case a etiqueta legible."""
        normalized = PasswordGeneratorApp._as_case_mode(case_value)
        return CASE_VALUE_TO_LABEL[normalized]

    @staticmethod
    def _separator_value_to_label(separator_value: str) -> str:
        """Mapea valor interno de separador a etiqueta legible."""
        for label, value in SEPARATOR_LABEL_TO_VALUE.items():
            if value == separator_value:
                return label
        return "Espacio"

    @staticmethod
    def _as_data_source_mode(raw_value: str) -> DataSourceMode:
        """Convierte string libre a `DataSourceMode` válido."""
        return "archivos" if raw_value == "archivos" else "embebido"

    @staticmethod
    def _as_generation_mode(raw_value: str) -> GenerationMode:
        """Convierte string libre a `GenerationMode` válido."""
        if raw_value in VALID_GENERATION_MODES:
            return raw_value
        return "memorable"

    @staticmethod
    def _as_case_mode(raw_value: str) -> TextCaseMode:
        """Convierte string libre a `TextCaseMode` válido."""
        if raw_value in {"original", "minusculas", "MAYUSCULAS", "Titulo"}:
            return cast(TextCaseMode, raw_value)
        return "original"


def run_app() -> None:
    """Punto de entrada para ejecutar la aplicación Tkinter."""
    root = tk.Tk()
    _app = PasswordGeneratorApp(root)
    root.mainloop()

