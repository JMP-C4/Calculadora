"""Solución de EDOs separables ``y' = g(x) h(y)``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import separable_parts
from odecalc.methods.atomic_steps import (
    StepBuilder,
    describe_sign_product,
    explain_integration_rules,
)
from odecalc.methods.common import (
    equilibrium_solutions,
    explicit_solution,
    implicit_solution,
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

    builder = StepBuilder()
    sign_hint = describe_sign_product(g_expr, h_expr) or ""
    builder.add(
        "Identificar método y fórmula (EDO separable)",
        sp.latex(sp.Eq(sp.Symbol("y'"), rhs)),
        rf"¿Por qué este método? El lado derecho factoriza exactamente como producto de "
        rf"una función de $x$ por una de $y$: $y' = g(x)\cdot h(y)$ con $g(x) = {sp.latex(g_expr)}$ "
        rf"y $h(y) = {sp.latex(h_expr)}$. Fórmula del método: $\frac{{1}}{{h(y)}}\,dy = g(x)\,dx \Longrightarrow "
        rf"\int \frac{{1}}{{h(y)}}\,dy = \int g(x)\,dx + C$. {sign_hint}".strip(),
    )

    if h_expr == 0:
        builder.add(
            "Integrar directamente la pendiente nula",
            r"y = C",
            r"Si $h(y) = 0$ entonces $\frac{dy}{dx} = 0$; usando $\int 0\,dx = C$, toda función "
            "constante es solución.",
        )
        return explicit_solution(C), builder.steps, []

    inv_h = safe_simplify(1 / h_expr)
    sign_sep = ""
    if str(sp.latex(h_expr)).lstrip().startswith("-"):
        sign_sep = (
            r" Como $h(y)$ lleva signo negativo, al dividir $+1$ entre un término negativo "
            r"el cociente hereda el signo menos ($\frac{+}{-} = -$)."
        )
    builder.add(
        "Separar variables",
        rf"\left({sp.latex(inv_h)}\right)\,dy = \left({sp.latex(g_expr)}\right)\,dx",
        r"Dividimos ambos miembros entre $h(y)$ (suponiendo $h(y) \neq 0$) y multiplicamos "
        r"por el diferencial $dx$ para agrupar toda $y$ a la izquierda y toda $x$ a la derecha."
        + sign_sep,
    )

    left = safe_integrate(inv_h, Y)
    right = safe_integrate(g_expr, X)
    builder.add(
        "Integrar el miembro en y",
        rf"\int \left({sp.latex(inv_h)}\right)\,dy = {sp.latex(left)} + C_1",
        explain_integration_rules(inv_h, Y, left),
    )
    builder.add(
        "Integrar el miembro en x y unificar constantes",
        f"{sp.latex(left)} = {sp.latex(right)} + C",
        explain_integration_rules(g_expr, X, right)
        + r" Se combinan las constantes arbitrarias de ambos lados en una sola constante $C = C_2 - C_1$.",
    )

    lost = equilibrium_solutions(h_expr)
    if lost:
        lost_tex = ", ".join(item.latex for item in lost)
        builder.add(
            "Analizar soluciones de equilibrio perdidas (h(y) = 0)",
            lost_tex,
            rf"Al dividir entre $h(y) = {sp.latex(h_expr)}$ excluimos las raíces de $h(y) = 0$. "
            "Cada raíz constante hace $y' = 0 = g(x)h(y)$ y constituye una solución constante o "
            "de equilibrio adicional.",
        )

    if left.has(sp.Piecewise, sp.Abs) or right.has(sp.Piecewise, sp.Abs):
        potential = left - right if left.has(sp.Piecewise) else safe_simplify(left - right)
        builder.add(
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            "Se conserva la relación implícita por tramos para preservar todas las ramas reales.",
        )
        return implicit_solution(potential), builder.steps, lost

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
    if len(explicit_branches) > 1:
        potential = safe_simplify(left - right)
        builder.add(
            "Conservar la relación implícita",
            sp.latex(potential) + " = C",
            "Al despejar y aparecen varias ramas. Se conserva la relación "
            "implícita para que el PVI elija la rama correcta.",
            ascii_expr=f"{sp.sstr(potential)} = C",
        )
        return implicit_solution(
            potential,
            note="La solución explícita tiene varias ramas; se usa la forma "
            "implícita hasta aplicar la condición inicial.",
        ), builder.steps, lost

    if explicit is not None:
        builder.add(
            "Despejar y(x)",
            sp.latex(sp.Eq(Y, explicit)),
            r"Aplicamos las operaciones inversas sobre la igualdad integrada para aislar $y$ en "
            r"función de $x$ y la constante $C$.",
        )
        return explicit_solution(explicit, note=None), builder.steps, lost

    potential = safe_simplify(left - right)
    builder.add(
        "Escribir la solución implícita",
        sp.latex(potential) + " = C",
        "No fue posible (o no es conveniente) despejar y; se conserva la "
        "solución implícita, que es igualmente válida.",
    )
    return implicit_solution(potential), builder.steps, lost


__all__ = ["solve"]
