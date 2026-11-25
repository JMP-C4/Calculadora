"""Pruebas del clasificador multi-método."""

from __future__ import annotations

import pytest
import sympy as sp

from odecalc.classify import classify
from odecalc.classify.classifier import (
    _depends_only_on,
    bernoulli_coeffs,
    clairaut_or_lagrange,
    exact_parts,
    homogeneous_degree_zero,
    reducible_linear_coeffs,
    riccati_coeffs,
    separable_parts,
    substitution_linear_combo,
)
from odecalc.parsing import parse_ode
from odecalc.symbols import DY, U, X, Y

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


@pytest.mark.parametrize("equation, expected", CASES)
def test_regression_cases_detect_expected_method(equation: str, expected: str) -> None:
    parsed = parse_ode(equation)
    assert parsed.error is None
    methods = [match.method for match in classify(parsed)]
    assert expected in methods, methods


def test_classifier_returns_all_applicable_methods() -> None:
    parsed = parse_ode("y' = exp(-x**2)*y + 1")
    methods = {match.method for match in classify(parsed)}
    assert {"linear", "integrating_factor_x"} <= methods


def test_classifier_matches_are_sorted_and_justified() -> None:
    parsed = parse_ode("y' = (x+y)**2")
    matches = classify(parsed)
    assert len(matches) >= 2
    assert matches == sorted(matches, key=lambda item: (item.priority, item.method))
    assert all(match.name and match.evidence for match in matches)


def test_classifier_reports_no_methods_for_invalid_input() -> None:
    assert classify(parse_ode("y' = __import__('os')")) == []


def test_riccati_not_confused_with_bernoulli() -> None:
    parsed = parse_ode("y' = y**2 - x*y + 1")
    methods = {match.method for match in classify(parsed)}
    assert "riccati" in methods
    assert "bernoulli" not in methods


def test_separable_detects_factorization() -> None:
    parsed = parse_ode("y' = x**2 * sin(y)")
    match = next(item for item in classify(parsed) if item.method == "separable")
    assert match.data["g"] is not None
    assert match.data["h"] is not None


def test_separable_parts_edge_cases() -> None:
    assert separable_parts(sp.Integer(3)) == (sp.Integer(3), sp.Integer(1))
    assert separable_parts(X * Y) == (X, Y)
    assert separable_parts(X + Y) is None


def test_bernoulli_coeffs_reject_non_bernoulli_forms() -> None:
    assert bernoulli_coeffs(Y) is None
    assert bernoulli_coeffs(Y**2 + 1) is None
    assert bernoulli_coeffs(Y**2 + Y**3) is None
    assert bernoulli_coeffs(sp.exp(Y)) is None

    p_expr, q_expr, n = bernoulli_coeffs(X * Y**2)
    assert p_expr == 0
    assert q_expr == X
    assert n == 2


def test_exact_parts_requires_differential_or_explicit_form() -> None:
    differential = parse_ode("y dx - x dy = 0")
    assert exact_parts(differential) == (Y, -X)

    implicit = parse_ode("y = x*y' + y'**2")
    assert exact_parts(implicit) is None


def test_homogeneous_detection() -> None:
    assert homogeneous_degree_zero(Y / X)
    assert not homogeneous_degree_zero(X + Y**2)
    assert not homogeneous_degree_zero(X)


def test_riccati_coeffs_reject_other_degrees() -> None:
    assert riccati_coeffs(Y) is None
    assert riccati_coeffs(Y**3) is None
    assert riccati_coeffs(Y**2 + Y) is None
    assert riccati_coeffs(Y**2 + X) == (X, 0, 1)


def test_reducible_linear_coeffs_edge_cases() -> None:
    assert reducible_linear_coeffs(sp.sin(X * Y)) is None
    assert reducible_linear_coeffs((X + Y) / (2 * X + 2 * Y)) is None
    assert reducible_linear_coeffs((X + 1) / (Y + 2)) == (1, 0, 1, 0, 1, 2)


def test_substitution_linear_combo_edge_cases() -> None:
    assert substitution_linear_combo(X + 1) is None
    a, b, g_u = substitution_linear_combo((X + Y) ** 2)
    assert (a, b) == (1, 1)
    assert sp.simplify(g_u - U**2) == 0


def test_depends_only_on_supported_substitutions() -> None:
    assert sp.simplify(_depends_only_on(sp.sin(X), X) - sp.sin(U)) == 0
    assert _depends_only_on(Y, X) is None
    assert sp.simplify(_depends_only_on(sp.cos(Y), Y) - sp.cos(U)) == 0
    assert _depends_only_on(X, Y) is None
    assert sp.simplify(_depends_only_on(1 / (X * Y), X * Y) - 1 / U) == 0
    assert sp.simplify(_depends_only_on(1 / (X + Y), X + Y) - 1 / U) == 0
    assert sp.simplify(
        _depends_only_on(1 / (X**2 + Y**2), X**2 + Y**2) - 1 / U
    ) == 0
    assert _depends_only_on(1 / (X + Y), sp.Symbol("W")) is None


def test_clairaut_and_lagrange_detection() -> None:
    clairaut = parse_ode("y = x*y' + y'**2")
    kind, phi, psi = clairaut_or_lagrange(clairaut)
    assert kind == "clairaut"
    assert phi.has(DY)
    assert sp.simplify(psi - DY**2) == 0

    lagrange = parse_ode("y = x*y'**2 + y'")
    kind, _, _ = clairaut_or_lagrange(lagrange)
    assert kind == "lagrange"
    assert "lagrange" in {match.method for match in classify(lagrange)}

    assert clairaut_or_lagrange(parse_ode("y' = x + y")) is None


def test_integrating_factors_xy_and_x_plus_y() -> None:
    methods = {match.method for match in classify(parse_ode("y dx - x dy = 0"))}
    assert "integrating_factor_xy" in methods
    assert "integrating_factor_x" in methods

    methods = {
        match.method for match in classify(parse_ode("(x+y) dx + dy = 0"))
    }
    assert "integrating_factor_x_plus_y" in methods


def test_homogeneous_is_classified_with_evidence() -> None:
    matches = classify(parse_ode("y' = y/x"))
    homogeneous = next(item for item in matches if item.method == "homogeneous")
    assert "grado cero" in homogeneous.name
    assert homogeneous.evidence
