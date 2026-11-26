"""Pruebas del parser seguro y de las formas de entrada de libro."""

from __future__ import annotations

import sympy as sp
import pytest

from odecalc.parsing import parse_ode
from odecalc.symbols import X, Y


@pytest.mark.parametrize(
    "text, kind",
    [
        ("y' = x + y", "explicit"),
        ("dy/dx = x + y", "explicit"),
        ("y' + 2*x*y = x", "explicit"),
        ("y' + y = sin(x)", "explicit"),
        ("y' = 2x + 3y^2", "explicit"),
        ("y' = x² + y²", "explicit"),
        ("x = y + y'", "explicit"),
        ("y = x*y' + y'**2", "implicit"),
        ("y = x*y' + sqrt(y')", "implicit"),
        ("(2*x*y + 1) dx + (x^2 + 3*y^2) dy = 0", "differential"),
        ("cos(x)*cos(y) dx - sin(x)*sin(y) dy = 0", "differential"),
    ],
)
def test_accepts_book_forms(text: str, kind: str) -> None:
    parsed = parse_ode(text)
    assert parsed.error is None
    assert parsed.kind == kind
    assert parsed.standard_form
    assert parsed.latex_str


def test_standard_linear_form() -> None:
    parsed = parse_ode("y' + 2*x*y = x")
    assert parsed.error is None
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - (X - 2 * X * Y)) == 0


def test_explicit_rhs_is_extracted_from_derivative() -> None:
    parsed = parse_ode("dy/dx = 2x + 3y^2")
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - (2 * X + 3 * Y**2)) == 0


def test_differential_form() -> None:
    parsed = parse_ode("(2*x*y + 1) dx + (x^2 + 3*y^2) dy = 0")
    assert parsed.error is None
    assert parsed.kind == "differential"
    assert parsed.M is not None and parsed.N is not None
    assert sp.simplify(parsed.M - (2 * X * Y + 1)) == 0
    assert sp.simplify(parsed.N - (X**2 + 3 * Y**2)) == 0
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs + parsed.M / parsed.N) == 0


def test_implicit_clairaut_form() -> None:
    parsed = parse_ode("y = x*y' + y'**2")
    assert parsed.error is None
    assert parsed.kind == "implicit"
    assert parsed.rhs is None
    assert parsed.F is not None


def test_latex_clairaut_keeps_derivative_between_parentheses() -> None:
    texto = r"$$y = x\frac{dy}{dx} - \left(\frac{dy}{dx}\right)^2$$"
    from odecalc.parsing.parser import _latex_to_plain

    plano = _latex_to_plain(texto)
    assert "x(dy/dx)" in plano
    assert "((dy/dx))**(2)" in plano
    parsed = parse_ode(texto)
    assert parsed.error is None
    assert parsed.kind == "implicit"
    assert parsed.F is not None


def test_unicode_and_implicit_multiplication() -> None:
    parsed = parse_ode("y' = 2x + 3y² + √(x)")
    assert parsed.error is None
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - (2 * X + 3 * Y**2 + sp.sqrt(X))) == 0


@pytest.mark.parametrize(
    "text",
    [
        r"$$\frac{dy}{dx} = \frac{x^2}{y}$$",
        r"$\frac{dy}{dx}=\frac{x^{2}}{y}$",
        r"\frac{\mathrm{d}y}{\mathrm{d}x} = \frac{x^2}{y}",
        r"\frac{d y}{d x} = \frac{x^2}{y}",
    ],
)
def test_accepts_latex_fraction_notation(text: str) -> None:
    parsed = parse_ode(text)
    assert parsed.error is None
    assert parsed.kind == "explicit"
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - X**2 / Y) == 0
    assert "\\frac{dy}{dx}" in parsed.latex_str


@pytest.mark.parametrize(
    "text, dominio",
    [
        (r"$$\frac{dy}{dx} + \frac{2}{x}y = 4x, \quad x > 0$$", "x > 0"),
        (r"$$\frac{dy}{dx} = y^2 - \frac{2}{x}y - \frac{1}{x^2}, \quad x > 0$$", "x > 0"),
        (r"y' = x*y, x>=0", "x >= 0"),
    ],
)
def test_accepts_trailing_domain_clause(text: str, dominio: str) -> None:
    parsed = parse_ode(text)
    assert parsed.error is None
    assert parsed.dominio == dominio
    assert parsed.rhs is not None


def test_accepts_latex_functions_roots_and_powers() -> None:
    parsed = parse_ode(r"$$\frac{dy}{dx} = \sqrt{x} + \sin(x) + x^{2}$$")
    assert parsed.error is None
    assert parsed.rhs is not None
    expected = sp.sqrt(X) + sp.sin(X) + X**2
    assert sp.simplify(parsed.rhs - expected) == 0


def test_accepts_latex_differential_form() -> None:
    parsed = parse_ode(r"$$y\,dx - x\,dy = 0$$")
    assert parsed.error is None
    assert parsed.kind == "differential"
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - Y / X) == 0


def test_rejects_higher_order_latex_fraction() -> None:
    parsed = parse_ode(r"$$\frac{d^2y}{dx^2} = y$$")
    assert parsed.error is not None
    assert parsed.rhs is None


def test_rejects_unclosed_latex_brace() -> None:
    parsed = parse_ode(r"$$\frac{dy}{dx} = \frac{x}{y$$")
    assert parsed.error is not None
    assert parsed.rhs is None


def test_rejects_unknown_latex_command() -> None:
    parsed = parse_ode(r"$$\frac{dy}{dx} = \unknown{x}$$")
    assert parsed.error is not None
    assert parsed.rhs is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "x + y",
        "= x + y",
        "y' = ",
        "dy/dx",
        "d2y/dx2 = y",
        "y'' = x",
        "y' = x + y + z",
        "y' = x = y",
    ],
)
def test_rejects_malformed_equations(text: str) -> None:
    parsed = parse_ode(text)
    assert parsed.error is not None
    assert parsed.rhs is None


@pytest.mark.parametrize(
    "text",
    [
        "__import__('os').system('ls')",
        "open('/etc/passwd').read()",
        "x.__class__",
        "x.real",
        "eval('1+1')",
        "exec('print(1)')",
        "lambda: 1",
        "[1, 2]",
        '"texto"',
        "x_y",
        "__builtins__",
        "globals()",
        "getattr(x, 'real')",
    ],
)
def test_blocks_malicious_input(text: str) -> None:
    parsed = parse_ode(f"y' = {text}")
    assert parsed.error is not None
    assert parsed.rhs is None


def test_no_arbitrary_code_is_executed(tmp_path) -> None:
    marker = tmp_path / "pwned"
    parsed = parse_ode(f"y' = __import__('pathlib').Path('{marker}').touch()")
    assert parsed.error is not None
    assert not marker.exists()


def test_higher_order_is_rejected() -> None:
    assert parse_ode("y''' = x").error is not None
    assert parse_ode("d3y/dx3 = x").error is not None
