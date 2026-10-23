"""Vista de gráficas: solución, campo de direcciones y superficie 3D."""

from __future__ import annotations

import tkinter as tk
from enum import Enum
from tkinter import ttk
from typing import TYPE_CHECKING, Any, Callable

import numpy as np
import sympy as sp
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

if TYPE_CHECKING:  # pragma: no cover
    from math_engine.numeric_solver import NumericResult
    from math_engine.symbolic_solver import SymbolicResult

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)

_DEFAULT_BOUNDS = (-5.0, 5.0, -5.0, 5.0)


class PlotMode(str, Enum):
    SOLUTION = "y(x)"
    DIRECTION_FIELD = "Direction Field"
    SURFACE_3D = "Surface 3D"


def compute_direction_field_bounds(
    rhs: sp.Expr,
    conditions: Any,
) -> tuple[float, float, float, float]:
    """Retorna ``(x_min, x_max, y_min, y_max)`` con valores por defecto."""

    del rhs
    if conditions is None:
        return _DEFAULT_BOUNDS

    x_min = getattr(conditions, "x_min", None)
    x_max = getattr(conditions, "x_max", None)
    y_min = getattr(conditions, "y_min", None)
    y_max = getattr(conditions, "y_max", None)

    if x_min is None or x_max is None:
        x_min, x_max = _DEFAULT_BOUNDS[0], _DEFAULT_BOUNDS[1]
    if y_min is None or y_max is None:
        y_min, y_max = _DEFAULT_BOUNDS[2], _DEFAULT_BOUNDS[3]
    return float(x_min), float(x_max), float(y_min), float(y_max)


