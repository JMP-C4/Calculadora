"""Pruebas de pasos atómicos, reglas de signos, fórmulas, PVI y verificación."""

from __future__ import annotations

import pytest
import sympy as sp

from apps.desktop.app import _renderizar_png_latex
from core.notacion import NATURAL, fragmentos
from odecalc.api import solve
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    add_transposition_step,
    describe_double_negative,
    describe_sign_product,
    explain_derivative_rules,
    explain_integration_rules,
)
from odecalc.symbols import X, Y


def test_atomic_sign_product_explains_minus_times_minus() -> None:
    msg = describe_sign_product(-sp.Integer(2) * X, -sp.Integer(3) * Y)
    assert msg is not None
    assert "menos por menos" in msg.lower()
    assert "6" in msg

    msg_mixed = describe_sign_product(-sp.Integer(2) * X, sp.Integer(3) * Y)
    assert msg_mixed is not None
    assert "menos por más" in msg_mixed.lower() or "más por menos" in msg_mixed.lower()


def test_atomic_double_negative_explains_subtraction_of_negative() -> None:
    msg = describe_double_negative(X, -sp.Integer(1))
    assert msg is not None
    assert "menos por menos" in msg.lower()
    assert "x + 1" in msg


def test_atomic_product_and_transposition_helpers() -> None:
    builder = StepBuilder()
    add_transposition_step(builder, "y'", -X * Y, -X * Y, r"y' + x\,y = 0")
    add_product_atomic_steps(
        builder,
        -sp.Integer(2),
        -(X + 1),
        sp.Integer(2) * X + 2,
        title="Multiplicar factores negativos",
        lhs_latex="Q_v(x)",
        intro_explanation="Producto con signos negativos y distribución.",
    )
    assert len(builder.steps) == 2
    assert builder.steps[0].number == 1
    assert builder.steps[1].number == 2
    assert "regla de los signos" in builder.steps[1].explanation.lower()
    assert "distribuye" in builder.steps[1].explanation.lower()


def test_derivative_and_integration_rule_descriptions() -> None:
    deriv_text = explain_derivative_rules(X**3 + sp.cos(X), X, label="f")
    assert "potencia" in deriv_text.lower()
    assert r"\cos" in deriv_text

    int_text = explain_integration_rules(1 / X + sp.exp(-2 * X), X, sp.log(X) - sp.exp(-2 * X) / 2)
    assert "logarítmica" in int_text.lower()
    assert "exponencial" in int_text.lower()


@pytest.mark.parametrize(
    "equation, x0, y0",
    [
        ("y' = -x*y", 0.0, 2.0),
        ("y' - (2/x)*y = -4*x", 1.0, 1.0),
        ("(2*x*y + 1)*dx + (x**2 + cos(y))*dy = 0", None, None),
        ("(3*x*y + y**2)*dx + (x**2 + x*y)*dy = 0", None, None),
        ("y' - y/x = -x*y**2", 1.0, 1.0),
        ("dy/dx = (x**2 + y**2)/(x*y)", None, None),
        ("dy/dx = (x + y - 1)/(x - y + 3)", None, None),
        ("dy/dx = sin(x + y)", None, None),
        ("y' = y**2 - x*y + 1", None, None),
        ("y = x*y' + (y')**2", None, None),
    ],
)
def test_every_method_emits_rich_sequential_steps_and_renders_cleanly(
    equation: str, x0: float | None, y0: float | None
) -> None:
    kw = {"x0": x0, "y0": y0} if x0 is not None and y0 is not None else {}
    res = solve(equation, compute_numeric=False, **kw)
    assert res.error is None
    assert [step.number for step in res.steps] == list(range(1, len(res.steps) + 1))
    assert len(res.steps) >= 4

    joined = " ".join(f"{s.title} {s.explanation}" for s in res.steps).lower()
    assert "verific" in joined or "residuo" in joined
    if x0 is not None and res.particular is not None:
        assert "condición inicial" in joined or "pvi" in joined
        assert "constante" in joined or "particular" in joined

    # Todas las fórmulas y fragmentos en prosa deben renderizar en mathtext sin excepciones.
    for step in res.steps:
        if step.latex:
            _renderizar_png_latex(step.latex)
        for mode in ("Algebraica", NATURAL):
            for content, is_tex in fragmentos(step.explanation, mode):
                if is_tex:
                    _renderizar_png_latex(content)


def test_reducible_double_negative_shift_is_explicitly_explained() -> None:
    res = solve("dy/dx = (x + y - 1)/(x - y + 3)", compute_numeric=False)
    combined = " ".join(s.explanation.lower() for s in res.steps)
    assert "menos por menos" in combined
    assert "determinante" in combined
