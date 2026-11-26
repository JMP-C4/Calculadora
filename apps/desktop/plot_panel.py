"""Panel de gráficas de la interfaz de escritorio.

Todas las series se obtienen de ``odecalc.plotting``; este módulo solo se
encarga de dibujarlas con Matplotlib/Tk y de avisar cuando una gráfica no es
posible para la ecuación actual.
"""

from __future__ import annotations

import tkinter as tk
from enum import Enum
from tkinter import ttk

import numpy as np
import sympy as sp
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from odecalc.models import SolveResult
from odecalc.plotting import (
    autonomous_rhs_from_result,
    direction_field,
    equilibrium_points,
    family_curves,
    family_expression_from_result,
    isoclines,
    phase_line,
    plot_bounds,
    rhs_from_result,
    singular_curves,
    solution_curve,
    tangency_points,
)
from odecalc.symbols import X, Y


class PlotMode(str, Enum):
    """Tipos de gráfica disponibles en el selector."""

    SOLUTION = "Solución y(x)"
    DIRECTION_FIELD = "Campo de direcciones"
    ISOCLINES = "Isoclinas"
    FAMILY = "Familia de curvas"
    PHASE_LINE = "Línea de fase"
    EQUILIBRIA = "Puntos de equilibrio"
    SURFACE = "Superficie 3D z = f(x,y)"


