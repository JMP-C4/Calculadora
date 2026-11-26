"""Solución de ecuaciones de Clairaut ``y = x y' + f(y')``."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.common import (
    explicit_solution,
    latex_with_prime,
    make_step,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, DY, P, X, Y


def solve(match: Match) -> tuple[Solution, list[Step], list[Solution]]:
    phi = safe_simplify(match.data.get("phi", DY))
    psi = safe_simplify(match.data.get("psi"))
    if sp.simplify(phi - DY) != 0:
        raise ValueError(
            "La ecuación es de Lagrange, no de Clairaut. Este método aún no "
            "genera una solución explícita; se usará el respaldo simbólico."
        )

    general = safe_simplify(C * X + psi.subs(DY, C))
    steps: list[Step] = [
        make_step(
            1,
            "Identificar la ecuación de Clairaut",
            latex_with_prime(sp.Eq(Y, X * DY + psi)),
            rf"Tiene la forma $y = x y' + f(y')$, con $f(p) = {sp.latex(psi.subs(DY, P))}$.",
        ),
        make_step(
            2,
            "Derivar respecto a x",
            r"y' = y' + \left(x + f'(y')\right)y''",
            "Al derivar ambos lados y simplificar queda "
            r"$\left(x + f'(y')\right) y'' = 0$.",
        ),
        make_step(
            3,
            "Caso y'' = 0",
            sp.latex(sp.Eq(Y, general)),
            r"Si $y'' = 0$, entonces $y' = C$ es constante y se obtiene la familia "
            r"de rectas $y = Cx + f(C)$.",
        ),
    ]

    singular: list[Solution] = []
    try:
        derivative = safe_simplify(sp.diff(psi, DY))
        for p_value in sp.solve(sp.Eq(X + derivative, 0), DY):
            if p_value.has(DY) or p_value in (sp.zoo, sp.nan, sp.oo, -sp.oo):
                continue
            singular_expr = safe_simplify(X * p_value + psi.subs(DY, p_value))
            if singular_expr.has(DY):
                continue
            singular.append(
                explicit_solution(
                    singular_expr,
                    note="Solución singular: envolvente de la familia de rectas, "
                    "no se obtiene fijando un valor de C.",
                )
            )
    except Exception:
        pass

    if singular:
        steps.append(
            make_step(
                4,
                "Caso x + f'(y') = 0",
                sp.latex(sp.Eq(Y, singular[0].expr)),
                r"Al eliminar $y'$ entre $x + f'(y') = 0$ y la ecuación original se "
                "obtiene la solución singular (envolvente).",
            )
        )

    return explicit_solution(general), steps, singular


__all__ = ["solve"]
