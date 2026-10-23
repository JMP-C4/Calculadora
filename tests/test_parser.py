"""Tests unitarios del parser de EDOs."""

from __future__ import annotations

import sympy as sp

from math_engine.parser import parse_ode, x, y


def test_parse_sum_returns_rhs_in_terms_of_y_function():
    result = parse_ode("dy/dx = x + y")

    assert result.error is None
    assert result.rhs is not None
    assert sp.simplify(result.rhs - (x + y)) == 0
    assert r"\frac{dy}{dx}" in result.latex_str


def test_parse_prime_notation():
    result = parse_ode("y' = sin(x)")

    assert result.error is None
    assert result.rhs is not None
    assert sp.simplify(result.rhs - sp.sin(x)) == 0


def test_parse_prime_with_explicit_argument():
    result = parse_ode("y'(x) = x*y")

    assert result.error is None
    assert result.rhs is not None
    assert sp.simplify(result.rhs - x * y) == 0


def test_empty_string_is_rejected():
    result = parse_ode("   ")

    assert result.rhs is None
    assert result.error is not None


def test_expression_without_equals_is_rejected():
    result = parse_ode("x + y")

    assert result.rhs is None
    assert result.error is not None


def test_second_order_is_rejected():
    for text in ("d2y/dx2 = y", "y'' = x", "d^2y/dx^2 = y"):
        result = parse_ode(text)
        assert result.rhs is None
        assert result.error is not None


def test_empty_right_hand_side_is_rejected():
    result = parse_ode("dy/dx = ")

    assert result.rhs is None
    assert result.error is not None


def test_unknown_symbol_is_rejected():
    result = parse_ode("dy/dx = x + y + z")

    assert result.rhs is None
    assert "z" in (result.error or "")


def test_standard_functions_are_supported():
    functions = (
        "sin(x)",
        "cos(x)",
        "tan(x)",
        "exp(x)",
        "log(x)",
        "ln(x)",
        "sqrt(x)",
    )

    for function in functions:
        result = parse_ode(f"dy/dx = {function}")
        assert result.error is None, function
        assert result.rhs is not None, function
        assert result.latex_str, function


def test_multiple_equals_are_rejected():
    result = parse_ode("dy/dx = x = y")

    assert result.rhs is None
    assert result.error is not None
