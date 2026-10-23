"""Barra de estado inferior con mensajes y spinner."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Literal

StatusLevel = Literal["info", "error", "warning"]

_STYLES: dict[str, tuple[str, str]] = {
    "info": ("Info.TLabel", "#1b5e20"),
    "error": ("Error.TLabel", "#b71c1c"),
    "warning": ("Warning.TLabel", "#e65100"),
}


class StatusBar(ttk.Frame):
    """Muestra el estado de la aplicación y un indicador de progreso."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)

        style = ttk.Style(self)
        for _level, (style_name, color) in _STYLES.items():
            style.configure(style_name, foreground=color)

        self.label = ttk.Label(self, text="Listo", style="Info.TLabel", anchor="w")
        self.label.pack(side="left", fill="x", expand=True, padx=6, pady=2)

        self.spinner = ttk.Progressbar(self, mode="indeterminate", length=120)

    def set_status(self, message: str, level: StatusLevel = "info") -> None:
        style_name = _STYLES.get(level, _STYLES["info"])[0]
        self.label.configure(text=message, style=style_name)

    def show_spinner(self) -> None:
        if not self.spinner.winfo_manager():
            self.spinner.pack(side="right", padx=6, pady=2)
        self.spinner.start(12)

    def hide_spinner(self) -> None:
        self.spinner.stop()
        self.spinner.pack_forget()

    @property
    def message(self) -> str:
        return str(self.label.cget("text"))

    @property
    def level_style(self) -> str:
        return str(self.label.cget("style"))


__all__ = ["StatusBar", "StatusLevel"]
