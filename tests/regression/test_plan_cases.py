"""Los nueve casos de regresión obligatorios del plan (sección 2.2)."""

from __future__ import annotations

import sympy as sp
import pytest

from odecalc.api import solve
from odecalc.symbols import C, X, Y

CASES = [
    ("y' = -(2*x*y+1)/(x**2+3*y**2)", "exact"),
    ("y' = y**2 - x*y + 1", "riccati"),
    ("y' = (x+y)**2", "substitution_linear_combo"),
    ("y' = exp(-x**2)*y + 1", "linear"),
    ("y' = y/x + sqrt(y)", "bernoulli"),
    ("y' = -(x**2+y**2+x)/(x*y)", "integrating_factor_x"),
    ("y' = -(y)/(2*x*y - exp(-2*y))", "integrating_factor_y"),
    ("y' = (x+y+1)/(x-y-3)", "reducible_homogeneous"),
    ("y = x*y' + y'**2", "clairaut"),
]


@pytest.mark.parametrize("equation, expected_method", CASES)
def test_plan_case_solves_and_verifies(equation: str, expected_method: str) -> None:
    result = solve(equation, compute_numeric=False)
    assert result.error is None, result.warnings
    assert result.general is not None
    assert result.verification is not None
    assert result.verification.status == "ok"
    assert expected_method in {match.method for match in result.classifications}
    assert result.chosen_method == expected_method
    assert result.steps


def test_case_1_exact_solution_matches_book() -> None:
    result = solve("y' = -(2*x*y+1)/(x**2+3*y**2)")
    expected = X**2 * Y + X + Y**3
    assert result.general is not None
    # La solución es implícita y puede diferir en una constante aditiva.
    assert sp.simplify(result.general.expr - expected) == 0


def test_case_3_returns_tangent_solution() -> None:
    result = solve("y' = (x+y)**2")
    assert result.general is not None
    assert result.general.latex
    assert sp.simplify(result.general.expr - (sp.tan(X + C) - X)) == 0


def test_case_4_has_no_y_inside_unresolved_integral() -> None:
    result = solve("y' = exp(-x**2)*y + 1")
    assert result.general is not None
    assert not result.general.expr.has(Y)
    for integral in result.general.expr.atoms(sp.Integral):
        assert not integral.args[0].has(Y)


def test_case_8_is_implicit_and_contains_expected_potential() -> None:
    result = solve("y' = (x+y+1)/(x-y-3)")
    assert result.general is not None
    assert result.general.is_implicit
    text = sp.sstr(result.general.expr)
    assert "atan" in text
    assert "log" in text


def test_case_9_reports_singular_envelope() -> None:
    result = solve("y = x*y' + y'**2")
    assert result.general is not None
    assert any(sp.simplify(item.expr + X**2 / 4) == 0 for item in result.singular_solutions)


def test_case_5_accepts_fractional_bernoulli() -> None:
    result = solve("y' = y/x + sqrt(y)")
    match = next(item for item in result.classifications if item.method == "bernoulli")
    assert sp.simplify(match.data["n"] - sp.Rational(1, 2)) == 0
