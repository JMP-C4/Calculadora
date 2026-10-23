"""Panel de condiciones iniciales y de visualización."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk


@dataclass
class SolverConditions:
    """Condiciones iniciales e intervalo usado por solvers y gráficas."""

    x0: float | None = None
    y0: float | None = None
    x_min: float = -5.0
    x_max: float = 5.0
    y_min: float | None = None
    y_max: float | None = None


def _parse_float(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _format_float(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return str(value)


class ConditionPanel(ttk.LabelFrame):
    """Campos editables para x₀, y₀ e intervalos de la gráfica."""

    _FIELDS = (
        ("x0", "x₀"),
        ("y0", "y₀"),
        ("x_min", "x mín"),
        ("x_max", "x máx"),
        ("y_min", "y mín"),
        ("y_max", "y máx"),
    )

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        kwargs.setdefault("text", "Condiciones")
        super().__init__(master, **kwargs)

        self._vars: dict[str, tk.StringVar] = {}
        for index, (key, label) in enumerate(self._FIELDS):
            row, column = divmod(index, 2)
            ttk.Label(self, text=label).grid(
                row=row, column=column * 2, sticky="e", padx=(6, 2), pady=2
            )
            variable = tk.StringVar()
            entry = ttk.Entry(self, textvariable=variable, width=10)
            entry.grid(row=row, column=column * 2 + 1, sticky="w", padx=(0, 8), pady=2)
            self._vars[key] = variable

        self.set_conditions(SolverConditions())

    def get_conditions(self) -> SolverConditions:
        x_min = _parse_float(self._vars["x_min"].get())
        x_max = _parse_float(self._vars["x_max"].get())

        return SolverConditions(
            x0=_parse_float(self._vars["x0"].get()),
            y0=_parse_float(self._vars["y0"].get()),
            x_min=x_min if x_min is not None else -5.0,
            x_max=x_max if x_max is not None else 5.0,
            y_min=_parse_float(self._vars["y_min"].get()),
            y_max=_parse_float(self._vars["y_max"].get()),
        )

    def set_conditions(self, conditions: SolverConditions) -> None:
        self._vars["x0"].set(_format_float(conditions.x0))
        self._vars["y0"].set(_format_float(conditions.y0))
        self._vars["x_min"].set(_format_float(conditions.x_min))
        self._vars["x_max"].set(_format_float(conditions.x_max))
        self._vars["y_min"].set(_format_float(conditions.y_min))
        self._vars["y_max"].set(_format_float(conditions.y_max))


__all__ = ["ConditionPanel", "SolverConditions"]
