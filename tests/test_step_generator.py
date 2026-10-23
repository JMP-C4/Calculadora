"""Tests unitarios del generador de pasos."""

from __future__ import annotations

from types import SimpleNamespace

import sympy as sp

from math_engine.step_generator import classify_ode, generate_steps
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


def test_separable_has_identification_step():
    result = generate_steps(y, solve_symbolic(y))

    assert result.steps
    assert result.ode_type == "separable"
    assert "identificar" in result.steps[0].operation.lower()
    assert "tipo" in result.steps[0].operation.lower()


def test_linear_includes_integrating_factor_step():
    result = generate_steps(x + y, solve_symbolic(x + y))

    operations = " ".join(step.operation.lower() for step in result.steps)
    assert "factor integrante" in operations
    assert len(result.steps) >= 4


def test_all_steps_have_latex_and_justification():
    equations = (y, x + y, y / x, y**2 - y, -(2 * x + y) / (x + 2 * y))

    for rhs in equations:
        result = generate_steps(rhs, solve_symbolic(rhs))
        assert result.steps
        for step in result.steps:
            assert step.latex_expr.strip()
            assert step.justification.strip()


def test_ascii_text_contains_step_numbers():
    result = generate_steps(x * y, solve_symbolic(x * y))

    assert result.ascii_text
    assert "Paso 1" in result.ascii_text
    assert "Paso 2" in result.ascii_text


def test_conditions_are_applied():
    conditions = _conditions(0.0, 1.0)
    symbolic = solve_symbolic(y, conditions)
    result = generate_steps(y, symbolic, conditions=conditions)

    operations = " ".join(step.operation.lower() for step in result.steps)
    assert "inicial" in operations


def test_numeric_steps_when_symbolic_fails():
    conditions = _conditions(0.0, 1.0, 0.0, 2.0)
    rhs = sp.sin(y) - x
    symbolic = solve_symbolic(rhs, conditions)

    from math_engine.numeric_solver import solve_numeric

    numeric = solve_numeric(rhs, conditions)
    result = generate_steps(
        rhs,
        symbolic_result=symbolic,
        conditions=conditions,
        numeric_result=numeric,
    )

    assert result.ode_type == "numeric"
    operations = " ".join(step.operation.lower() for step in result.steps)
    assert "numérico" in operations
    assert "discretizar" in operations


def test_classification_covers_expected_types():
    expected = {
        y: "separable",
        x: "linear",
        x + y: "linear",
        y / x: "homogeneous",
        y**2 - y: "bernoulli",
        -(2 * x + y) / (x + 2 * y): "exact",
    }

    for rhs, ode_type in expected.items():
        assert classify_ode(rhs) == ode_type
