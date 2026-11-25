"""Pruebas del selector de gráficas de la interfaz de escritorio."""

from __future__ import annotations

import tkinter as tk

import pytest
import sympy as sp

pytest.importorskip("tkinter")
pytest.importorskip("matplotlib")

from apps.desktop.plot_panel import PlotMode, PlotPanel  # noqa: E402
from odecalc.models import Solution, SolveResult  # noqa: E402
from odecalc.symbols import C, X  # noqa: E402


@pytest.fixture
def panel():
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    root.withdraw()
    widget = PlotPanel(root)
    widget.pack()
    yield widget
    root.destroy()


def _solution_result() -> SolveResult:
    return SolveResult(
        input_text="y' = y",
        general=Solution(form="explicit", expr=C * sp.exp(X), constant=C),
        particular=Solution(form="explicit", expr=sp.exp(X)),
    )


def _autonomous_result() -> SolveResult:
    return SolveResult(input_text="y' = y*(1-y)")


def _select(panel: PlotPanel, mode: PlotMode) -> None:
    panel.mode_selector.set(mode.value)
    panel._on_mode_selected()


def test_selector_lists_every_mode(panel: PlotPanel) -> None:
    values = panel.mode_selector.cget("values")
    assert tuple(values) == tuple(mode.value for mode in PlotMode)
    assert panel.mode_selector.get() == PlotMode.SOLUTION.value


def test_solution_mode_plots_curve(panel: PlotPanel) -> None:
    panel.show_result(_solution_result(), x_min=-2, x_max=2)
    assert panel.axes.lines
    assert panel.notice.cget("text") == ""


def test_direction_field_plots_quiver_and_solution(panel: PlotPanel) -> None:
    _select(panel, PlotMode.DIRECTION_FIELD)
    panel.show_result(_solution_result(), x_min=-2, x_max=2)
    assert panel.axes.collections
    assert panel.axes.lines  # curva solución superpuesta


def test_isoclines_plot_each_level(panel: PlotPanel) -> None:
    _select(panel, PlotMode.ISOCLINES)
    panel.show_result(SolveResult(input_text="y' = x + y"))
    assert len(panel.axes.lines) == 3
    assert panel.notice.cget("text") == ""


def test_family_mode_plots_five_curves(panel: PlotPanel) -> None:
    _select(panel, PlotMode.FAMILY)
    panel.show_result(_solution_result(), x_min=-1, x_max=1)
    assert len(panel.axes.lines) == 5
    assert panel.notice.cget("text") == ""


def test_phase_line_is_plotted_for_autonomous_ode(panel: PlotPanel) -> None:
    _select(panel, PlotMode.PHASE_LINE)
    panel.show_result(_autonomous_result())
    assert panel.axes.lines
    assert panel.axes.get_xlabel() == "y"


def test_equilibria_marks_points(panel: PlotPanel) -> None:
    _select(panel, PlotMode.EQUILIBRIA)
    panel.show_result(_autonomous_result())
    assert panel.axes.collections
    assert panel.notice.cget("text") == ""


def test_surface_is_3d(panel: PlotPanel) -> None:
    _select(panel, PlotMode.SURFACE)
    panel.show_result(SolveResult(input_text="y' = x + y"))
    assert panel.axes.name == "3d"
    assert panel.axes.collections


def test_non_autonomous_phase_line_shows_notice(panel: PlotPanel) -> None:
    _select(panel, PlotMode.PHASE_LINE)
    panel.show_result(SolveResult(input_text="y' = x + y"))
    assert "autónomas" in panel.notice.cget("text")


def test_non_autonomous_equilibria_shows_notice(panel: PlotPanel) -> None:
    _select(panel, PlotMode.EQUILIBRIA)
    panel.show_result(SolveResult(input_text="y' = x + y"))
    assert "autónomas" in panel.notice.cget("text")


def test_implicit_clairaut_can_draw_direction_field(panel: PlotPanel) -> None:
    _select(panel, PlotMode.DIRECTION_FIELD)
    panel.show_result(SolveResult(input_text="y = x*y' + y'**2"))
    assert panel.axes.collections
    assert "varias ramas" in panel.notice.cget("text")


def test_no_result_shows_notice(panel: PlotPanel) -> None:
    panel.show_result(None)
    assert "Resuelve una ecuación" in panel.notice.cget("text")


def test_error_result_shows_notice(panel: PlotPanel) -> None:
    panel.show_result(SolveResult(input_text="no es una edo", error="Sintaxis inválida"))
    assert "No se puede graficar" in panel.notice.cget("text")
    assert "Sintaxis inválida" in panel.notice.cget("text")


def test_implicit_family_without_explicit_branch_shows_notice(panel: PlotPanel) -> None:
    _select(panel, PlotMode.FAMILY)
    result = SolveResult(
        input_text="y' = y",
        general=Solution(form="implicit", expr=sp.sin(X) * sp.sin(C), value=C),
    )
    panel.show_result(result)
    assert panel.notice.cget("text")
