Password Generator
================================

Aplicación de escritorio (Tkinter) para generar combinaciones de tres segmentos: santo, seña y contraseña. Permite trabajar con archivos `.dict` o con listas embebidas.

Características
---------------

- Origen de datos seleccionable:
  - Archivos `.dict` (configurables desde el menú)
  - Listas embebidas (sin archivos externos)
- Copia al portapapeles con fallback si `pyperclip` no está disponible
- Preferencias de formato:
  - Capitalización: Original, minúsculas, MAYÚSCULAS, Título
  - Separador: espacio, guion, barra vertical, guion bajo
- Evitar repeticiones (opcional) y control de combinaciones ya usadas
- Historial de combinaciones recientes
- Generación por lotes y guardado a archivo
- Semilla reproducible para generar siempre las mismas combinaciones
- Atajos de teclado: F5, Ctrl+G (generar) y Ctrl+C (copiar)

Requisitos
----------

- Python 3.12 o superior
- Windows, macOS o Linux

Instalación
-----------

```
python -m venv venv   # o: python -m venv .venv
venv\Scripts\pip install -r requirements.txt   # Windows (o .venv\Scripts\...)
# Unix/macOS:
source venv/bin/activate && pip install -r requirements.txt
```

Uso
---

```
python generador.py
```

Generar ejecutable
-----------------

```
.\build\build.ps1        # Windows PowerShell
```

El .exe se crea en `dist\password-generator.exe`. Ver `build\LEEME.txt`.

- Menú "Origen de datos": selecciona "Archivos (*.dict)" o "Listas embebidas".
- Menú "Configuración": selecciona rutas de `santos.dict`, `senas.dict` y `contrasenyas.dict`.
- Menú "Opciones": define capitalización, separador, evitar repeticiones y semilla.
- Menú "Herramientas": genera un lote a archivo, consulta el historial, limpia el campo o resetea las combinaciones usadas.

Estructura de archivos `.dict`
------------------------------

- Un término por línea, sin líneas vacías. Ejemplo de `santos.dict`:

```
San Miguel
San Gabriel
San Rafael
```

Configuración
-------------

Se guarda en `config.json`. Ejemplo mínimo:

```
{
  "modo": "embebido",
  "archivos": {
    "santos": "dict/santos.dict",
    "senas": "dict/senas.dict",
    "contrasenyas": "dict/contrasenyas.dict"
  },
  "formato": { "case": "original", "separador": " " },
  "evitar_repeticiones": false,
  "historial_max": 50,
  "semilla": null
}
```

Notas
-----

- Si `pyperclip` no está disponible o falla, se usa el portapapeles de Tk.
- Si activas "Evitar repeticiones" y se agotan todas las combinaciones únicas, la app te avisará.

Licencia
--------

DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE (WTFPL) v2

Solución de problemas
---------------------

Tk/Tcl no encontrado (Windows):

- Error: `TclError: Can't find a usable init.tcl ...` al ejecutar `python generador.py`.
- Causas habituales:
  - Python instalado sin los componentes de Tcl/Tk (opción de “tcl/tk and IDLE”).
  - Múltiples instalaciones de Python conviven (por ejemplo, 3.12 en venv y 3.13 del sistema) y la 3.13 no tiene Tcl/Tk.

Soluciones:

- Reinstala Python asegurando la casilla “tcl/tk and IDLE”.
- O instala el bundle oficial de Python que incluye Tcl/Tk y verifica que `python -c "import tkinter; print(tkinter.TkVersion)"` funciona.
- Si usas varias versiones, ejecuta con el intérprete del entorno virtual que tenga Tcl/Tk. Ejemplos:
  - Windows (PowerShell): `venv\\Scripts\\python.exe generador.py`
  - Unix/macOS: `venv/bin/python generador.py`
- Comprueba variables de entorno que podrían interferir (`TCL_LIBRARY`, `TK_LIBRARY`). En la mayoría de casos no debes definirlas.
