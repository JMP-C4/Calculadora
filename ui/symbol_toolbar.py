"""Barra de botones para insertar símbolos matemáticos."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ui.equation_input import EquationInput

TOOLBAR_TOKENS: tuple[tuple[str, str, bool], ...] = (
    ("dy/dx", "dy/dx", False),
    ("∫", "Integral", False),
    ("∞", "oo", False),
    ("exp", "exp()", True),
    ("√", "sqrt()", True),
    ("π", "pi", False),
)


class SymbolToolbar(ttk.Frame):
    """Botones que insertan tokens en el campo de ecuación."""

    def __init__(
        self,
        master: tk.Misc | None = None,
        equation_input: EquationInput | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        if equation_input is None:
            raise ValueError("SymbolToolbar requiere una instancia de EquationInput.")
        self.equation_input = equation_input

        self.buttons: dict[str, ttk.Button] = {}
        for label, token, cursor_inside in TOOLBAR_TOKENS:
            button = ttk.Button(
                self,
                text=label,
                width=max(3, len(label) + 1),
                command=lambda t=token, inside=cursor_inside: self.equation_input.insert_token(
                    t, place_cursor_inside=inside
                ),
            )
            button.pack(side="left", padx=2, pady=2)
            self.buttons[token] = button


__all__ = ["SymbolToolbar", "TOOLBAR_TOKENS"]
