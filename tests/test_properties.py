"""Tests de propiedades (Hypothesis) de ODE Calculator."""

from __future__ import annotations

import tkinter as tk

import pytest
import sympy as sp
from hypothesis import HealthCheck, given, settings, strategies as st

from data.exercises import load_exercises
from math_engine.numeric_solver import solve_numeric
from math_engine.parser import parse_ode
from math_engine.symbolic_solver import solve_symbolic, x, y
from tests.conftest import (
    SHORTCUT_MAP,
    invalid_ode_texts,
    numeric_odes,
    solvable_odes,
    valid_ode_texts,
    valid_rhs_exprs,
)
from ui.condition_panel import SolverConditions
from ui.equation_input import EquationInput
from ui.plot_view import PlotView, compute_direction_field_bounds

PROPERTY_SETTINGS = settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)


@pytest.fixture(scope="module")
def tk_root():
    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture(scope="module")
def equation_field(tk_root):
    return EquationInput(tk_root)


@pytest.fixture(scope="module")
def plot_view(tk_root):
    return PlotView(tk_root)


@PROPERTY_SETTINGS
@given(ode=valid_ode_texts)
def test_property_1_parse_roundtrip(ode):
    # Feature: ode-calculator, Property 1: Round-trip de parsing y renderizado LaTeX
    result = parse_ode(ode)

    assert result.error is None
    assert result.rhs is not None
    assert result.latex_str


@PROPERTY_SETTINGS
@given(ode=invalid_ode_texts)
def test_property_2_invalid_input_rejected(ode):
    # Feature: ode-calculator, Property 2: Rechazo de entradas inválidas
    result = parse_ode(ode)

    assert result.rhs is None
    assert result.error is not None


@PROPERTY_SETTINGS
@given(ode=solvable_odes)
def test_property_3_symbolic_solution_satisfies_ode(ode):
    # Feature: ode-calculator, Property 3: Solución simbólica satisface la EDO original
    rhs, _ode_type = ode
    result = solve_symbolic(rhs)

    assert result.general_solution is not None
    residual = (rhs - sp.diff(result.general_solution.rhs, x)).subs(
        y, result.general_solution.rhs
    )
    assert sp.simplify(residual) == 0


@PROPERTY_SETTINGS
@given(
    ode=solvable_odes,
    x0=st.floats(
        -3.0, 3.0, allow_nan=False, allow_infinity=False
    ).filter(lambda value: abs(value) >= 0.5),
    y0=st.floats(
        -3.0, 3.0, allow_nan=False, allow_infinity=False
    ),
)
def test_property_4_particular_solution_satisfies_ic(ode, x0, y0):
    # Feature: ode-calculator, Property 4: Solución particular satisface condiciones iniciales
    rhs, _ode_type = ode
    conditions = SolverConditions(x0=x0, y0=y0, x_min=-5.0, x_max=5.0)

    result = solve_symbolic(rhs, conditions)

    assert result.error is None
    assert result.particular_solution is not None
    value = complex(sp.N(result.particular_solution.rhs.subs(x, x0)))
    assert abs(value - y0) < 1e-6


@PROPERTY_SETTINGS
@given(ode=numeric_odes)
def test_property_5_numeric_solution_coverage_and_ic(ode):
    # Feature: ode-calculator, Property 5: Solución numérica y cobertura mínima de puntos
    rhs, x0, y0, x_min, x_max = ode
    conditions = SolverConditions(x0=x0, y0=y0, x_min=x_min, x_max=x_max)

    result = solve_numeric(rhs, conditions)

    assert result.success is True
    assert result.x_arr is not None
    assert result.y_arr is not None
    assert len(result.x_arr) >= 500
    assert abs(float(result.x_arr[0]) - x0) < 1e-9
    assert abs(float(result.y_arr[0]) - y0) < 1e-6


@PROPERTY_SETTINGS
@given(exercise=st.sampled_from(load_exercises()))
def test_property_6_exercise_catalog_integrity(exercise):
    # Feature: ode-calculator, Property 6: Integridad del catálogo de ejercicios
    exercises = load_exercises()

    assert len(exercises) >= 15
    assert exercise.name
    assert exercise.latex_str
    assert exercise.description
    result = parse_ode(exercise.equation_text)
    assert result.error is None


@PROPERTY_SETTINGS
@given(shortcut=st.sampled_from(list(SHORTCUT_MAP.items())))
def test_property_7_shortcut_inserts_token(equation_field, shortcut):
    # Feature: ode-calculator, Property 7: Inserción de tokens mediante atajos de teclado
    _key, (token, cursor_inside) = shortcut
    equation_field.set_text("")

    equation_field.insert_token(token, place_cursor_inside=cursor_inside)

    text = equation_field.get_text()
    assert token.replace("()", "") in text
    if cursor_inside:
        expected = text.index("(") + 1
        assert equation_field.get_cursor_position() == expected


@PROPERTY_SETTINGS
@given(rhs=valid_rhs_exprs)
def test_property_8_direction_field_default_interval(rhs):
    # Feature: ode-calculator, Property 8: Direction Field usa intervalo por defecto cuando faltan condiciones
    bounds = compute_direction_field_bounds(rhs, SolverConditions())

    assert bounds == (-5.0, 5.0, -5.0, 5.0)


@PROPERTY_SETTINGS
@given(rhs=valid_rhs_exprs)
def test_property_9_surface_3d_resolution_and_labels(plot_view, rhs):
    # Feature: ode-calculator, Property 9: Resolución mínima y etiquetas en visualizaciones
    conditions = SolverConditions(
        x0=1.0,
        y0=1.0,
        x_min=0.5,
        x_max=2.0,
        y_min=-5.0,
        y_max=5.0,
    )

    numeric = solve_numeric(rhs, conditions)
    plot_view.plot_solution(None, numeric, conditions)
    assert plot_view.axes.get_xlabel()
    assert plot_view.axes.get_ylabel()

    plot_view.plot_direction_field(rhs, conditions)
    assert plot_view.axes.get_xlabel()
    assert plot_view.axes.get_ylabel()

    plot_view.plot_surface_3d(rhs, conditions)
    assert plot_view.last_surface_shape is not None
    assert plot_view.last_surface_shape[0] >= 50
    assert plot_view.last_surface_shape[1] >= 50
    assert plot_view.axes.get_xlabel()
    assert plot_view.axes.get_ylabel()
    assert plot_view.axes.get_zlabel()
