"""Interfaz Tkinter para el Password Generator modernizado."""

from __future__ import annotations

import tkinter as tk
from collections import deque
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import cast

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


class PasswordGeneratorApp:
    """Controlador de la aplicación de escritorio."""

    def __init__(self, master: tk.Tk) -> None:
        """Inicializa servicios, estado y widgets principales."""
        self.master = master
        self.master.title("Password Generator")
        self.master.geometry("640x350")
        self.master.resizable(False, False)

        self._config_repository = ConfigRepository(Path(__file__).resolve().parent.parent / "config.json")
        self._dictionary_repository = DictionaryRepository(self._config_repository)
        self.config, self._config_read_error = self._config_repository.load()

        self._engine = GenerationEngine(seed=self.config.semilla)
        self._clipboard = ClipboardManager(master)
        self.historial: deque[str] = deque(maxlen=self.config.historial_max)
        self._last_generated_value = ""

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.data_source_var = tk.StringVar(value=self.config.modo)
        self.case_var = tk.StringVar(value=self.config.formato.case)
        self.separator_var = tk.StringVar(value=self.config.formato.separador)
        self.avoid_repetition_var = tk.BooleanVar(value=self.config.evitar_repeticiones)
        self.generation_mode_var = tk.StringVar(value=self.config.modo_generacion)
        self.auto_copy_var = tk.BooleanVar(value=self.config.clipboard.auto_copiar)
        self.entropy_var = tk.StringVar(value="Entropía: --")
        self.seed_warning_var = tk.StringVar(value="")

        self._build_layout()
        self._build_menu()
        self._register_shortcuts()
        self._refresh_seed_warning()
        self.master.after(100, self._show_config_error_if_needed)

    def _build_layout(self) -> None:
        """Construye widgets principales de salida y acciones rápidas."""
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        container = ttk.Frame(self.master, padding="20 20 20 20")
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)

        title_label = ttk.Label(
            container,
            text="Password Generator",
            font=("Helvetica", 18, "bold"),
        )
        title_label.grid(row=0, column=0, pady=(0, 16), sticky="w")

        self.combination_entry = ttk.Entry(
            container,
            font=("Courier", 12),
            state="readonly",
            width=68,
        )
        self.combination_entry.grid(row=1, column=0, pady=(0, 8), sticky="we")

        entropy_label = ttk.Label(
            container,
            textvariable=self.entropy_var,
            font=("Helvetica", 10),
        )
        entropy_label.grid(row=2, column=0, pady=(0, 6), sticky="w")

        seed_warning_label = ttk.Label(
            container,
            textvariable=self.seed_warning_var,
            font=("Helvetica", 10),
            foreground="#8a5a00",
        )
        seed_warning_label.grid(row=3, column=0, pady=(0, 14), sticky="w")

        actions_frame = ttk.Frame(container)
        actions_frame.grid(row=4, column=0, sticky="we")
        actions_frame.grid_columnconfigure(0, weight=1)
        actions_frame.grid_columnconfigure(1, weight=1)
        actions_frame.grid_columnconfigure(2, weight=1)

        ttk.Button(
            actions_frame,
            text="Generar combinación",
            command=self.generate_combination,
        ).grid(row=0, column=0, padx=(0, 6), sticky="we")
        ttk.Button(
            actions_frame,
            text="Copiar al portapapeles",
            command=self.copy_current_password,
        ).grid(row=0, column=1, padx=(0, 6), sticky="we")
        ttk.Button(
            actions_frame,
            text="Limpiar campo",
            command=self.clear_output,
        ).grid(row=0, column=2, sticky="we")

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
        source_menu.add_radiobutton(
            label="Archivos (*.dict)",
            variable=self.data_source_var,
            value="archivos",
            command=self._on_change_data_source,
        )
        source_menu.add_radiobutton(
            label="Listas embebidas",
            variable=self.data_source_var,
            value="embebido",
            command=self._on_change_data_source,
        )

        options_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Opciones", menu=options_menu)

        format_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="Formato", menu=format_menu)
        format_menu.add_radiobutton(
            label="Original",
            variable=self.case_var,
            value="original",
            command=self._on_change_case,
        )
        format_menu.add_radiobutton(
            label="minúsculas",
            variable=self.case_var,
            value="minusculas",
            command=self._on_change_case,
        )
        format_menu.add_radiobutton(
            label="MAYÚSCULAS",
            variable=self.case_var,
            value="MAYUSCULAS",
            command=self._on_change_case,
        )
        format_menu.add_radiobutton(
            label="Título",
            variable=self.case_var,
            value="Titulo",
            command=self._on_change_case,
        )

        separator_menu = tk.Menu(options_menu, tearoff=0)
        options_menu.add_cascade(label="Separador", menu=separator_menu)
        separator_menu.add_radiobutton(
            label="Espacio",
            variable=self.separator_var,
            value=" ",
            command=self._on_change_separator,
        )
        separator_menu.add_radiobutton(
            label="Guion (-)",
            variable=self.separator_var,
            value="-",
            command=self._on_change_separator,
        )
        separator_menu.add_radiobutton(
            label="Guion bajo (_)",
            variable=self.separator_var,
            value="_",
            command=self._on_change_separator,
        )
        separator_menu.add_radiobutton(
            label="Barra vertical (|)",
            variable=self.separator_var,
            value="|",
            command=self._on_change_separator,
        )
        separator_menu.add_radiobutton(
            label="Punto (.)",
            variable=self.separator_var,
            value=".",
            command=self._on_change_separator,
        )

        options_menu.add_checkbutton(
            label="Evitar repeticiones",
            variable=self.avoid_repetition_var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle_avoid_repetition,
        )
        options_menu.add_command(
            label="Usar semilla...",
            command=self._set_seed,
        )

        security_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Seguridad", menu=security_menu)

        generation_mode_menu = tk.Menu(security_menu, tearoff=0)
        security_menu.add_cascade(label="Modo de generación", menu=generation_mode_menu)
        generation_mode_menu.add_radiobutton(
            label="Memorable (PRNG)",
            variable=self.generation_mode_var,
            value="memorable",
            command=self._on_change_generation_mode,
        )
        generation_mode_menu.add_radiobutton(
            label="Secure (SystemRandom)",
            variable=self.generation_mode_var,
            value="secure",
            command=self._on_change_generation_mode,
        )
        generation_mode_menu.add_radiobutton(
            label="Diceware",
            variable=self.generation_mode_var,
            value="diceware",
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

    def generate_combination(self) -> None:
        """Genera una combinación con feedback de entropía y nivel."""
        pools, errors = self._dictionary_repository.load_pools(self.config)
        if errors and self.config.modo == "archivos":
            messagebox.showerror(
                "Error de origen de datos",
                "\n".join(errors),
                parent=self.master,
            )
            return

        if not pools.santos or not pools.senas or not pools.contrasenyas:
            messagebox.showerror(
                "Error",
                "No hay suficientes datos para generar combinaciones.",
                parent=self.master,
            )
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
            return
        except ValueError as exc:
            messagebox.showerror("Error", str(exc), parent=self.master)
            return

        self._set_output(generated.value)
        self.historial.appendleft(generated.value)
        entropy_label = classify_entropy(generated.entropy_bits)
        self.entropy_var.set(
            f"Entropía estimada: {generated.entropy_bits:.2f} bits ({entropy_label})"
        )

        if self.config.clipboard.auto_copiar:
            self._clipboard.copy(
                generated.value,
                clear_after_seconds=self.config.clipboard.limpiar_segundos,
            )
            show_copy_feedback(self.master)

    def copy_current_password(self) -> None:
        """Copia la contraseña actual al portapapeles con limpieza opcional."""
        value = self.combination_entry.get()
        if not value:
            messagebox.showwarning(
                "Advertencia",
                "No hay combinación para copiar.",
                parent=self.master,
            )
            return
        self._clipboard.copy(
            value,
            clear_after_seconds=self.config.clipboard.limpiar_segundos,
        )
        show_copy_feedback(self.master)

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
            return

        if not pools.santos or not pools.senas or not pools.contrasenyas:
            messagebox.showerror(
                "Error",
                "No se pueden generar combinaciones sin listas válidas.",
                parent=self.master,
            )
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
        messagebox.showinfo("Lote generado", details, parent=self.master)

    def show_history(self) -> None:
        """Muestra historial de combinaciones recientes."""
        if not self.historial:
            messagebox.showinfo(
                "Historial",
                "Aún no hay combinaciones generadas.",
                parent=self.master,
            )
            return

        top = tk.Toplevel(self.master)
        top.title("Historial de combinaciones")
        top.geometry("560x320")
        top.resizable(False, False)

        listbox = tk.Listbox(top, font=("Courier", 10))
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for item in self.historial:
            listbox.insert(tk.END, item)

        button_bar = ttk.Frame(top)
        button_bar.pack(fill=tk.X, padx=10, pady=(0, 10))
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

    def clear_output(self) -> None:
        """Limpia campo de salida y reinicia métrica de entropía."""
        self._set_output("")
        self.entropy_var.set("Entropía: --")

    def reset_used_combinations(self) -> None:
        """Resetea combinaciones usadas para opción `evitar repeticiones`."""
        self._engine.reset_used()
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
        self._persist_config()

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
        self._persist_config()

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
        self._persist_config()

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
        self._persist_config()

    def _on_change_data_source(self) -> None:
        """Sincroniza modo de origen cuando cambia en UI."""
        self._persist_config()

    def _on_change_case(self) -> None:
        """Persiste cambio de capitalización."""
        self._persist_config()

    def _on_change_separator(self) -> None:
        """Persiste cambio de separador."""
        self._persist_config()

    def _on_toggle_avoid_repetition(self) -> None:
        """Persiste cambio de opción evitar repeticiones."""
        self._persist_config()

    def _on_change_generation_mode(self) -> None:
        """Persiste modo de generación y actualiza advertencias."""
        self._persist_config()
        self._refresh_seed_warning()

    def _on_toggle_auto_copy(self) -> None:
        """Persiste preferencia de copiado automático."""
        self._persist_config()

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
                    "Aviso: existe semilla fija guardada; no aplica en este modo."
                )
            return
        self.seed_warning_var.set("")

    def _set_output(self, value: str) -> None:
        """Escribe valor en el `Entry` readonly de salida."""
        self._last_generated_value = value
        self.combination_entry.config(state="normal")
        self.combination_entry.delete(0, tk.END)
        self.combination_entry.insert(0, value)
        self.combination_entry.config(state="readonly")

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

