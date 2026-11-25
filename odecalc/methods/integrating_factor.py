"""Solución mediante factores integrantes μ(x), μ(y), μ(xy), μ(x+y), μ(x²+y²)."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.common import (
    implicit_solution,
    make_step,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import X, Y

_LABELS = {
    "integrating_factor_x": "μ(x)",
    "integrating_factor_y": "μ(y)",
    "integrating_factor_xy": "μ(xy)",
    "integrating_factor_x_plus_y": "μ(x+y)",
    "integrating_factor_x2_plus_y2": "μ(x²+y²)",
}


def solve(match: Match) -> tuple[Solution, list[Step], list[Solution]]:
    m_expr = safe_simplify(match.data["M"])
    n_expr = safe_simplify(match.data["N"])
    mu = safe_simplify(match.data["mu"])
    u_expr = match.data.get("u", X)
    label = _LABELS.get(match.method, match.method)

    m_mult = safe_simplify(mu * m_expr)
    n_mult = safe_simplify(mu * n_expr)
    m_y = safe_simplify(sp.diff(m_expr, Y))
    n_x = safe_simplify(sp.diff(n_expr, X))

    steps: list[Step] = [
        make_step(
            1,
            "Escribir la forma diferencial",
            sp.latex(m_expr) + r"\,dx + " + sp.latex(n_expr) + r"\,dy = 0",
            "Se identifican M y N para comprobar la exactitud.",
        ),
        make_step(
            2,
            "Comprobar que no es exacta",
            rf"\frac{{\partial M}}{{\partial y}} - \frac{{\partial N}}{{\partial x}} = "
            f"{sp.latex(safe_simplify(m_y - n_x))}",
            "Las derivadas cruzadas no coinciden, por lo que se busca un factor integrante.",
        ),
        make_step(
            3,
            f"Construir el factor {label}",
            f"{label} = {sp.latex(mu)}",
            f"La razón que define el factor depende sólo de u = {sp.latex(u_expr)}; "
            "al multiplicar, la ecuación resultante es exacta.",
            ascii_expr=f"{label} = {sp.sstr(mu)}",
        ),
        make_step(
            4,
            "Multiplicar la ecuación",
            sp.latex(m_mult) + r"\,dx + " + sp.latex(n_mult) + r"\,dy = 0",
            "Se multiplican M y N por el factor integrante.",
        ),
    ]

    from odecalc.methods.exact import exact_potential

    full_potential, potential, g_prime, g_y = exact_potential(m_mult, n_mult)
    steps.extend(
        [
            make_step(
                5,
                "Integrar la ecuación exacta",
                rf"F(x,y) = {sp.latex(full_potential)} = C",
                "La nueva ecuación es exacta; su potencial F proporciona la "
                "solución general implícita.",
            )
        ]
    )
    return implicit_solution(full_potential), steps, []


__all__ = ["solve"]