class PlotView(ttk.Frame):
    """Figura Matplotlib con selector de modo y vistas 3D predefinidas."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self.figure = Figure(figsize=(6.5, 4.8), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.current_mode = PlotMode.SOLUTION
        self.on_mode_change: Callable[[PlotMode], None] | None = None
        self.last_surface_shape: tuple[int, int] | None = None

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 4))

        ttk.Label(header, text="Modo:").pack(side="left", padx=(0, 6))
        self.mode_selector = ttk.Combobox(
            header,
            state="readonly",
            width=16,
            values=[mode.value for mode in PlotMode],
        )
        self.mode_selector.set(self.current_mode.value)
        self.mode_selector.pack(side="left")
        self.mode_selector.bind("<<ComboboxSelected>>", self._on_mode_selected)

        self.view_buttons = ttk.Frame(header)
        self._view_buttons = {}
        for label, elev, azim in (
            ("Frontal", 0, 0),
            ("Lateral", 0, 90),
            ("Isométrica", 30, 45),
        ):
            button = ttk.Button(
                self.view_buttons,
                text=label,
                command=lambda e=elev, a=azim: self.set_3d_view(e, a),
            )
            button.pack(side="left", padx=2)
            self._view_buttons[label] = button

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        toolbar_frame = ttk.Frame(self)
        toolbar_frame.pack(fill="x")
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        self._show_message("Introduce una ecuación y resuelve para graficar.")

    def _on_mode_selected(self, _event=None) -> None:
        mode = PlotMode(self.mode_selector.get())
        self.current_mode = mode
        self._update_view_buttons()
        if self.on_mode_change is not None:
            self.on_mode_change(mode)

    def _update_view_buttons(self) -> None:
        if self.current_mode == PlotMode.SURFACE_3D:
            self.view_buttons.pack(side="right", padx=4)
        else:
            self.view_buttons.pack_forget()

    def _reset_2d(self) -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True, linestyle="--", alpha=0.35)
        self.axes.set_xlabel("x")
        self.axes.set_ylabel("y")

    def _reset_3d(self):
        self.figure.clear()
        self.axes = self.figure.add_subplot(111, projection="3d")
        self.axes.set_xlabel("x")
        self.axes.set_ylabel("y")
        self.axes.set_zlabel("z = f(x, y)")
        return self.axes

    def _show_message(self, message: str) -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.set_axis_off()
        self.axes.text(
            0.5,
            0.5,
            message,
            ha="center",
            va="center",
            fontsize=12,
            transform=self.axes.transAxes,
            color="#666666",
        )
        self.canvas.draw_idle()

    def _evaluate(self, function, x_values: np.ndarray) -> np.ndarray:
        try:
            with np.errstate(all="ignore"):
                values = function(x_values)
            array = np.asarray(values, dtype=float)
            if array.shape != x_values.shape:
                array = np.broadcast_to(array, x_values.shape).astype(float)
            return np.where(np.isfinite(array), array, np.nan)
        except Exception:
            return np.full_like(x_values, np.nan, dtype=float)

    def _apply_limits(self, conditions: Any) -> None:
        if conditions is None:
            return
        x_min = getattr(conditions, "x_min", None)
        x_max = getattr(conditions, "x_max", None)
        y_min = getattr(conditions, "y_min", None)
        y_max = getattr(conditions, "y_max", None)
        if x_min is not None and x_max is not None and x_min < x_max:
            self.axes.set_xlim(float(x_min), float(x_max))
        if y_min is not None and y_max is not None and y_min < y_max:
            self.axes.set_ylim(float(y_min), float(y_max))

    def _plot_symbolic(
        self,
        symbolic: "SymbolicResult",
        x_values: np.ndarray,
    ) -> bool:
        particular = symbolic.particular_solution
        general = symbolic.general_solution

        if particular is not None:
            curve = self._evaluate(sp.lambdify(x, particular.rhs, "numpy"), x_values)
            self.axes.plot(x_values, curve, color="#1565c0", linewidth=2, label="Solución particular")
            return True

        if general is None:
            return False

        constants = sorted(
            (symbol for symbol in general.rhs.free_symbols if symbol != x),
            key=str,
        )
        if not constants:
            curve = self._evaluate(sp.lambdify(x, general.rhs, "numpy"), x_values)
            self.axes.plot(x_values, curve, color="#1565c0", linewidth=2, label="Solución simbólica")
            return True

        constant = constants[0]
        colors = ("#1565c0", "#2e7d32", "#6a1b9a", "#ef6c00", "#00838f")
        plotted = False
        for value, color in zip((-2, -1, 0, 1, 2), colors):
            expression = general.rhs.subs(constant, value)
            curve = self._evaluate(sp.lambdify(x, expression, "numpy"), x_values)
            if np.all(np.isnan(curve)):
                continue
            self.axes.plot(
                x_values,
                curve,
                color=color,
                linewidth=1.5,
                alpha=0.85,
                label=f"{constant} = {value}",
            )
            plotted = True
        return plotted

    def _plot_numeric(self, numeric: "NumericResult") -> bool:
        if numeric is None or numeric.x_arr is None or numeric.y_arr is None:
            return False
        x_values = np.asarray(numeric.x_arr, dtype=float)
        y_values = np.asarray(numeric.y_arr, dtype=float)
        mask = np.isfinite(x_values) & np.isfinite(y_values)
        self.axes.plot(
            x_values[mask],
            y_values[mask],
            color="#d84315",
            linewidth=2,
            linestyle="--",
            label="Solución numérica",
        )
        return bool(np.any(mask))

    def plot_solution(
        self,
        symbolic: "SymbolicResult | None",
        numeric: "NumericResult | None",
        conditions: Any,
    ) -> None:
        """Grafica la solución simbólica y/o numérica sobre el intervalo."""

        self._reset_2d()
        x_min, x_max = -5.0, 5.0
        if conditions is not None:
            condition_x_min = getattr(conditions, "x_min", None)
            condition_x_max = getattr(conditions, "x_max", None)
            if condition_x_min is not None:
                x_min = float(condition_x_min)
            if condition_x_max is not None:
                x_max = float(condition_x_max)
        if x_min >= x_max:
            x_min, x_max = -5.0, 5.0
        x_values = np.linspace(float(x_min), float(x_max), 600)

        plotted = False
        if symbolic is not None and symbolic.error is None:
            plotted = self._plot_symbolic(symbolic, x_values) or plotted
        plotted = self._plot_numeric(numeric) or plotted

        if not plotted:
            self._show_message("No hay una solución disponible para graficar.")
            return

        self.axes.set_title("Solución de la EDO")
        self._apply_limits(conditions)
        handles, _labels = self.axes.get_legend_handles_labels()
        if handles:
            self.axes.legend(loc="best", fontsize=9)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.toolbar.update()

    def plot_direction_field(
        self,
        rhs: sp.Expr,
        conditions: Any,
        solution_curve: "NumericResult | None" = None,
    ) -> None:
        """Dibuja el campo de pendientes y, si existe, la curva solución."""

        self._reset_2d()
        x_min, x_max, y_min, y_max = compute_direction_field_bounds(rhs, conditions)

        grid_size = 25
        x_grid = np.linspace(x_min, x_max, grid_size)
        y_grid = np.linspace(y_min, y_max, grid_size)
        x_mesh, y_mesh = np.meshgrid(x_grid, y_grid)

        try:
            function = sp.lambdify((x, y), rhs, "numpy")
            with np.errstate(all="ignore"):
                slopes = np.asarray(function(x_mesh, y_mesh), dtype=float)
            slopes = np.broadcast_to(slopes, x_mesh.shape).astype(float)
        except Exception:
            slopes = np.full_like(x_mesh, np.nan, dtype=float)

        u = np.ones_like(x_mesh)
        v = slopes
        length = np.hypot(u, v)
        length = np.where((length == 0) | ~np.isfinite(length), 1.0, length)
        u = u / length
        v = np.where(np.isfinite(v), v / length, np.nan)
        mask = np.isfinite(v)

        self.axes.quiver(
            x_mesh[mask],
            y_mesh[mask],
            u[mask],
            v[mask],
            color="#455a64",
            angles="xy",
            pivot="mid",
            width=0.002,
        )
        plotted = self._plot_numeric(solution_curve) if solution_curve is not None else False

        self.axes.set_xlim(x_min, x_max)
        self.axes.set_ylim(y_min, y_max)
        self.axes.set_title("Campo de direcciones")
        if plotted:
            self.axes.legend(loc="best", fontsize=9)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.toolbar.update()

    def plot_surface_3d(self, rhs: sp.Expr, conditions: Any) -> None:
        """Grafica ``z = f(x, y)`` sobre una malla de al menos 50×50 puntos."""

        axes = self._reset_3d()
        x_min, x_max, y_min, y_max = compute_direction_field_bounds(rhs, conditions)
        grid_size = 60
        x_grid = np.linspace(x_min, x_max, grid_size)
        y_grid = np.linspace(y_min, y_max, grid_size)
        x_mesh, y_mesh = np.meshgrid(x_grid, y_grid)

        try:
            function = sp.lambdify((x, y), rhs, "numpy")
            with np.errstate(all="ignore"):
                z_mesh = np.asarray(function(x_mesh, y_mesh), dtype=float)
            z_mesh = np.broadcast_to(z_mesh, x_mesh.shape).astype(float)
        except Exception:
            self._show_message("No se pudo evaluar f(x, y) para la superficie.")
            return

        self.last_surface_shape = z_mesh.shape
        surface = axes.plot_surface(
            x_mesh,
            y_mesh,
            z_mesh,
            cmap="viridis",
            linewidth=0,
            antialiased=True,
        )
        axes.set_title(r"Superficie $z = f(x, y)$")
        self.figure.colorbar(surface, ax=axes, shrink=0.65, pad=0.08)
        self.figure.tight_layout()
        self.canvas.draw_idle()
        self.toolbar.update()

    def set_3d_view(self, elev: float, azim: float) -> None:
        """Ajusta la cámara si la gráfica actual es 3D."""

        if getattr(self.axes, "name", "") != "3d":
            return
        self.axes.view_init(elev=elev, azim=azim)
        self.canvas.draw_idle()


__all__ = ["PlotMode", "PlotView", "compute_direction_field_bounds"]
