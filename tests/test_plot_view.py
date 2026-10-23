"""Tests unitarios de la vista de gráficas."""

from __future__ import annotations

import tkinter as tk

import pytest

from math_engine.numeric_solver import solve_numeric
from math_engine.symbolic_solver import solve_symbolic, x, y
from ui.condition_panel import SolverConditions
from ui.plot_view import PlotMode, PlotView, compute_direction_field_bounds


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_default_direction_field_bounds():
    assert compute_direction_field_bounds(x + y, SolverConditions()) == (
        -5.0,
        5.0,
        -5.0,
        5.0,
    )


def test_custom_direction_field_bounds():
    conditions = SolverConditions(0.0, 1.0, -2.0, 3.0, -4.0, 4.0)

    assert compute_direction_field_bounds(x + y, conditions) == (-2.0, 3.0, -4.0, 4.0)


def test_plot_numeric_solution(root):
    view = PlotView(root)
    conditions = SolverConditions(0.0, 1.0, 0.0, 2.0)
    numeric = solve_numeric(y, conditions)

    view.plot_solution(None, numeric, conditions)

    labels = [line.get_label() for line in view.axes.lines]
    assert "Solución numérica" in labels
    assert view.axes.get_xlabel() == "x"
    assert view.axes.get_ylabel() == "y"


def test_plot_symbolic_family(root):
    view = PlotView(root)
    conditions = SolverConditions(None, None, -2.0, 2.0)
    symbolic = solve_symbolic(y)

    view.plot_solution(symbolic, None, conditions)

    assert len(view.axes.lines) >= 2
    assert view.axes.get_title() == "Solución de la EDO"


def test_plot_particular_solution(root):
    view = PlotView(root)
    conditions = SolverConditions(0.0, 1.0, -2.0, 2.0)
    symbolic = solve_symbolic(y, conditions)

    view.plot_solution(symbolic, None, conditions)

    labels = [line.get_label() for line in view.axes.lines]
    assert "Solución particular" in labels


def test_plot_direction_field_with_curve(root):
    view = PlotView(root)
    conditions = SolverConditions(0.0, 1.0, -2.0, 2.0)
    numeric = solve_numeric(y, conditions)

    view.plot_direction_field(y, conditions, solution_curve=numeric)

    assert view.axes.get_title() == "Campo de direcciones"
    assert len(view.axes.collections) >= 1
    assert "Solución numérica" in [line.get_label() for line in view.axes.lines]


def test_plot_surface_and_views(root):
    view = PlotView(root)
    conditions = SolverConditions(0.0, 1.0, -2.0, 2.0, -2.0, 2.0)

    view.plot_surface_3d(x + y, conditions)

    assert view.axes.name == "3d"
    assert view.axes.get_zlabel() == "z = f(x, y)"
    assert len(view.axes.collections) >= 1

    view.set_3d_view(30, 45)
    assert view.axes.elev == 30
    assert view.axes.azim == 45


def test_mode_selector_notifies_callback(root):
    view = PlotView(root)
    received: list[PlotMode] = []
    view.on_mode_change = received.append

    view.mode_selector.set(PlotMode.SURFACE_3D.value)
    view._on_mode_selected()

    assert view.current_mode == PlotMode.SURFACE_3D
    assert received == [PlotMode.SURFACE_3D]
    assert view.view_buttons.winfo_manager() != ""


def test_export_button_reports_saved_path(root, monkeypatch, tmp_path):
    target = tmp_path / "grafica.png"
    monkeypatch.setattr(
        "ui.plot_view.export_figure",
        lambda figure, parent=None: (str(target), None),
    )
    view = PlotView(root)
    messages = []
    view.on_export_status = lambda message, level: messages.append((message, level))

    view.export_button.invoke()

    assert messages
    message, level = messages[-1]
    assert str(target) in message
    assert level == "info"


def test_export_button_reports_error(root, monkeypatch):
    monkeypatch.setattr(
        "ui.plot_view.export_figure",
        lambda figure, parent=None: (None, "Pillow no está instalado."),
    )
    view = PlotView(root)
    messages = []
    view.on_export_status = lambda message, level: messages.append((message, level))

    view.export_button.invoke()

    assert messages[-1] == ("Pillow no está instalado.", "error")
