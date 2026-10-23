"""Tests unitarios del solver simbólico."""

from __future__ import annotations

from types import SimpleNamespace

import sympy as sp

from math_engine.symbolic_solver import solve_symbolic, x, y


def _conditions(x0=0.0, y0=1.0, x_min=-5.0, x_max=5.0):
    return SimpleNamespace(
        x0=x0,
        y0=y0,
        x_min=x_min,
        x_max=x_max,
        y_min=None,
        y_max=None,
    )


def test_exponential_growth_general_solution():
    result = solve_symbolic(y)

    assert result.error is None
    assert result.general_solution is not None
    c1 = sp.Symbol("C1")
    assert sp.simplify(result.general_solution.rhs - c1 * sp.exp(x)) == 0


def test_linear_general_solution():
    result = solve_symbolic(x)

    assert result.error is None
    assert result.general_solution is not None
    c1 = sp.Symbol("C1")
    assert sp.simplify(result.general_solution.rhs - (x**2 / 2 + c1)) == 0


def test_particular_solution_uses_initial_conditions():
    result = solve_symbolic(y, _conditions(0.0, 1.0))

    assert result.error is None
    assert result.particular_solution is not None
    assert sp.simplify(result.particular_solution.rhs - sp.exp(x)) == 0
    assert result.latex_particular


def test_unsolvable_equation_populates_error():
    result = solve_symbolic(sp.sin(y) - x)

    assert result.general_solution is None
    assert result.error is not None
    assert result.step_by_step is not None
    assert result.step_by_step.steps


def test_ode_type_is_detected():
    expected = {
        y: "separable",
        x + y: "linear",
        y / x: "homogeneous",
        y**2 - y: "bernoulli",
        -(2 * x + y) / (x + 2 * y): "exact",
    }

    for rhs, ode_type in expected.items():
        result = solve_symbolic(rhs)
        assert result.ode_type == ode_type
        assert result.general_solution is not None


def test_step_by_step_always_present_on_success():
    result = solve_symbolic(x * y)

    assert result.step_by_step is not None
    assert len(result.step_by_step.steps) >= 2
    assert result.step_by_step.ascii_text
