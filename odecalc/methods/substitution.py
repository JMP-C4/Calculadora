"""Solución mediante la sustitución ``u = a x + b y``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import substitution_linear_combo
from odecalc.methods.common import (
    _signed_term_latex,
    explicit_solution,
    format_linear_combo_latex,
    implicit_solution,
    make_step,
    safe_integrate,
    safe_solve_expr,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, U, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    data = None
    if match is not None and match.data.get("a") is not None:
        data = (match.data["a"], match.data["b"], match.data["G"])
    if data is None:
        data = substitution_linear_combo(rhs)
    if data is None:
        raise ValueError("La ecuación no admite la sustitución u = a x + b y.")

    a, b, g_u = (safe_simplify(item) for item in data)
    if b == 0:
        raise ValueError("La sustitución lineal requiere b ≠ 0.")

    g_tex = sp.latex(g_u)
    g_arg = rf"\left({g_tex}\right)" if isinstance(g_u, sp.Add) else g_tex
    b_term = _signed_term_latex(b, g_arg, include_plus=(a != 0))
    rhs_u = f"{sp.latex(a)}{b_term}" if a != 0 else b_term.lstrip()

    steps: list[Step] = [
        make_step(
            1,
            "Identificar la sustitución",
            f"u = {format_linear_combo_latex(a, b)}",
            r"El lado derecho depende de $x$ e $y$ únicamente a través de la "
            rf"combinación $u$. Entonces $y' = G(u)$ con $G(u) = {g_tex}$.",
        ),
        make_step(
            2,
            "Derivar la sustitución",
            r"\frac{du}{dx} = a + b\,\frac{dy}{dx}",
            r"Se deriva $u = ax + by$ respecto a $x$.",
        ),
        make_step(
            3,
            "Transformar la EDO",
            rf"\frac{{du}}{{dx}} = {rhs_u}",
            r"Al sustituir $y' = G(u)$ se obtiene una EDO separable en $u$ y $x$.",
        ),
    ]

    denominator = safe_simplify(a + b * g_u)
    if denominator == 0:
        steps.append(
            make_step(
                4,
                "Integrar",
                r"u = C \quad\Longrightarrow\quad y = \frac{C - ax}{b}",
                r"Si $u' = 0$, $u$ es constante y la solución es una recta.",
            )
        )
        return explicit_solution((C - a * X) / b), steps, []

    steps.append(
        make_step(
            4,
            "Separar variables",
            rf"\frac{{du}}{{{sp.latex(denominator)}}} = dx",
            r"La ecuación es separable: todo depende de $u$ a la izquierda y de $x$ "
            "a la derecha.",
        )
    )

    integral = safe_integrate(1 / denominator, U)
    relation = safe_simplify(integral - X - C)
    steps.append(
        make_step(
            5,
            "Integrar",
            f"{sp.latex(integral)} = x + C",
            r"Se integra respecto a $u$ y respecto a $x$.",
        )
    )

    explicit_u = next(
        (
            item
            for item in safe_solve_expr(relation, U)
            if not item.has(U) and item not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
        ),
        None,
    )
    if explicit_u is not None:
        solution = safe_simplify((explicit_u - a * X) / b)
        steps.append(
            make_step(
                6,
                "Volver a y",
                sp.latex(sp.Eq(Y, solution)),
                r"Se sustituye $u = ax + by$ y se despeja $y$.",
            )
        )
        return explicit_solution(solution), steps, []

    potential = safe_simplify(integral.subs(U, a * X + b * Y) - X)
    steps.append(
        make_step(
            6,
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            r"No se pudo despejar $u$; se conserva la relación implícita.",
        )
    )
    return implicit_solution(potential), steps, []


__all__ = ["solve"]
