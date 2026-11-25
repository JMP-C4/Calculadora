"""Solución de EDOs de Bernoulli ``y' + P(x)y = Q(x)yⁿ`` para n real."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import bernoulli_coeffs
from odecalc.methods.common import (
    explicit_solution,
    make_step,
    safe_integrate,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, V, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    coeffs = None
    if match is not None:
        if match.data.get("P") is not None:
            coeffs = (match.data["P"], match.data["Q"], match.data["n"])
    if coeffs is None:
        coeffs = bernoulli_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es de Bernoulli.")

    p_expr, q_expr, n = (safe_simplify(item) for item in coeffs)
    alpha = safe_simplify(1 - n)
    if alpha == 0:
        raise ValueError("n = 1 no es una EDO de Bernoulli.")

    steps: list[Step] = [
        make_step(
            1,
            "Identificar la EDO de Bernoulli",
            f"y' + {sp.latex(p_expr)}\\,y = {sp.latex(q_expr)}\\,y^{{{sp.latex(n)}}}",
            f"La ecuación tiene la forma de Bernoulli con n = {sp.sstr(n)}.",
        ),
        make_step(
            2,
            "Aplicar la sustitución v = y^(1−n)",
            f"v = y^{{{sp.latex(alpha)}}}",
            f"Con n = {sp.sstr(n)}, el exponente es 1 − n = {sp.sstr(alpha)}. "
            "Esta sustitución elimina la potencia no lineal.",
        ),
    ]

    p_transformed = safe_simplify(alpha * p_expr)
    q_transformed = safe_simplify(alpha * q_expr)
    steps.append(
        make_step(
            3,
            "Obtener la EDO lineal en v",
            f"v' + {sp.latex(p_transformed)}\\,v = {sp.latex(q_transformed)}",
            "Al derivar v = y^(1−n) y sustituir se obtiene una EDO lineal.",
        )
    )

    integral_p = safe_integrate(p_transformed, X)
    mu = safe_simplify(sp.exp(integral_p))
    integral_muq = safe_integrate(safe_simplify(mu * q_transformed), X)
    v_solution = safe_simplify((C + integral_muq) / mu)
    steps.append(
        make_step(
            4,
            "Resolver la EDO lineal",
            rf"v = {sp.latex(v_solution)}",
            "Se aplica el factor integrante μ(x) = e^(∫(1−n)P dx) a la EDO lineal.",
        )
    )

    exponent = safe_simplify(1 / alpha)
    y_solution = safe_simplify(v_solution**exponent)
    steps.append(
        make_step(
            5,
            "Volver a y",
            sp.latex(sp.Eq(Y, y_solution)),
            f"Se despeja y = v^{{{sp.latex(exponent)}}}. Deben respetarse las "
            "ramas reales de la potencia.",
        )
    )

    singular: list[Solution] = []
    try:
        if n.is_positive:
            singular.append(
                explicit_solution(
                    0,
                    note="y = 0 es una solución de equilibrio que se pierde al "
                    "dividir entre yⁿ.",
                )
            )
    except Exception:
        pass
    return (
        explicit_solution(
            y_solution,
            note="La potencia final puede requerir elegir la rama real; "
            "la verificación numérica comprueba la rama principal.",
        ),
        steps,
        singular,
    )


__all__ = ["solve"]
