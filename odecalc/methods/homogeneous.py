"""Solución de EDOs homogéneas de grado cero con ``y = u x``."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.common import (
    explicit_solution,
    implicit_solution,
    make_step,
    safe_integrate,
    safe_solve_expr,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, U, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    del match
    transformed = safe_simplify(rhs.subs(Y, U * X))
    if transformed.has(X):
        raise ValueError("La ecuación no es homogénea de grado cero.")

    steps: list[Step] = [
        make_step(
            1,
            "Aplicar la sustitución y = u x",
            sp.latex(sp.Eq(sp.Symbol("y"), U * X)),
            "En una EDO homogénea de grado cero, y = ux convierte la ecuación "
            "en una EDO separable en u y x.",
        ),
        make_step(
            2,
            "Derivar la sustitución",
            r"\frac{dy}{dx} = u + x\frac{du}{dx}",
            "Se deriva y = ux con la regla del producto.",
        ),
        make_step(
            3,
            "Sustituir en la EDO",
            f"u + x\\frac{{du}}{{dx}} = {sp.latex(transformed)}",
            "La ecuación resultante sólo contiene u, x y du/dx.",
        ),
    ]

    difference = safe_simplify(transformed - U)
    if difference == 0:
        steps.append(
            make_step(
                4,
                "Integrar",
                r"u = C \quad\Longrightarrow\quad y = Cx",
                "Si u' = 0, entonces u es constante y la solución es una recta "
                "que pasa por el origen.",
            )
        )
        return explicit_solution(C * X), steps, []

    steps.append(
        make_step(
            4,
            "Separar variables",
            rf"\frac{{du}}{{{sp.latex(difference)}}} = \frac{{dx}}{{x}}",
            "Se agrupan los términos en u y en x.",
        )
    )

    left = safe_integrate(1 / difference, U)
    right = safe_integrate(1 / X, X)
    steps.append(
        make_step(
            5,
            "Integrar",
            f"{sp.latex(left)} = {sp.latex(right)} + C",
            "Se integra cada miembro respecto a su variable.",
        )
    )

    relation = safe_simplify(left - right - C)
    candidates = safe_solve_expr(relation, U)
    explicit_u = next(
        (
            item
            for item in candidates
            if not item.has(U) and item not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
        ),
        None,
    )
    if explicit_u is not None:
        solution = safe_simplify(explicit_u * X)
        steps.append(
            make_step(
                6,
                "Volver a las variables originales",
                sp.latex(sp.Eq(Y, solution)),
                "Se sustituye u = y/x y se despeja y.",
            )
        )
        return explicit_solution(solution), steps, []

    potential = safe_simplify(left.subs(U, Y / X) - right)
    steps.append(
        make_step(
            6,
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            "No se pudo despejar u; se conserva la relación implícita con "
            "u = y/x.",
        )
    )
    return implicit_solution(potential), steps, []


__all__ = ["solve"]
