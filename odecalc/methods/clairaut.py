"""Solución de ecuaciones de Clairaut ``y = x y' + f(y')``."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.atomic_steps import StepBuilder, explain_derivative_rules
from odecalc.methods.common import (
    explicit_solution,
    latex_with_prime,
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
    builder = StepBuilder()
    builder.add(
        "Identificar la ecuación de Clairaut y su estructura",
        latex_with_prime(sp.Eq(Y, X * DY + psi)),
        rf"¿Por qué este método? Tiene la forma exacta $y = x y' + \psi(y')$ con "
        rf"$\psi(p) = {sp.latex(psi.subs(DY, P))}$. Al derivar respecto a $x$, un factor "
        r"$y'$ se cancela en ambos miembros dando lugar a una familia general de rectas y a "
        r"una posible envolvente singular.",
    )
    builder.add(
        "Derivar respecto a x (regla del producto y cadena) y factorizar",
        r"y' = y' + x\,y'' + \psi'(y')\,y'' \quad\Longrightarrow\quad \left(x + \psi'(y')\right)y'' = 0",
        r"Derivamos $x y'$ con $(uv)' = y' + x y''$ y $\psi(y')$ con regla de la cadena "
        r"$\psi'(y')y''$. Restamos $y'$ a ambos lados (se cancela $y' - y' = 0$) y sacamos "
        r"factor común $y''$. Un producto es $0$ cuando alguno de sus dos factores se anula.",
    )
    builder.add(
        "Caso 1: y'' = 0 (familia general de rectas)",
        sp.latex(sp.Eq(Y, general)),
        r"Si $y'' = 0$, integrando $\int 0\,dx = C$ queda $y' = C$ constante; sustituyendo $y' = C$ en "
        r"la ecuación original resulta la familia $y = Cx + \psi(C)$.",
    )

    singular: list[Solution] = []
    derivative = sp.Integer(0)
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
        psi_p = psi.subs(DY, P)
        eq_p = sp.Eq(X + derivative.subs(DY, P), 0)
        builder.add(
            "Caso 2: x + f'(y') = 0 (solución singular / envolvente)",
            rf"{sp.latex(eq_p)} \quad\Longrightarrow\quad {sp.latex(sp.Eq(Y, singular[0].expr))}",
            explain_derivative_rules(psi_p, P, label=r"\psi(p)")
            + r" Igualamos $x + \psi'(p) = 0$ para despejar el parámetro $p(x)$ en función de $x$ "
            r"(cambiando signo al transponer) y sustituimos en $y = xp + \psi(p)$ para obtener "
            "la curva envolvente tangente a toda la familia.",
        )

    return explicit_solution(general), builder.steps, singular


__all__ = ["solve"]
