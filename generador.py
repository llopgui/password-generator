"""Password Generator - estilo Santo-Seña-Contraseña.

Aplicación de escritorio para generar contraseñas memorables combinando
tres segmentos: santo, seña y contraseña, inspirado en el método descrito
por Edward Snowden en su libro.
"""

import json
import random
import sys
import tkinter as tk
from collections import deque
from itertools import product
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any, Dict, List, Tuple

try:
    import pyperclip
except Exception:
    pyperclip = None

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
DEFAULT_ARCHIVOS_REL: Dict[str, str] = {
    "santos": "dict/santos.dict",
    "senas": "dict/senas.dict",
    "contrasenyas": "dict/contrasenyas.dict",
}
VALID_MODOS = {"embebido", "archivos"}
VALID_CASES = {"original", "minusculas", "MAYUSCULAS", "Titulo"}


DEFAULT_SANTOS: List[str] = [
    "San Miguel",
    "San Gabriel",
    "San Rafael",
    "San Uriel",
    "San Jofiel",
    "San Chamuel",
    "San Zadkiel",
    "San Raguel",
    "San Remiel",
    "San Sariel",
    "San Anael",
    "San Cassiel",
    "San Azrael",
    "San Haniel",
    "San Jeremiel",
    "San Raziel",
    "San Camael",
    "San Metatron",
    "San Sandalfon",
    "San Ariel",
]

DEFAULT_SENYAS: List[str] = [
    "Espada",
    "Escudo",
    "Lanza",
    "Arco",
    "Flecha",
    "Casco",
    "Armadura",
    "Estandarte",
    "Trompeta",
    "Pergamino",
    "Cáliz",
    "Báculo",
    "Corona",
    "Anillo",
    "Medallón",
    "Talismán",
    "Cetro",
    "Orbe",
    "Capa",
    "Sandalia",
]

DEFAULT_CONTRASENYAS: List[str] = [
    "Valor",
    "Honor",
    "Lealtad",
    "Coraje",
    "Fuerza",
    "Justicia",
    "Verdad",
    "Libertad",
    "Sabiduría",
    "Compasión",
    "Esperanza",
    "Fe",
    "Caridad",
    "Humildad",
    "Paciencia",
    "Templanza",
    "Prudencia",
    "Diligencia",
    "Gratitud",
    "Perseverancia",
]


