"""Solución de EDOs homogéneas de grado cero con ``y = u x``."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_transposition_step,
    explain_integration_rules,
)
from odecalc.methods.common import (
    explicit_solution,
    implicit_solution,
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

    builder = StepBuilder()
    builder.add(
        "Comprobar homogeneidad y elegir sustitución y = u x",
        sp.latex(sp.Eq(sp.Symbol("y"), U * X)),
        r"¿Por qué este método? Al escalar $(x,y) \to (tx, ty)$ todos los factores en $t$ "
        r"se cancelan ($f(tx,ty)=f(x,y)$: grado $0$). Fórmula: $y = ux$ reduce la EDO a "
        r"variables separables en $u$ y $x$.",
    )
    builder.add(
        "Derivar la sustitución con la regla del producto",
        r"\frac{dy}{dx} = u + x\frac{du}{dx}",
        r"Derivamos $y = u(x)\cdot x$ respecto a $x$ usando $(uv)' = u'v + uv'$, con $x' = 1$.",
    )
    builder.add(
        "Sustituir y = u x y cancelar x en el miembro derecho",
        f"u + x\\frac{{du}}{{dx}} = {sp.latex(transformed)}",
        rf"Reemplazamos $y$ por $ux$ en $f(x,y)$ y cancelamos los factores comunes de $x$; "
        rf"sólo permanece $\phi(u) = {sp.latex(transformed)}$.",
    )

    difference = safe_simplify(transformed - U)
    if difference == 0:
        builder.add(
            "Integrar la pendiente nula du/dx = 0",
            r"u = C \quad\Longrightarrow\quad y = Cx",
            r"Al restar $u$ en ambos lados resulta $x\frac{du}{dx} = 0$, luego $u = C$ y $y = Cx$.",
        )
        return explicit_solution(C * X), builder.steps, []

    add_transposition_step(
        builder,
        r"u + x\frac{du}{dx}",
        transformed,
        U,
        rf"x\frac{{du}}{{dx}} = {sp.latex(difference)}",
        title="Restar u en ambos miembros",
        from_left=True,
    )

    inv_diff = safe_simplify(1 / difference)
    builder.add(
        "Separar variables u y x",
        rf"\left({sp.latex(inv_diff)}\right)\,du = \frac{{dx}}{{x}}",
        r"Dividimos entre $\phi(u) - u$ y dividimos entre $x$ (multiplicando por $dx$) para "
        r"separar completamente las variables.",
    )

    left = safe_integrate(inv_diff, U)
    right = safe_integrate(1 / X, X)
    builder.add(
        "Integrar ambos miembros",
        f"{sp.latex(left)} = {sp.latex(right)} + C",
        "En $u$ — "
        + explain_integration_rules(inv_diff, U, left)
        + " En $x$ — "
        + explain_integration_rules(1 / X, X, right)
        + r" Añadimos la constante $+C$.",
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
        builder.add(
            "Volver a las variables originales x, y",
            sp.latex(sp.Eq(Y, solution)),
            r"Sustituimos $u = \frac{y}{x}$ y multiplicamos por $x$ para despejar $y(x)$.",
        )
        return explicit_solution(solution), builder.steps, []

    potential = safe_simplify(left.subs(U, Y / X) - right)
    builder.add(
        "Escribir la solución implícita",
        sp.latex(potential) + " = C",
        r"No se pudo despejar $u$ explícitamente; sustituimos $u = \frac{y}{x}$ y conservamos "
        r"la relación implícita.",
    )
    return implicit_solution(potential), builder.steps, []


__all__ = ["solve"]