class PlotPanel(ttk.Frame):
    """Selector de gráfica y lienzo Matplotlib con avisos visibles."""

    def __init__(self, master: tk.Misc | None = None, **kwargs) -> None:
        super().__init__(master, **kwargs)
        self._result: SolveResult | None = None
        self._bounds: tuple[float, float] = (-5.0, 5.0)

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 6))
        ttk.Label(header, text="Tipo de gráfica:").pack(side="left", padx=(0, 6))
        self.mode_selector = ttk.Combobox(
            header,
            state="readonly",
            width=28,
            values=[mode.value for mode in PlotMode],
        )
        self.mode_selector.set(PlotMode.SOLUTION.value)
        self.mode_selector.pack(side="left")
        self.mode_selector.bind("<<ComboboxSelected>>", self._on_mode_selected)
        ttk.Button(header, text="Actualizar", command=self._draw).pack(
            side="left", padx=(8, 0)
        )
        self._tools_visible = False
        self.tools_button = ttk.Button(
            header,
            text="Herramientas",
            command=self._toggle_tools,
        )
        self.tools_button.pack(side="left", padx=(8, 0))

        self.notice = ttk.Label(
            self,
            text="",
            foreground="#b45309",
            justify="left",
        )
        self.notice.pack(fill="x", pady=(0, 4))
        self._notice_wrap = 0

        self.figure = Figure(figsize=(8.0, 5.0), dpi=100)
        self.axes = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.toolbar_frame = ttk.Frame(self)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
        self.toolbar.update()
        self.toolbar_frame.pack_forget()

        self.bind("<Configure>", self._ajustar_notice)
        self._show_axes_message("Resuelve una ecuación para ver su gráfica.")

    def _toggle_tools(self) -> None:
        self._tools_visible = not self._tools_visible
        if self._tools_visible:
            self.toolbar_frame.pack(fill="x")
            self.tools_button.configure(text="Ocultar herramientas")
        else:
            self.toolbar_frame.pack_forget()
            self.tools_button.configure(text="Herramientas")
        self.toolbar.update()

    def _ajustar_notice(self, event: object) -> None:
        if getattr(event, "widget", None) is not self:
            return
        ancho = max(int(getattr(event, "width", 0) or 0), self.winfo_width())
        if ancho <= 1:
            return
        envolver = max(240, ancho - 36)
        if envolver != self._notice_wrap:
            self.notice.configure(wraplength=envolver)
            self._notice_wrap = envolver

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def show_waiting(self) -> None:
        """Muestra un aviso mientras se resuelve la ecuación."""

        self._result = None
        self._show_axes_message("Calculando la solución…")

    def show_error(self, message: str) -> None:
        """Muestra un error de resolución en el panel de gráficas."""

        self._result = None
        self._fail(f"No se puede graficar: {message}")

    def show_result(
        self,
        result: SolveResult | None,
        *,
        x_min: float | None = None,
        x_max: float | None = None,
    ) -> None:
        """Dibuja el tipo de gráfica seleccionado para ``result``."""

        self._result = result
        if (
            x_min is not None
            and x_max is not None
            and np.isfinite(x_min)
            and np.isfinite(x_max)
            and x_min < x_max
        ):
            self._bounds = (float(x_min), float(x_max))
        self._draw()

    def draw_current(self) -> None:
        """Vuelve a dibujar con el resultado y el modo actuales."""

        self._draw()

    # ------------------------------------------------------------------
    # Selección de modo
    # ------------------------------------------------------------------
    def _on_mode_selected(self, _event=None) -> None:
        self._draw()

    def _draw(self) -> None:
        result = self._result
        if result is None:
            self._fail("Resuelve una ecuación para ver su gráfica.")
            return
        if getattr(result, "error", None):
            self._fail(f"No se puede graficar: {result.error}")
            return

        self.notice.configure(text="")
        mode = PlotMode(self.mode_selector.get())
        drawers = {
            PlotMode.SOLUTION: self._draw_solution,
            PlotMode.DIRECTION_FIELD: self._draw_direction_field,
            PlotMode.ISOCLINES: self._draw_isoclines,
            PlotMode.FAMILY: self._draw_family,
            PlotMode.PHASE_LINE: self._draw_phase_line,
            PlotMode.EQUILIBRIA: self._draw_equilibria,
            PlotMode.SURFACE: self._draw_surface,
        }
        try:
            drawers[mode](result)
        except Exception as exc:  # pragma: no cover - defensa de la UI
            self._fail(f"No se pudo graficar: {type(exc).__name__}: {exc}")
        self.canvas.draw_idle()
        self.toolbar.update()

    # ------------------------------------------------------------------
    # Utilidades de dibujo
    # ------------------------------------------------------------------
    def _reset_2d(self, *, title: str = "") -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(111)
        self.axes.grid(True, linestyle="--", alpha=0.35)
        self.axes.set_xlabel("$x$")
        self.axes.set_ylabel("$y$")
        if title:
            self.axes.set_title(title)

    def _reset_3d(self) -> None:
        self.figure.clear()
        self.axes = self.figure.add_subplot(111, projection="3d")
        self.axes.set_xlabel("$x$")
        self.axes.set_ylabel("$y$")
        self.axes.set_zlabel(r"$z = f(x, y)$")

    def _show_axes_message(self, message: str) -> None:
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
            wrap=True,
            transform=self.axes.transAxes,
            color="#666666",
        )
        self.notice.configure(text="")
        self.canvas.draw_idle()

    def _note(self, message: str) -> None:
        self.notice.configure(text=message)

    def _fail(self, message: str) -> None:
        self._show_axes_message(message)
        self.notice.configure(text=message)

    def _plot_bounds(self, result: SolveResult) -> tuple[float, float, float, float]:
        x_min, x_max = self._bounds
        return plot_bounds(result, x_min=x_min, x_max=x_max)

    def _rhs(self, result: SolveResult) -> tuple[sp.Expr | None, str | None]:
        return rhs_from_result(result)

    def _autonomous_rhs(self, result: SolveResult) -> tuple[sp.Expr | None, str | None]:
        return autonomous_rhs_from_result(result)

    def _family_expression(
        self, result: SolveResult
    ) -> tuple[sp.Expr | None, str | None]:
        return family_expression_from_result(result)

    # ------------------------------------------------------------------
    # Tipos de gráfica
    # ------------------------------------------------------------------
    def _plot_singular(self, result: SolveResult) -> bool:
        """Dibuja la envolvente singular y los puntos de tangencia."""

        x_min, x_max, _, _ = self._plot_bounds(result)
        curvas = singular_curves(result, x_min=x_min, x_max=x_max)
        puntos = tangency_points(result, x_min=x_min, x_max=x_max)
        for curva in curvas:
            self.axes.plot(
                curva["x"],
                curva["y"],
                color="#7c3aed",
                linewidth=2.8,
                linestyle="--",
                label=curva["label"],
                zorder=4,
            )
        for punto in puntos:
            self.axes.scatter(
                [punto["x"]],
                [punto["y"]],
                color="#b45309",
                marker="D",
                s=70,
                zorder=6,
                label=punto["label"],
            )
            self.axes.annotate(
                punto["label"],
                (punto["x"], punto["y"]),
                textcoords="offset points",
                xytext=(8, 8),
                fontsize=8,
                color="#b45309",
            )
        return bool(curvas or puntos)

    def _draw_solution(self, result: SolveResult) -> None:
        self._reset_2d(title=r"Solución de la EDO $y(x)$")
        x_min, x_max, _y_min, _y_max = self._plot_bounds(result)
        curve = solution_curve(result, x_min=x_min, x_max=x_max)
        if curve is not None and len(curve["x"]):
            self.axes.plot(
                curve["x"],
                curve["y"],
                color="#1565c0",
                linewidth=2,
                label=r"Solución $y(x)$",
            )
            self._plot_singular(result)
            self.axes.legend(loc="best", fontsize=9)
            self.figure.tight_layout()
            return

        # Sin PVI ni curva numérica: se muestra la familia general si es
        # explícita (o despejable), en lugar de dejar la gráfica vacía.
        expression, note = self._family_expression(result)
        if expression is None:
            self._fail(
                note
                or "No hay solución particular explícita ni curva numérica para graficar."
            )
            return
        self._plot_family_expression(
            expression, title="Familia de soluciones", result=result
        )
        self._note(
            "No hay una solución particular explícita; se muestra la familia "
            "general. Selecciona «Familia de curvas» para verla con más detalle."
        )
        if note:
            self.notice.configure(text=f"{self.notice.cget('text')} {note}")

    def _draw_direction_field(self, result: SolveResult) -> None:
        rhs, note = self._rhs(result)
        if rhs is None:
            self._fail(note or "No se pudo obtener y' para el campo de direcciones.")
            return

        x_min, x_max, y_min, y_max = self._plot_bounds(result)
        data = direction_field(
            rhs,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            density=21,
        )
        mask = np.isfinite(data["u"]) & np.isfinite(data["v"])
        if not np.any(mask):
            self._fail("No se pudo evaluar el campo de direcciones en el intervalo.")
            return

        self._reset_2d(title=r"Campo de direcciones ($\frac{dy}{dx} = f(x, y)$)")
        self.axes.quiver(
            data["x"][mask],
            data["y"][mask],
            data["u"][mask],
            data["v"][mask],
            color="#455a64",
            angles="xy",
            pivot="mid",
            width=0.002,
        )
        curve = solution_curve(result, x_min=x_min, x_max=x_max)
        if curve is not None and len(curve["x"]):
            self.axes.plot(
                curve["x"],
                curve["y"],
                color="#d84315",
                linewidth=2,
                label=r"Solución $y(x)$",
            )
        self._plot_singular(result)
        if self.axes.get_legend_handles_labels()[0]:
            self.axes.legend(loc="best", fontsize=9)
        self.axes.set_xlim(x_min, x_max)
        self.axes.set_ylim(y_min, y_max)
        self.figure.tight_layout()
        if note:
            self._note(note)
        if not np.all(mask):
            aviso = (
                "Hay zonas sin pendiente real (por ejemplo, por encima de la "
                "envolvente); se omiten en el campo."
            )
            self.notice.configure(
                text=f"{self.notice.cget('text')} {aviso}".strip()
            )

    def _draw_isoclines(self, result: SolveResult) -> None:
        rhs, note = self._rhs(result)
        if rhs is None:
            self._fail(note or "No se pudo obtener y' para calcular las isoclinas.")
            return

        x_min, x_max, y_min, y_max = self._plot_bounds(result)
        lines = isoclines(
            rhs,
            levels=(-1.0, 0.0, 1.0),
            x_min=x_min,
            x_max=x_max,
        )
        if not lines:
            self._fail(
                "No se pudieron calcular isoclinas reales para esta ecuación "
                "en el intervalo indicado."
            )
            return

        self._reset_2d(title=r"Isoclinas $f(x, y) = k$")
        for line in lines:
            self.axes.plot(
                line["x"],
                line["y"],
                linewidth=1.6,
                label=f"$k = {line['level']:g}$",
            )
        self.axes.set_xlim(x_min, x_max)
        self.axes.set_ylim(y_min, y_max)
        self.axes.legend(loc="best", fontsize=9)
        self.figure.tight_layout()
        if note:
            self._note(note)

    def _plot_family_expression(
        self,
        expression: sp.Expr,
        *,
        title: str,
        result: SolveResult | None = None,
    ) -> bool:
        x_min, x_max = self._bounds
        constants = [
            symbol for symbol in expression.free_symbols if symbol not in {X, Y}
        ]
        plotted = False
        if not constants:
            curves = family_curves(
                expression,
                constants=(0.0,),
                x_min=x_min,
                x_max=x_max,
            )
            if curves:
                self.axes.plot(
                    curves[0]["x"],
                    curves[0]["y"],
                    linewidth=1.8,
                    label="Solución general",
                )
                plotted = True
        else:
            colors = (
                "#1565c0",
                "#2e7d32",
                "#6a1b9a",
                "#ef6c00",
                "#00838f",
                "#b5651d",
                "#3949ab",
            )
            for value, color in zip(
                (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0), colors
            ):
                curves = family_curves(
                    expression,
                    constants=(value,),
                    x_min=x_min,
                    x_max=x_max,
                )
                if not curves:
                    continue
                self.axes.plot(
                    curves[0]["x"],
                    curves[0]["y"],
                    color=color,
                    linewidth=1.5,
                    alpha=0.9,
                    label=f"C = {value:g}",
                )
                plotted = True
        if result is not None:
            plotted = self._plot_singular(result) or plotted
        if plotted:
            self.axes.set_title(title)
            self.axes.legend(loc="best", fontsize=9)
            self.figure.tight_layout()
        return plotted

    def _draw_family(self, result: SolveResult) -> None:
        expression, note = self._family_expression(result)
        if expression is None:
            self._fail(note or "No hay una familia de curvas para graficar.")
            return
        self._reset_2d()
        if not self._plot_family_expression(
            expression, title="Familia de curvas", result=result
        ):
            self._fail(
                "La expresión de la familia no se pudo evaluar en el intervalo."
            )
            return
        if note:
            self._note(note)

    def _draw_phase_line(self, result: SolveResult) -> None:
        rhs, note = self._autonomous_rhs(result)
        if rhs is None:
            self._fail(note or "No se pudo obtener f(y) para la línea de fase.")
            return

        _, _, y_min, y_max = self._plot_bounds(result)
        data = phase_line(rhs, y_min=y_min, y_max=y_max)
        mask = np.isfinite(data["f(y)"])
        if not np.any(mask):
            self._fail("No se pudo evaluar f(y) en el intervalo de la línea de fase.")
            return

        self._reset_2d(title=r"Línea de fase ($\frac{dy}{dx} = f(y)$)")
        self.axes.plot(
            data["y"][mask],
            data["f(y)"][mask],
            color="#1565c0",
            linewidth=2,
        )
        self.axes.axhline(0.0, color="#616161", linewidth=1, linestyle="--")
        self.axes.set_xlabel("$y$")
        self.axes.set_ylabel("$f(y)$")
        self.figure.tight_layout()
        if note:
            self._note(note)

    def _draw_equilibria(self, result: SolveResult) -> None:
        rhs, note = self._autonomous_rhs(result)
        if rhs is None:
            self._fail(
                note or "No se pudo obtener f(y) para los puntos de equilibrio."
            )
            return

        points = equilibrium_points(rhs)
        if not points:
            self._fail(
                "No se encontraron puntos de equilibrio reales para esta EDO "
                "autónoma en el intervalo."
            )
            return

        _, _, y_min, y_max = self._plot_bounds(result)
        equilibrium_y = [point["y"] for point in points]
        y_min = min(y_min, min(equilibrium_y) - 1.0)
        y_max = max(y_max, max(equilibrium_y) + 1.0)
        data = phase_line(rhs, y_min=y_min, y_max=y_max)
        mask = np.isfinite(data["f(y)"])

        self._reset_2d(title=r"Puntos de equilibrio ($f(y) = 0$)")
        if np.any(mask):
            self.axes.plot(
                data["y"][mask],
                data["f(y)"][mask],
                color="#90a4ae",
                linewidth=1.5,
                label="$f(y)$",
            )
        colors = {
            "asintóticamente estable": "#2e7d32",
            "inestable": "#c62828",
        }
        for point in points:
            color = colors.get(point["stability"], "#6a1b9a")
            self.axes.scatter(
                [point["y"]],
                [0.0],
                color=color,
                s=80,
                zorder=5,
            )
            self.axes.annotate(
                f"$y = {point['y']:g}$\n{point['stability']}",
                (point["y"], 0.0),
                textcoords="offset points",
                xytext=(8, 10),
                fontsize=8,
                color=color,
            )
        self.axes.axhline(0.0, color="#616161", linewidth=1, linestyle="--")
        self.axes.set_xlabel("$y$")
        self.axes.set_ylabel("$f(y)$")
        self.axes.legend(loc="best", fontsize=9)
        self.figure.tight_layout()
        if note:
            self._note(note)

    def _draw_surface(self, result: SolveResult) -> None:
        rhs, note = self._rhs(result)
        if rhs is None:
            self._fail(note or "No se pudo obtener f(x, y) para la superficie.")
            return

        x_min, x_max, y_min, y_max = self._plot_bounds(result)
        self._reset_3d()
        grid_size = 50
        x_values = np.linspace(x_min, x_max, grid_size)
        y_values = np.linspace(y_min, y_max, grid_size)
        grid_x, grid_y = np.meshgrid(x_values, y_values)
        try:
            function = sp.lambdify((X, Y), rhs, modules=["numpy"])
            with np.errstate(all="ignore"):
                z_values = np.asarray(function(grid_x, grid_y), dtype=float)
            z_values = np.broadcast_to(z_values, grid_x.shape).astype(float)
        except Exception as exc:
            self._fail(f"No se pudo evaluar f(x, y) para la superficie: {exc}")
            return
        if not np.any(np.isfinite(z_values)):
            self._fail("La superficie no tiene valores finitos en el intervalo.")
            return
        z_values = np.where(np.isfinite(z_values), z_values, np.nan)

        surface = self.axes.plot_surface(
            grid_x,
            grid_y,
            z_values,
            cmap="viridis",
            linewidth=0,
            antialiased=True,
        )
        self.axes.set_title(r"Superficie $z = f(x, y)$")
        self.figure.colorbar(surface, ax=self.axes, shrink=0.65, pad=0.08)
        self.figure.tight_layout()
        if note:
            self._note(note)


__all__ = ["PlotMode", "PlotPanel"]
