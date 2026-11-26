"""Solución de EDOs exactas ``M(x,y) dx + N(x,y) dy = 0``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import exact_parts, is_exact
from odecalc.methods.common import (
    format_differential_latex,
    implicit_solution,
    make_step,
    safe_integrate,
    safe_simplify,
)
from odecalc.models import Match, ParsedODE, Solution, Step
from odecalc.symbols import X, Y


def exact_potential(m_expr: sp.Expr, n_expr: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    """Construye ``F`` y devuelve ``(F, M_x_integral, g'(y), g(y))``."""

    potential = safe_integrate(m_expr, X)
    g_prime = safe_simplify(n_expr - sp.diff(potential, Y))
    g_y = safe_integrate(g_prime, Y)
    full_potential = safe_simplify(potential + g_y)
    return full_potential, potential, g_prime, g_y


def solve(parsed: ParsedODE, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    parts = None
    if match is not None:
        if match.data.get("M") is not None:
            parts = (match.data["M"], match.data["N"])
    if parts is None:
        parts = exact_parts(parsed)
    if parts is None:
        raise ValueError("La ecuación no es exacta.")
    m_expr, n_expr = (safe_simplify(item) for item in parts)
    if not is_exact(m_expr, n_expr):
        raise ValueError("La ecuación no cumple la condición de exactitud.")

    steps: list[Step] = [
        make_step(
            1,
            "Escribir en forma diferencial",
            format_differential_latex(m_expr, n_expr),
            r"Se identifica $M(x,y)$ como el coeficiente de $dx$ y $N(x,y)$ como el "
            r"coeficiente de $dy$.",
            ascii_expr=f"({sp.sstr(m_expr)}) dx + ({sp.sstr(n_expr)}) dy = 0",
        )
    ]

    m_y = safe_simplify(sp.diff(m_expr, Y))
    n_x = safe_simplify(sp.diff(n_expr, X))
    steps.append(
        make_step(
            2,
            "Comprobar la exactitud",
            rf"\frac{{\partial M}}{{\partial y}} = {sp.latex(m_y)}, \qquad "
            rf"\frac{{\partial N}}{{\partial x}} = {sp.latex(n_x)}",
            "La ecuación es exacta porque las derivadas cruzadas coinciden.",
        )
    )

    potential = safe_integrate(m_expr, X)
    steps.append(
        make_step(
            3,
            "Integrar M respecto a x",
            rf"F(x,y) = {sp.latex(potential)} + g(y)",
            r"La constante de integración puede depender de $y$.",
        )
    )

    full_potential, potential, g_prime, g_y = exact_potential(m_expr, n_expr)
    steps.append(
        make_step(
            4,
            "Determinar g(y)",
            rf"g'(y) = {sp.latex(g_prime)} \quad\Longrightarrow\quad "
            rf"g(y) = {sp.latex(g_y)}",
            r"Se deriva $F$ respecto a $y$, se iguala con $N$ y se integra.",
        )
    )

    steps.append(
        make_step(
            5,
            "Escribir la solución general",
            sp.latex(full_potential) + " = C",
            "La solución de una EDO exacta es la familia de curvas de nivel "
            r"$F(x,y) = C$.",
        )
    )
    return implicit_solution(full_potential), steps, []


__all__ = ["solve"]
