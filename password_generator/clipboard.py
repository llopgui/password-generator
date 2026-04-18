"""Servicio de portapapeles con limpieza automática opcional."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

try:
    import pyperclip
except Exception:
    pyperclip = None


class ClipboardManager:
    """Encapsula copia segura y borrado diferido del portapapeles."""

    def __init__(self, master: tk.Misc) -> None:
        """Recibe una referencia Tk para fallback y temporizadores."""
        self.master = master
        self._clear_job_id: str | None = None
        self._last_copied_text: str | None = None

    def copy(self, text: str, *, clear_after_seconds: int = 0) -> None:
        """Copia texto y programa limpieza automática opcional."""
        if pyperclip is not None:
            try:
                pyperclip.copy(text)
            except Exception:
                self._copy_with_tk(text)
        else:
            self._copy_with_tk(text)

        self._last_copied_text = text
        self._schedule_clear_if_needed(clear_after_seconds)

    def clear_now(self) -> None:
        """Borra de inmediato el contenido del portapapeles."""
        self._last_copied_text = None
        self._cancel_pending_clear()
        self.master.clipboard_clear()
        self.master.update()

    def _copy_with_tk(self, text: str) -> None:
        """Fallback de copia usando la API de Tkinter."""
        self.master.clipboard_clear()
        self.master.clipboard_append(text)
        self.master.update()

    def _schedule_clear_if_needed(self, clear_after_seconds: int) -> None:
        """Programa una limpieza sin pisar copias más recientes."""
        self._cancel_pending_clear()
        if clear_after_seconds <= 0:
            return

        self._clear_job_id = self.master.after(
            clear_after_seconds * 1000,
            self._clear_if_unchanged,
        )

    def _cancel_pending_clear(self) -> None:
        """Cancela la tarea de limpieza previa si existía."""
        if self._clear_job_id is None:
            return
        try:
            self.master.after_cancel(self._clear_job_id)
        except tk.TclError:
            # Ignoramos si el temporizador ya no existe.
            pass
        self._clear_job_id = None

    def _clear_if_unchanged(self) -> None:
        """Limpia el portapapeles solo si aún contiene el último valor copiado."""
        self._clear_job_id = None
        if self._last_copied_text is None:
            return
        try:
            clipboard_value = self.master.clipboard_get()
        except tk.TclError:
            return
        if clipboard_value == self._last_copied_text:
            self.master.clipboard_clear()
            self.master.update()
            self._last_copied_text = None


def show_copy_feedback(master: tk.Misc) -> None:
    """Muestra un mensaje estándar de copia al usuario."""
    messagebox.showinfo(
        "Copiado",
        "Contenido copiado al portapapeles.",
        parent=master,
    )

