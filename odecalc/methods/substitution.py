"""Solución mediante la sustitución ``u = a x + b y``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import substitution_linear_combo
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    explain_integration_rules,
)
from odecalc.methods.common import (
    _signed_term_latex,
    explicit_solution,
    format_linear_combo_latex,
    implicit_solution,
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

    builder = StepBuilder()
    builder.add(
        "Identificar la sustitución lineal u = a x + b y",
        f"u = {format_linear_combo_latex(a, b)}",
        rf"¿Por qué este método? $x$ e $y$ sólo aparecen combinados en la expresión lineal "
        rf"$u = {format_linear_combo_latex(a, b)}$, de modo que $y' = G(u) = {g_tex}$.",
    )
    du_rhs_term = _signed_term_latex(b, r"\frac{dy}{dx}", include_plus=(a != 0))
    du_lhs_expr = rf"{sp.latex(a)}{du_rhs_term}" if a != 0 else du_rhs_term.lstrip()
    builder.add(
        "Derivar u respecto a x (regla de la suma y cadena)",
        rf"\frac{{du}}{{dx}} = {du_lhs_expr}",
        rf"Derivamos $u = {format_linear_combo_latex(a, b)}$ respecto a $x$: $\frac{{d}}{{dx}}(ax) = a$ "
        r"y $\frac{d}{dx}(by) = b\frac{dy}{dx}$.",
    )

    denominator = safe_simplify(a + b * g_u)
    add_product_atomic_steps(
        builder,
        b,
        g_u,
        safe_simplify(b * g_u),
        title="Sustituir dy/dx = G(u) y calcular b·G(u)",
        lhs_latex=rf"\frac{{du}}{{dx}} - \left({sp.latex(a)}\right)",
        intro_explanation=rf"Sustituimos $\frac{{dy}}{{dx}} = {g_tex}$ en $\frac{{du}}{{dx}} = a + b\,y'$, obteniendo $\frac{{du}}{{dx}} = {rhs_u}$.",
    )

    if denominator == 0:
        builder.add(
            "Integrar la pendiente nula du/dx = 0",
            r"u = C \quad\Longrightarrow\quad y = \frac{C - ax}{b}",
            r"Como $a + b G(u) = 0$, $u$ es constante y la solución es una recta.",
        )
        return explicit_solution((C - a * X) / b), builder.steps, []

    inv_den = safe_simplify(1 / denominator)
    builder.add(
        "Separar variables en u y x",
        rf"\left({sp.latex(inv_den)}\right)\,du = dx",
        r"Dividimos entre $a + b G(u)$ y multiplicamos por $dx$ para separar $u$ y $x$.",
    )

    integral = safe_integrate(inv_den, U)
    relation = safe_simplify(integral - X - C)
    builder.add(
        "Integrar ambos miembros",
        f"{sp.latex(integral)} = x + C",
        explain_integration_rules(inv_den, U, integral) + r" Además $\int 1\,dx = x + C$.",
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
        builder.add(
            "Deshacer la sustitución u = a x + b y y despejar y",
            sp.latex(sp.Eq(Y, solution)),
            rf"Reemplazamos $u = {format_linear_combo_latex(a, b)}$, pasamos ${sp.latex(a * X)}$ con signo "
            rf"cambiado al otro lado y dividimos entre $b = {sp.latex(b)}$.",
        )
        return explicit_solution(solution), builder.steps, []

    potential = safe_simplify(integral.subs(U, a * X + b * Y) - X)
    builder.add(
        "Escribir la solución implícita",
        sp.latex(potential) + " = C",
        r"Sustituimos $u = ax + by$; como no fue posible aislar $y$, conservamos la solución implícita.",
    )
    return implicit_solution(potential), builder.steps, []


__all__ = ["solve"]
