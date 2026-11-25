"""Solución de EDOs lineales de primer orden con factor integrante."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import linear_coeffs
from odecalc.methods.common import (
    explicit_solution,
    make_step,
    safe_integrate,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    coeffs = None
    if match is not None:
        if match.data.get("P") is not None:
            coeffs = (match.data["P"], match.data["Q"])
    if coeffs is None:
        coeffs = linear_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es lineal de primer orden.")

    p_expr, q_expr = (safe_simplify(item) for item in coeffs)
    steps: list[Step] = [
        make_step(
            1,
            "Escribir la forma estándar",
            f"{sp.latex(sp.Symbol('y'))}' + {sp.latex(p_expr)}\\,y = {sp.latex(q_expr)}",
            "Toda EDO lineal de primer orden se escribe como y' + P(x)y = Q(x).",
            ascii_expr=f"y' + ({sp.sstr(p_expr)}) y = {sp.sstr(q_expr)}",
        )
    ]

    integral_p = safe_integrate(p_expr, X)
    mu = safe_simplify(sp.exp(integral_p))
    steps.append(
        make_step(
            2,
            "Calcular el factor integrante",
            rf"\mu(x) = e^{{\int P(x)\,dx}} = {sp.latex(mu)}",
            "El factor integrante convierte el lado izquierdo en la derivada "
            "del producto μ(x)y.",
            ascii_expr=f"mu(x) = exp({sp.sstr(integral_p)}) = {sp.sstr(mu)}",
        )
    )
    steps.append(
        make_step(
            3,
            "Multiplicar por μ(x)",
            rf"\left(\mu(x)y\right)' = {sp.latex(safe_simplify(mu * q_expr))}",
            "Al multiplicar la ecuación por μ(x), el miembro izquierdo es "
            "exactamente (μy)'.",
            ascii_expr=f"(mu*y)' = {sp.sstr(safe_simplify(mu * q_expr))}",
        )
    )

    integral_muq = safe_integrate(safe_simplify(mu * q_expr), X)
    steps.append(
        make_step(
            4,
            "Integrar",
            rf"\mu(x)y = {sp.latex(integral_muq)} + C",
            "Se integra (μy)' respecto a x. Si la integral no es elemental, "
            "se deja indicada explícitamente en x.",
            ascii_expr=f"mu*y = {sp.sstr(integral_muq)} + C",
        )
    )

    general = safe_simplify((C + integral_muq) / mu)
    steps.append(
        make_step(
            5,
            "Despejar y",
            sp.latex(sp.Eq(Y, general)),
            "Se divide entre μ(x), que nunca se anula en el dominio real.",
        )
    )
    if integral_muq.has(sp.Integral):
        steps.append(
            make_step(
                6,
                "Nota sobre la integral",
                sp.latex(integral_muq),
                "La integral no admite una primitiva elemental; se conserva "
                "como integral definida/indefinida en x, sin incluir y(x) "
                "dentro del integrando.",
            )
        )

    return explicit_solution(general), steps, []


__all__ = ["solve"]
