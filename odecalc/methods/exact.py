"""Solución de EDOs exactas ``M(x,y) dx + N(x,y) dy = 0``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import exact_parts, is_exact
from odecalc.methods.atomic_steps import (
    StepBuilder,
    describe_double_negative,
    explain_derivative_rules,
    explain_integration_rules,
)
from odecalc.methods.common import (
    format_differential_latex,
    implicit_solution,
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

    builder = StepBuilder()
    builder.add(
        "Escribir en forma diferencial e identificar M y N",
        format_differential_latex(m_expr, n_expr),
        rf"Método: ecuación diferencial exacta. Escribimos $M(x,y)\,dx + N(x,y)\,dy = 0$ con "
        rf"$M(x,y) = {sp.latex(m_expr)}$ y $N(x,y) = {sp.latex(n_expr)}$ (si el enunciado venía "
        rf"como $y' = -M/N$, al despejar $N\,dy + M\,dx = 0$ el signo menos pasa multiplicando). "
        r"Criterio de exactitud: $\frac{\partial M}{\partial y} = \frac{\partial N}{\partial x}$.",
        ascii_expr=f"({sp.sstr(m_expr)}) dx + ({sp.sstr(n_expr)}) dy = 0",
    )

    m_y = safe_simplify(sp.diff(m_expr, Y))
    n_x = safe_simplify(sp.diff(n_expr, X))
    builder.add(
        "Comprobar derivadas parciales cruzadas",
        rf"\frac{{\partial M}}{{\partial y}} = {sp.latex(m_y)}, \qquad "
        rf"\frac{{\partial N}}{{\partial x}} = {sp.latex(n_x)}",
        explain_derivative_rules(m_expr, Y, label="M")
        + " "
        + explain_derivative_rules(n_expr, X, label="N")
        + " Como ambas coinciden, existe una función potencial $F(x,y)$ tal que $F_x = M$ y $F_y = N$.",
    )

    full_potential, potential, g_prime, g_y = exact_potential(m_expr, n_expr)
    builder.add(
        "Integrar M(x,y) respecto a x para construir F(x,y)",
        rf"F(x,y) = \int \left({sp.latex(m_expr)}\right)\,dx + g(y) = {sp.latex(potential)} + g(y)",
        explain_integration_rules(m_expr, X, potential)
        + r" Al integrar respecto a $x$, cualquier función $g(y)$ que dependa sólo de $y$ tiene "
        r"derivada parcial respecto a $x$ igual a $0$, por lo que reemplaza a la constante ordinaria.",
    )

    f_y_partial = safe_simplify(sp.diff(potential, Y))
    dbl_neg = describe_double_negative(n_expr, f_y_partial) or ""
    builder.add(
        "Derivar F respecto a y e igualar con N(x,y)",
        rf"\frac{{\partial F}}{{\partial y}} = {sp.latex(f_y_partial)} + g'(y) = {sp.latex(n_expr)} "
        rf"\quad\Longrightarrow\quad g'(y) = {sp.latex(g_prime)}",
        explain_derivative_rules(potential, Y, label=r"\int M\,dx")
        + rf" Al igualar con $N = {sp.latex(n_expr)}$, los términos con $x$ se cancelan entre sí dejando "
        rf"$g'(y) = N - \frac{{\partial}}{{\partial y}}\int M\,dx = {sp.latex(g_prime)}$. {dbl_neg}".strip(),
    )

    builder.add(
        "Integrar g'(y) respecto a y",
        rf"g(y) = \int \left({sp.latex(g_prime)}\right)\,dy = {sp.latex(g_y)}",
        explain_integration_rules(g_prime, Y, g_y),
    )

    builder.add(
        "Escribir la familia implícita F(x,y) = C",
        sp.latex(full_potential) + " = C",
        r"La diferencial total es $dF = F_x\,dx + F_y\,dy = 0$, luego $F(x,y) = C$ es constante "
        "a lo largo de cada curva solución.",
    )
    return implicit_solution(full_potential), builder.steps, []


__all__ = ["solve"]
