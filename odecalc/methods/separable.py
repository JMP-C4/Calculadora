"""Solución de EDOs separables ``y' = g(x) h(y)``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import separable_parts
from odecalc.methods.common import (
    equilibrium_solutions,
    explicit_solution,
    implicit_solution,
    make_step,
    safe_integrate,
    safe_solve_expr,
    safe_simplify,
)
from odecalc.models import Match, ParsedODE, Solution, Step
from odecalc.symbols import C, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    parts = None
    if match is not None:
        parts = (match.data.get("g"), match.data.get("h"))
    if not parts or parts[0] is None:
        parts = separable_parts(rhs)
    if parts is None:
        raise ValueError("La ecuación no es separable.")

    g_expr, h_expr = parts
    g_expr = safe_simplify(g_expr)
    h_expr = safe_simplify(h_expr)

    steps: list[Step] = []
    steps.append(
        make_step(
            1,
            "Identificar una EDO separable",
            sp.latex(sp.Eq(sp.Symbol("y'"), rhs)),
            f"El lado derecho factoriza como g(x)h(y) con g(x) = {sp.sstr(g_expr)} "
            f"y h(y) = {sp.sstr(h_expr)}.",
        )
    )

    if h_expr == 0:
        steps.append(
            make_step(
                2,
                "Integrar directamente",
                r"y = C",
                "Si h(y) = 0 entonces y' = 0 y toda función constante es solución.",
            )
        )
        return explicit_solution(C), steps, []

    steps.append(
        make_step(
            2,
            "Separar variables",
            rf"\frac{{1}}{{{sp.latex(h_expr)}}}\,dy = {sp.latex(g_expr)}\,dx",
            "Se divide entre h(y) (suponiendo h(y) ≠ 0) y se multiplica por dx.",
        )
    )

    left = safe_integrate(1 / h_expr, Y)
    right = safe_integrate(g_expr, X)
    steps.append(
        make_step(
            3,
            "Integrar ambos miembros",
            f"{sp.latex(left)} = {sp.latex(right)} + C",
            "Cada variable se integra por separado; la constante se añade una sola vez.",
        )
    )

    relation = safe_simplify(left - right - C)
    solutions_y = safe_solve_expr(relation, Y)
    explicit_branches = list(
        dict.fromkeys(
            item
            for item in solutions_y
            if not item.has(Y) and item not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
        )
    )
    explicit = explicit_branches[0] if len(explicit_branches) == 1 else None

    lost = equilibrium_solutions(h_expr)
    if len(explicit_branches) > 1:
        potential = safe_simplify(left - right)
        steps.append(
            make_step(
                4,
                "Conservar la relación implícita",
                sp.latex(potential) + " = C",
                "Al despejar y aparecen varias ramas. Se conserva la relación "
                "implícita para que el PVI elija la rama correcta.",
                ascii_expr=f"{sp.sstr(potential)} = C",
            )
        )
        return implicit_solution(
            potential,
            note="La solución explícita tiene varias ramas; se usa la forma "
            "implícita hasta aplicar la condición inicial.",
        ), steps, lost

    if explicit is not None:
        steps.append(
            make_step(
                4,
                "Despejar y",
                sp.latex(sp.Eq(Y, explicit)),
                "Se resuelve la relación implícita para obtener y(x).",
            )
        )
        return explicit_solution(explicit, note=None), steps, lost

    potential = safe_simplify(left - right)
    steps.append(
        make_step(
            4,
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            "No fue posible (o no es conveniente) despejar y; se conserva la "
            "solución implícita, que es igualmente válida.",
        )
    )
    return implicit_solution(potential), steps, lost


__all__ = ["solve"]
