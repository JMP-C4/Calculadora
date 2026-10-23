"""Previsualización tipográfica de la ecuación y sus condiciones."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

_PLACEHOLDER = r"$\frac{dy}{dx} = f(x, y)$"


def _format_number(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:g}"


class MathPreview(ttk.Frame):
    """Figura Matplotlib que renderiza LaTeX con ``mathtext``."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self.figure = Figure(figsize=(5.0, 1.5), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.axes.set_axis_off()

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self._current_latex = ""
        self.show_placeholder()

    def _draw(self, latex_str: str) -> None:
        self.axes.clear()
        self.axes.set_axis_off()
        self.axes.text(
            0.5,
            0.5,
            latex_str,
            ha="center",
            va="center",
            fontsize=16,
            transform=self.axes.transAxes,
        )
        self.figure.tight_layout(pad=0.2)
        self.canvas.draw_idle()
        self._current_latex = latex_str

    def render(self, latex_str: str, conditions: Any = None) -> None:
        """Renderiza ``latex_str``; si hay condiciones, las añade debajo."""

        expression = (latex_str or "").strip()
        if not expression:
            self.show_placeholder()
            return

        display = expression
        values = None
        if conditions is not None:
            x0 = getattr(conditions, "x0", None)
            y0 = getattr(conditions, "y0", None)
            if x0 is not None and y0 is not None:
                values = rf"y({_format_number(x0)}) = {_format_number(y0)}"

        if not display.startswith("$"):
            display = f"${display}$"
        if values is not None:
            display = display[:-1] + rf",\quad {values}$"

        self._draw(display)

    def show_placeholder(self) -> None:
        self._draw(_PLACEHOLDER)

    @property
    def current_latex(self) -> str:
        return self._current_latex


__all__ = ["MathPreview"]