class SantoSenyaContrasenyaApp:
    """Interfaz de generación de Santo, Seña y Contraseña.

    Ofrece dos orígenes de datos:
    - "archivos": lee desde `dict/*.dict` configurables.
    - "embebido": usa listas internas incluidas en el código.
    """

    def __init__(self, master: tk.Tk) -> None:
        """Inicializa la aplicación y su interfaz.

        Args:
            master: Ventana principal de la aplicación.
        """
        self.master = master
        self._config_error: str | None = None
        self.master.title("Password Generator")
        self.master.geometry("520x260")
        self.master.resizable(False, False)

        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.config: Dict[str, Any] = self.cargar_configuracion()
        modo_inicial = self.config.get("modo", "embebido")
        self.data_source_var = tk.StringVar(value=modo_inicial)

        formato = self.config.get("formato", {})
        if not isinstance(formato, dict):
            formato = {}
        self.case_var = tk.StringVar(value=str(formato.get("case", "original")))
        self.sep_var = tk.StringVar(value=str(formato.get("separador", " ")))
        evitar = self.config.get("evitar_repeticiones", False)
        self.evitar_var = tk.BooleanVar(value=bool(evitar))

        # Estructuras auxiliares: set de combinaciones usadas e historial
        self.usadas: set[Tuple[str, str, str]] = set()
        self.historial_max: int = int(self.config.get("historial_max", 50))
        self.historial: deque[str] = deque(maxlen=self.historial_max)

        # PRNG con semilla opcional para reproducibilidad
        semilla = self.config.get("semilla")
        self.rng = random.Random(semilla) if semilla is not None else random.Random()

        self.create_widgets()

    def create_widgets(self) -> None:
        """Crea y configura los widgets de la interfaz gráfica."""
        self.master.grid_columnconfigure(0, weight=1)
        self.master.grid_rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.master, padding="20 20 20 20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=1)

        title_label = ttk.Label(
            main_frame,
            text="Password Generator",
            font=("Helvetica", 16, "bold"),
        )
        title_label.grid(column=0, row=0, columnspan=2, pady=(0, 20))

        combo_frame = ttk.Frame(
            main_frame,
            relief=tk.GROOVE,
            borderwidth=2,
        )
        combo_frame.grid(
            column=0,
            row=1,
            columnspan=2,
            sticky="we",
            pady=(0, 20),
        )
        combo_frame.grid_columnconfigure(0, weight=1)

        # Campo de una sola línea para la combinación generada.
        self.combinacion_entry = ttk.Entry(
            combo_frame,
            font=("Courier", 12),
            state="readonly",
            width=50,
        )
        self.combinacion_entry.grid(
            column=0,
            row=0,
            sticky="we",
            padx=10,
            pady=10,
        )

        button_frame = ttk.Frame(main_frame)
        button_frame.grid(column=0, row=2, columnspan=2, sticky="we")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        generate_button = ttk.Button(
            button_frame,
            text="Generar combinación",
            command=self.generar_combinacion,
        )
        generate_button.grid(column=0, row=0, sticky=tk.W, padx=(0, 5))

        copy_button = ttk.Button(
            button_frame,
            text="Copiar al portapapeles",
            command=self.copiar_al_portapapeles,
        )
        copy_button.grid(column=1, row=0, sticky=tk.E, padx=(5, 0))

        config_menu = tk.Menu(self.master)
        self.master.config(menu=config_menu)

        file_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Configuración", menu=file_menu)
        file_menu.add_command(
            label="Cambiar santos",
            command=lambda: self.cambiar_archivo("santos"),
        )
        file_menu.add_command(
            label="Cambiar señas",
            command=lambda: self.cambiar_archivo("senas"),
        )
        file_menu.add_command(
            label="Cambiar contraseñas",
            command=lambda: self.cambiar_archivo("contrasenyas"),
        )
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.master.quit)

        origen_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Origen de datos", menu=origen_menu)
        origen_menu.add_radiobutton(
            label="Archivos (*.dict)",
            variable=self.data_source_var,
            value="archivos",
            command=self._on_cambiar_origen,
        )
        origen_menu.add_radiobutton(
            label="Listas embebidas",
            variable=self.data_source_var,
            value="embebido",
            command=self._on_cambiar_origen,
        )

        # Opciones avanzadas
        opciones_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Opciones", menu=opciones_menu)

        formato_menu = tk.Menu(opciones_menu, tearoff=0)
        opciones_menu.add_cascade(label="Formato de texto", menu=formato_menu)
        formato_menu.add_radiobutton(
            label="Original",
            variable=self.case_var,
            value="original",
            command=self._on_cambiar_case,
        )
        formato_menu.add_radiobutton(
            label="minúsculas",
            variable=self.case_var,
            value="minusculas",
            command=self._on_cambiar_case,
        )
        formato_menu.add_radiobutton(
            label="MAYÚSCULAS",
            variable=self.case_var,
            value="MAYUSCULAS",
            command=self._on_cambiar_case,
        )
        formato_menu.add_radiobutton(
            label="Título",
            variable=self.case_var,
            value="Titulo",
            command=self._on_cambiar_case,
        )

        sep_menu = tk.Menu(opciones_menu, tearoff=0)
        opciones_menu.add_cascade(label="Separador", menu=sep_menu)
        sep_menu.add_radiobutton(
            label="Espacio",
            variable=self.sep_var,
            value=" ",
            command=self._on_cambiar_separador,
        )
        sep_menu.add_radiobutton(
            label="Guion (-)",
            variable=self.sep_var,
            value="-",
            command=self._on_cambiar_separador,
        )
        sep_menu.add_radiobutton(
            label="Barra vertical (|)",
            variable=self.sep_var,
            value=" | ",
            command=self._on_cambiar_separador,
        )
        sep_menu.add_radiobutton(
            label="Guion bajo (_)",
            variable=self.sep_var,
            value="_",
            command=self._on_cambiar_separador,
        )

        opciones_menu.add_checkbutton(
            label="Evitar repeticiones",
            variable=self.evitar_var,
            onvalue=True,
            offvalue=False,
            command=self._on_toggle_evitar,
        )

        opciones_menu.add_command(
            label="Usar semilla...",
            command=self._establecer_semilla,
        )

        herramientas_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Herramientas", menu=herramientas_menu)
        herramientas_menu.add_command(
            label="Generar lote...",
            command=self.generar_lote,
        )
        herramientas_menu.add_command(
            label="Ver historial...",
            command=self.ver_historial,
        )
        herramientas_menu.add_command(
            label="Limpiar campo",
            command=self.limpiar_campo,
        )
        herramientas_menu.add_command(
            label="Resetear combinaciones usadas",
            command=self._resetear_usadas,
        )

        ayuda_menu = tk.Menu(config_menu, tearoff=0)
        config_menu.add_cascade(label="Ayuda", menu=ayuda_menu)
        ayuda_menu.add_command(
            label="Acerca de...",
            command=self._mostrar_acerca_de,
        )

        self.master.bind("<F5>", lambda _e: self.generar_combinacion())
        self.master.bind("<Control-g>", lambda _e: self.generar_combinacion())
        self.master.bind("<Control-c>", lambda _e: self.copiar_al_portapapeles())
        if sys.platform == "darwin":
            self.master.bind("<Command-c>", lambda _e: self.copiar_al_portapapeles())

        # Mostrar advertencia si hubo error al cargar config (tras mostrar la ventana)
        self.master.after(100, self._mostrar_error_config_si_hay)

    def cargar_configuracion(self) -> Dict[str, Any]:
        """Carga la configuración desde `config.json`.

        Devuelve valores por defecto si no existe o faltan claves.
        Las rutas se resuelven relativas al directorio del script.
        """
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                    data = json.load(file)
            except (json.JSONDecodeError, OSError) as exc:
                data = {}
                self._config_error = str(exc)
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}

        modo = str(data.get("modo", "embebido"))
        if modo not in VALID_MODOS:
            modo = "embebido"
        data["modo"] = modo

        data["archivos"] = self._normalizar_archivos_config(data.get("archivos"))
        data["formato"] = self._normalizar_formato_config(data.get("formato"))
        data.setdefault("evitar_repeticiones", False)
        try:
            data.setdefault("historial_max", 50)
            data["historial_max"] = max(1, int(data["historial_max"]))
        except (TypeError, ValueError):
            data["historial_max"] = 50
        return data

    def _normalizar_archivos_config(self, archivos: Any) -> Dict[str, str]:
        """Normaliza el bloque `archivos` para mantener rutas estables.

        Args:
            archivos: Estructura de rutas leida de configuración.

        Returns:
            Diccionario con claves esperadas y rutas válidas.
        """
        if not isinstance(archivos, dict):
            archivos = {}
        normalizados: Dict[str, str] = {}
        for clave, ruta_default in DEFAULT_ARCHIVOS_REL.items():
            ruta = archivos.get(clave, ruta_default)
            normalizados[clave] = self._normalizar_ruta_dict(ruta, ruta_default)
        return normalizados

    def _normalizar_ruta_dict(self, ruta: Any, fallback: str) -> str:
        """Normaliza una ruta de diccionario evitando rutas temporales.

        Si detecta rutas absolutas temporales tipo `_MEI*` (PyInstaller),
        migra a la ruta relativa por defecto para hacer la config portable.

        Args:
            ruta: Ruta actual (cualquier tipo, proveniente de configuración).
            fallback: Ruta relativa por defecto.

        Returns:
            Ruta de archivo normalizada como string.
        """
        if not isinstance(ruta, str) or not ruta.strip():
            return fallback

        ruta_limpia = ruta.strip()
        candidata = Path(ruta_limpia)
        if not candidata.is_absolute():
            return ruta_limpia

        partes = [p.lower() for p in candidata.parts]
        es_mei = any(p.startswith("_mei") for p in partes)
        if es_mei:
            return fallback

        return ruta_limpia

    def _normalizar_formato_config(self, formato: Any) -> Dict[str, str]:
        """Normaliza el bloque `formato` con valores permitidos.

        Args:
            formato: Estructura de formato leida de configuración.

        Returns:
            Diccionario con claves `case` y `separador` saneadas.
        """
        if not isinstance(formato, dict):
            formato = {}

        case = str(formato.get("case", "original"))
        if case not in VALID_CASES:
            case = "original"

        separador = formato.get("separador", " ")
        if not isinstance(separador, str):
            separador = " "

        return {"case": case, "separador": separador}

    def _mostrar_error_config_si_hay(self) -> None:
        """Muestra advertencia si hubo error al cargar la configuración."""
        if self._config_error:
            messagebox.showwarning(
                "Configuración",
                f"No se pudo cargar config.json: {self._config_error}\n"
                "Se usarán valores por defecto.",
                parent=self.master,
            )
            self._config_error = None

    def guardar_configuracion(self) -> None:
        """Guarda la configuración actual en `config.json`."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as file:
                json.dump(self.config, file, indent=4, ensure_ascii=False)
        except OSError as exc:
            messagebox.showerror(
                "Error",
                f"No se pudo guardar la configuración:\n{exc}",
                parent=self.master,
            )

    def _resolver_ruta(self, ruta: str) -> Path:
        """Resuelve rutas relativas respecto al directorio del script.

        Args:
            ruta: Ruta del archivo (absoluta o relativa).

        Returns:
            Path resuelto.
        """
        p = Path(ruta)
        if not p.is_absolute():
            return _BASE_DIR / p
        return p

    def leer_archivo(self, nombre_archivo: str, silent: bool = False) -> List[str]:
        """Lee líneas desde un archivo `.dict` y devuelve palabras no vacías.

        Args:
            nombre_archivo: Ruta del archivo a leer (relativa o absoluta).
            silent: Si True, no muestra messagebox en errores (para agrupar avisos).

        Returns:
            Lista de palabras.
        """
        if not nombre_archivo:
            return []
        ruta = self._resolver_ruta(nombre_archivo)
        try:
            with open(ruta, "r", encoding="utf-8") as file:
                return [line.strip() for line in file if line.strip()]
        except FileNotFoundError:
            if not silent:
                messagebox.showerror(
                    "Error",
                    f"No se pudo encontrar el archivo:\n{ruta}",
                    parent=self.master,
                )
            return []
        except (OSError, UnicodeDecodeError) as exc:
            if not silent:
                messagebox.showerror(
                    "Error",
                    f"Error al leer el archivo:\n{ruta}\n{exc}",
                    parent=self.master,
                )
            return []

    def _obtener_listas(self) -> Tuple[List[str], List[str], List[str]]:
        """Obtiene listas de palabras según el origen seleccionado.

        Returns:
            Tupla con listas (santos, señas, contraseñas).
        """
        modo = self.data_source_var.get()
        if modo == "embebido":
            return (
                DEFAULT_SANTOS[:],
                DEFAULT_SENYAS[:],
                DEFAULT_CONTRASENYAS[:],
            )

        archivos = self.config.get("archivos", {})
        if not isinstance(archivos, dict):
            archivos = {}
        santos = self.leer_archivo(str(archivos.get("santos", "")), silent=True)
        senas = self.leer_archivo(str(archivos.get("senas", "")), silent=True)
        contras = self.leer_archivo(str(archivos.get("contrasenyas", "")), silent=True)
        return (santos, senas, contras)

    def generar_combinacion(self) -> None:
        """Genera y muestra una combinación de santo, seña y contraseña.

        Respeta formato, separador y la opción de evitar repeticiones.
        """
        santos, senas, contrasenyas = self._obtener_listas()

        if not all([santos, senas, contrasenyas]):
            messagebox.showerror(
                "Error",
                "No se pudieron cargar todas las listas. Revise el origen de datos.",
                parent=self.master,
            )
            return

        santo, senya, contrasenya = self._generar_triple(santos, senas, contrasenyas)

        combinacion = self._formatear(santo, senya, contrasenya)

        self.combinacion_entry.config(state="normal")
        self.combinacion_entry.delete(0, tk.END)
        self.combinacion_entry.insert(0, combinacion)
        self.combinacion_entry.config(state="readonly")
        self.historial.appendleft(combinacion)

    def copiar_al_portapapeles(self) -> None:
        """Copia la combinación visible al portapapeles del sistema."""
        combinacion = self.combinacion_entry.get()
        if not combinacion:
            messagebox.showwarning(
                "Advertencia",
                "No hay combinación para copiar.",
                parent=self.master,
            )
            return

        if pyperclip is not None:
            try:
                pyperclip.copy(combinacion)  # type: ignore[attr-defined]
            except Exception:
                # Fallback si falla pyperclip en el entorno
                self.master.clipboard_clear()
                self.master.clipboard_append(combinacion)
                self.master.update()
        else:
            # Fallback con el portapapeles de Tk
            self.master.clipboard_clear()
            self.master.clipboard_append(combinacion)
            self.master.update()

        messagebox.showinfo(
            "Copiado",
            "La combinación ha sido copiada al portapapeles.",
            parent=self.master,
        )

    def cambiar_archivo(self, tipo: str) -> None:
        """Permite elegir un nuevo archivo `.dict` y guardarlo en la
        configuración.

        Args:
            tipo: Uno de "santos", "senas" o "contrasenyas".
        """
        nuevo_archivo = filedialog.askopenfilename(
            title=f"Seleccionar archivo para {tipo}",
            filetypes=[("Archivos de diccionario", "*.dict")],
        )
        if nuevo_archivo:
            self.config.setdefault("archivos", {})[tipo] = nuevo_archivo
            self.guardar_configuracion()
            messagebox.showinfo(
                "Actualización",
                f"Archivo para {tipo} actualizado.",
                parent=self.master,
            )

    def _on_cambiar_origen(self) -> None:
        """Actualiza el modo de origen de datos en la configuración."""
        self.config["modo"] = self.data_source_var.get()
        self.guardar_configuracion()

    # --- Opciones y formato ---
    def _on_cambiar_case(self) -> None:
        """Actualiza el tipo de capitalización y guarda configuración."""
        self.config.setdefault("formato", {})["case"] = self.case_var.get()
        self.guardar_configuracion()

    def _on_cambiar_separador(self) -> None:
        """Actualiza el separador y guarda configuración."""
        self.config.setdefault("formato", {})["separador"] = self.sep_var.get()
        self.guardar_configuracion()

    def _on_toggle_evitar(self) -> None:
        """Activa o desactiva evitar repeticiones y guarda configuración."""
        self.config["evitar_repeticiones"] = bool(self.evitar_var.get())
        self.guardar_configuracion()

    def _normalizar_case(self, texto: str) -> str:
        """Devuelve `texto` con la capitalización elegida en opciones."""
        modo = self.case_var.get()
        if modo == "minusculas":
            return texto.lower()
        if modo == "MAYUSCULAS":
            return texto.upper()
        if modo == "Titulo":
            return texto.title()
        return texto

    def _formatear(self, s: str, e: str, c: str) -> str:
        """Aplica case y separador al triple y devuelve el string final."""
        s2 = self._normalizar_case(s)
        e2 = self._normalizar_case(e)
        c2 = self._normalizar_case(c)
        sep = self.sep_var.get()
        return f"{s2}{sep}{e2}{sep}{c2}"

    def _generar_triple(
        self,
        santos: List[str],
        senas: List[str],
        contras: List[str],
    ) -> Tuple[str, str, str]:
        """Genera un triple (santo, seña, contraseña).

        Evita repeticiones si está activado. Si se agota el espacio de
        combinaciones únicas, avisa y devuelve una combinación cualquiera.
        """
        evitar = bool(self.evitar_var.get())
        if not evitar:
            return (
                self.rng.choice(santos),
                self.rng.choice(senas),
                self.rng.choice(contras),
            )

        espacio = len(santos) * len(senas) * len(contras)
        if len(self.usadas) >= espacio:
            messagebox.showwarning(
                "Sin combinaciones",
                "Se han agotado todas las combinaciones únicas.",
                parent=self.master,
            )
            return (
                self.rng.choice(santos),
                self.rng.choice(senas),
                self.rng.choice(contras),
            )

        # Primero intenta al azar para mantener distribución uniforme.
        intentos_max = min(10000, max(1000, espacio * 2))
        for _ in range(intentos_max):
            triple = (
                self.rng.choice(santos),
                self.rng.choice(senas),
                self.rng.choice(contras),
            )
            if triple not in self.usadas:
                self.usadas.add(triple)
                return triple

        # Fallback determinista: garantiza encontrar una libre si existe.
        for santo, sena, contra in product(santos, senas, contras):
            triple = (santo, sena, contra)
            if triple not in self.usadas:
                self.usadas.add(triple)
                return triple

        # Defensa adicional por seguridad; no debería alcanzarse.
        return (
            self.rng.choice(santos),
            self.rng.choice(senas),
            self.rng.choice(contras),
        )

    # --- Semilla ---
    def _establecer_semilla(self) -> None:
        """Pide una semilla al usuario y reinicia el PRNG de la sesión."""
        msg = "Introduce una semilla (texto o número).\nDejar vacío para aleatoria."
        valor = simpledialog.askstring(
            "Semilla",
            msg,
            parent=self.master,
        )
        if valor is None:
            return
        if valor == "":
            self.rng = random.Random()
            self.config["semilla"] = None
        else:
            self.rng = random.Random(valor)
            self.config["semilla"] = valor
        self.usadas.clear()
        self.guardar_configuracion()

    # --- Herramientas ---
    def generar_lote(self) -> None:
        """Genera un lote de combinaciones y lo guarda en un archivo."""
        cantidad = simpledialog.askinteger(
            "Generar lote",
            "¿Cuántas combinaciones deseas generar?",
            minvalue=1,
            maxvalue=10000,
            parent=self.master,
        )
        if not cantidad:
            return

        ruta = filedialog.asksaveasfilename(
            title="Guardar lote",
            defaultextension=".txt",
            filetypes=[("Texto", "*.txt"), ("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not ruta:
            return

        santos, senas, contras = self._obtener_listas()
        if not all([santos, senas, contras]):
            messagebox.showerror(
                "Error",
                "No se pueden generar combinaciones sin listas válidas.",
                parent=self.master,
            )
            return

        evitar = bool(self.evitar_var.get())
        espacio_total = len(santos) * len(senas) * len(contras)
        disponibles = espacio_total - len(self.usadas)
        if evitar:
            if disponibles <= 0:
                messagebox.showwarning(
                    "Sin combinaciones",
                    "No quedan combinaciones únicas. Resetea o desactiva "
                    '"Evitar repeticiones".',
                    parent=self.master,
                )
                return
            if cantidad > disponibles:
                messagebox.showwarning(
                    "Lote limitado",
                    f"Solo hay {disponibles} combinaciones únicas disponibles. "
                    f"Se generarán {disponibles} en lugar de {cantidad}.",
                    parent=self.master,
                )
                cantidad = disponibles

        originales_usadas = set(self.usadas)
        generadas: List[str] = []
        for _ in range(int(cantidad)):
            s, e, c = self._generar_triple(santos, senas, contras)
            generadas.append(self._formatear(s, e, c))

        # Restaurar set si no se desea que el lote afecte al estado
        self.usadas = originales_usadas

        try:
            with open(ruta, "w", encoding="utf-8") as salida:
                for linea in generadas:
                    salida.write(linea + "\n")
        except OSError as exc:
            messagebox.showerror(
                "Error",
                f"No se pudo escribir el archivo:\n{exc}",
                parent=self.master,
            )
            return

        messagebox.showinfo(
            "Listo",
            f"Se generaron {len(generadas)} combinaciones en el archivo.",
            parent=self.master,
        )

    def ver_historial(self) -> None:
        """Muestra una ventana con el historial reciente de combinaciones."""
        if not self.historial:
            messagebox.showinfo(
                "Historial",
                "Aún no hay combinaciones generadas.",
                parent=self.master,
            )
            return

        top = tk.Toplevel(self.master)
        top.title("Historial de combinaciones")
        top.geometry("480x300")
        top.resizable(False, False)

        lst = tk.Listbox(top, font=("Courier", 10))
        lst.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for item in self.historial:
            lst.insert(tk.END, item)

        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(
            btn_frame,
            text="Copiar seleccionado",
            command=lambda: self._copiar_desde_listbox(lst),
        ).pack(side=tk.LEFT)
        ttk.Button(
            btn_frame,
            text="Copiar todos",
            command=lambda: self._copiar_texto("\n".join(self.historial), True),
        ).pack(side=tk.LEFT, padx=(10, 0))

        lst.bind(
            "<Double-1>",
            lambda _e: self._copiar_desde_listbox(lst),
        )

    def _copiar_desde_listbox(self, lst: tk.Listbox) -> None:
        """Copia el elemento seleccionado del historial, si lo hay."""
        if not lst.curselection():
            messagebox.showwarning(
                "Advertencia",
                "Selecciona una combinación del historial para copiar.",
                parent=self.master,
            )
            return
        valor = str(lst.get(lst.curselection()[0]))
        self._copiar_texto(valor, mostrar_feedback=True)

    def _copiar_texto(self, texto: str, mostrar_feedback: bool = False) -> None:
        """Copia `texto` al portapapeles con fallback si es necesario.

        Args:
            texto: Texto a copiar.
            mostrar_feedback: Si True, muestra un mensaje de confirmación.
        """
        if pyperclip is not None:
            try:
                pyperclip.copy(texto)  # type: ignore[attr-defined]
            except Exception:
                self.master.clipboard_clear()
                self.master.clipboard_append(texto)
                self.master.update()
        else:
            self.master.clipboard_clear()
            self.master.clipboard_append(texto)
            self.master.update()
        if mostrar_feedback:
            messagebox.showinfo(
                "Copiado",
                "Contenido copiado al portapapeles.",
                parent=self.master,
            )

    def limpiar_campo(self) -> None:
        """Limpia el campo de combinación."""
        self.combinacion_entry.config(state="normal")
        self.combinacion_entry.delete(0, tk.END)
        self.combinacion_entry.config(state="readonly")

    def _resetear_usadas(self) -> None:
        """Vacía el set de combinaciones usadas (evitar repeticiones)."""
        self.usadas.clear()
        messagebox.showinfo(
            "Resetear",
            "Se han reseteado las combinaciones usadas.",
            parent=self.master,
        )

    # --- Acerca de ---
    def _mostrar_acerca_de(self) -> None:
        """Muestra un cuadro de diálogo con información de la app."""
        msg = (
            "Password Generator - estilo Santo Seña y Contraseña.\n"
            "Aplicación de escritorio para generar contraseñas memorables\n"
            "combinando tres segmentos: santo, seña y contraseña\n"
            "inspirado en el método descrito por Edward Snowden en su libro."
        )
        messagebox.showinfo("Acerca de", msg, parent=self.master)


if __name__ == "__main__":
    root = tk.Tk()
    app = SantoSenyaContrasenyaApp(root)
    root.mainloop()
