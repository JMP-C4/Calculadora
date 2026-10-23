"""Tests de integración del controlador principal."""

from __future__ import annotations

import time

import pytest

from app import App
from ui.condition_panel import SolverConditions
from ui.plot_view import PlotMode


@pytest.fixture
def app():
    try:
        application = App()
    except Exception as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"No se pudo crear la ventana: {exc}")
    application.withdraw()
    yield application
    application.destroy()


def _wait_until(application: App, predicate, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.update()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_app_initial_state(app):
    assert app.state.current_equation_text == ""
    assert app.state.symbolic_result is None
    assert app.state.numeric_result is None
    assert app.wm_minsize() == (1024, 768)


def test_equation_change_updates_parse_state(app):
    app.equation_input.set_text("dy/dx = x + y")

    assert app.state.last_parse_result is not None
    assert app.state.last_parse_result.error is None
    assert app.state.last_parse_result.rhs is not None
    assert "x + y" in app.math_preview.current_latex
    assert "válida" in app.status_bar.message.lower()


def test_invalid_equation_shows_error(app):
    app.equation_input.set_text("dy/dx = x + z")

    assert app.state.last_parse_result is not None
    assert app.state.last_parse_result.error is not None
    assert app.status_bar.level_style.startswith("Error")


def test_symbolic_solution_flow(app):
    app.equation_input.set_text("dy/dx = y")

    app._on_solve_symbolic()

    assert _wait_until(
        app, lambda: app.state.symbolic_result is not None and not app._busy
    )
    symbolic = app.state.symbolic_result
    assert symbolic is not None
    assert symbolic.error is None
    assert symbolic.general_solution is not None
    assert app.step_panel.ascii_text
    assert app.plot_view.axes.lines


def test_particular_solution_flow(app):
    app.condition_panel.set_conditions(SolverConditions(0.0, 1.0, -2.0, 2.0))
    app.equation_input.set_text("dy/dx = y")

    app._on_solve_symbolic()

    assert _wait_until(
        app, lambda: app.state.symbolic_result is not None and not app._busy
    )
    symbolic = app.state.symbolic_result
    assert symbolic is not None
    assert symbolic.particular_solution is not None
    assert "e" in app.math_preview.current_latex


def test_numeric_solution_flow(app):
    app.condition_panel.set_conditions(SolverConditions(0.0, 1.0, 0.0, 2.0))
    app.equation_input.set_text("dy/dx = y")

    app._on_solve_numeric()

    assert _wait_until(
        app, lambda: app.state.numeric_result is not None and not app._busy
    )
    numeric = app.state.numeric_result
    assert numeric is not None
    assert numeric.success is True
    assert len(numeric.x_arr) >= 500
    assert "numérica" in app.plot_view.axes.lines[0].get_label().lower()


def test_numeric_requires_initial_conditions(app):
    app.equation_input.set_text("dy/dx = y")

    app._on_solve_numeric()

    assert app.state.numeric_result is None
    assert "x₀" in app.status_bar.message


def test_loading_exercise_updates_input_and_conditions(app):
    exercise = app.exercise_library._by_id["sep-01"]

    app._on_exercise_selected(exercise)

    assert app.equation_input.get_text() == "dy/dx = y"
    conditions = app.condition_panel.get_conditions()
    assert conditions.x0 == 0.0
    assert conditions.y0 == 1.0
    assert "sep-01" not in app.status_bar.message


def test_mode_changes_dispatch_plots(app):
    app.condition_panel.set_conditions(SolverConditions(0.0, 1.0, 0.0, 2.0))
    app.equation_input.set_text("dy/dx = y")
    app._on_solve_numeric()
    assert _wait_until(
        app, lambda: app.state.numeric_result is not None and not app._busy
    )

    app._on_mode_changed(PlotMode.DIRECTION_FIELD)
    assert app.plot_view.axes.get_title() == "Campo de direcciones"

    app._on_mode_changed(PlotMode.SURFACE_3D)
    assert app.plot_view.axes.name == "3d"

    app._on_mode_changed(PlotMode.SOLUTION)
    assert app.plot_view.axes.get_xlabel() == "x"


def test_global_shortcut_inserts_token(app):
    app._insert_global("pi", False)

    assert "pi" in app.equation_input.get_text()


def test_spinner_is_deferred_until_operation_is_slow(app):
    app._set_busy(True, "Calculando…")

    assert app.status_bar.spinner.winfo_manager() == ""
    assert _wait_until(
        app,
        lambda: bool(app.status_bar.spinner.winfo_manager()),
        timeout=3.0,
    )

    app._set_busy(False)
    assert app.status_bar.spinner.winfo_manager() == ""
