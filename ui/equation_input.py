"""Campo de entrada de ecuaciones con atajos de teclado."""

from __future__ import annotations

import tkinter as tk
from functools import partial
from tkinter import ttk
from typing import Callable

SHORTCUTS: dict[str, tuple[str, bool]] = {
    "<Control-d>": ("dy/dx", False),
    "<Control-i>": ("Integral", False),
    "<Control-Shift-I>": ("oo", False),
    "<Control-e>": ("exp()", True),
    "<Control-Shift-S>": ("sqrt()", True),
    "<Control-p>": ("pi", False),
}


class EquationInput(ttk.Frame):
    """Entrada de una línea para la ecuación diferencial."""

    def __init__(
        self,
        master: tk.Misc | None = None,
        on_change: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_change = on_change

        self._text = tk.Text(
            self,
            height=1,
            wrap="none",
            undo=True,
            font=("DejaVu Sans Mono", 14),
            relief="flat",
            padx=8,
            pady=6,
        )
        self._text.pack(fill="x", expand=True)

        self._text.bind("<KeyRelease>", self._notify)
        self._text.bind("<<Paste>>", self._notify_after_idle)
        self._text.bind("<<Cut>>", self._notify_after_idle)
        self._text.bind("<Return>", lambda _event: "break")
        self._bind_shortcuts()

    def _bind_shortcuts(self) -> None:
        for sequence, (token, cursor_inside) in SHORTCUTS.items():
            self._text.bind(
                sequence,
                partial(self._on_shortcut, token, cursor_inside),
            )

    def _on_shortcut(self, token: str, cursor_inside: bool, _event=None):
        self.insert_token(token, place_cursor_inside=cursor_inside)
        return "break"

    def _notify(self, _event=None) -> None:
        if self.on_change is not None:
            self.on_change(self.get_text())

    def _notify_after_idle(self, _event=None) -> None:
        self.after_idle(self._notify)

    def insert_token(self, token: str, place_cursor_inside: bool = False) -> None:
        """Inserta ``token`` en la posición del cursor."""

        self._text.focus_set()
        self._text.insert("insert", token)
        if place_cursor_inside and token.endswith("()"):
            self._text.mark_set("insert", "insert-1c")
        self._notify()

    def get_text(self) -> str:
        return self._text.get("1.0", "end-1c")

    def set_text(self, text: str) -> None:
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._notify()

    def get_cursor_position(self) -> int:
        """Posición del cursor como índice de columna (base 0 en la línea 1)."""

        return int(self._text.index("insert").split(".")[1])

    def focus_input(self) -> None:
        self._text.focus_set()

    def bind_global_shortcut(self, sequence: str, callback: Callable[[], None]) -> None:
        """Registra un atajo alternativo (usado por el controlador principal)."""

        self._text.bind(sequence, lambda _event: (callback(), "break")[1])


__all__ = ["EquationInput", "SHORTCUTS"]
