"""Propiedades del motor ``odecalc`` con Hypothesis."""

from __future__ import annotations

import sympy as sp
from hypothesis import HealthCheck, given, settings, strategies as st

from odecalc.api import solve
from odecalc.parsing import parse_ode

SETTINGS = settings(
    max_examples=15,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

SMALL_INTS = st.integers(min_value=-3, max_value=3).filter(lambda value: value != 0)


@SETTINGS
@given(a=SMALL_INTS, b=SMALL_INTS)
def test_generated_linear_equation_verifies(a: int, b: int) -> None:
    equation = f"y' = {a}*y + {b}*x"
    result = solve(equation, compute_numeric=False)
    assert result.error is None, result.warnings
    assert result.general is not None
    assert result.verification is not None
    assert result.verification.status == "ok"


@SETTINGS
@given(a=SMALL_INTS, b=SMALL_INTS, c=SMALL_INTS)
def test_generated_exact_differential_form_verifies(a: int, b: int, c: int) -> None:
    # F(x,y) = a*x^2/2 + b*x*y + c*y^2/2 produce una forma exacta.
    m_expr = f"{a}*x + {b}*y"
    n_expr = f"{b}*x + {c}*y"
    equation = f"({m_expr}) dx + ({n_expr}) dy = 0"
    parsed = parse_ode(equation)
    assert parsed.error is None
    result = solve(equation, compute_numeric=False)
    assert result.error is None, result.warnings
    assert result.general is not None
    assert result.verification is not None
    assert result.verification.status == "ok"


@SETTINGS
@given(
    x0=st.floats(-2.0, 2.0, allow_nan=False, allow_infinity=False),
    y0=st.floats(-2.0, 2.0, allow_nan=False, allow_infinity=False).filter(
        lambda value: abs(value) > 1e-3
    ),
)
def test_generated_pvi_is_satisfied(x0: float, y0: float) -> None:
    result = solve("y' = 2*y + x", x0=x0, y0=y0, compute_numeric=False)
    assert result.particular is not None
    value = complex(sp.N(result.particular.expr.subs(sp.Symbol("x", real=True), x0)))
    assert abs(value - y0) < 1e-5


@SETTINGS
@given(
    payload=st.sampled_from(
        [
            "__import__('os')",
            "open('/etc/passwd')",
            "eval('1+1')",
            "exec('x=1')",
            "lambda: 1",
            "x.__class__",
            "globals()",
            "[1, 2, 3]",
            '"cadena"',
        ]
    )
)
def test_malicious_payloads_never_parse(payload: str) -> None:
    assert parse_ode(f"y' = {payload}").error is not None
