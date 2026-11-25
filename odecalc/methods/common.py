"""Utilidades compartidas por los solucionadores por método."""

from __future__ import annotations

import sympy as sp

from odecalc.models import Solution, Step
from odecalc.symbols import C, U, X, Y


def safe_simplify(expr: sp.Expr) -> sp.Expr:
    try:
        return sp.simplify(expr)
    except Exception:
        return expr


def safe_integrate(expr: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    """Integra o deja la integral explícita (nunca con ``y(x)`` dentro)."""

    try:
        result = sp.integrate(expr, variable)
        if result.has(sp.Integral):
            return result
        return result
    except Exception:
        return sp.Integral(expr, variable)


def safe_solve(equation: sp.Eq, symbol: sp.Symbol) -> list[sp.Expr]:
    try:
        return [sp.simplify(item) for item in sp.solve(equation, symbol)]
    except Exception:
        return []


def safe_solve_expr(expr: sp.Expr, symbol: sp.Symbol) -> list[sp.Expr]:
    try:
        return [sp.simplify(item) for item in sp.solve(expr, symbol)]
    except Exception:
        return []


def explicit_solution(expr: sp.Expr, note: str | None = None) -> Solution:
    expr = safe_simplify(expr)
    return Solution(
        form="explicit",
        expr=expr,
        latex=sp.latex(sp.Eq(Y, expr)),
        branch_note=note,
    )


def implicit_solution(
    potential: sp.Expr,
    value: sp.Expr | None = None,
    note: str | None = None,
) -> Solution:
    potential = safe_simplify(potential)
    value = C if value is None else value
    return Solution(
        form="implicit",
        expr=potential,
        value=value,
        constant=C,
        latex=sp.latex(potential) + " = " + sp.latex(value),
        branch_note=note,
    )


def make_step(
    number: int,
    title: str,
    latex: str,
    explanation: str,
    ascii_expr: str | None = None,
) -> Step:
    return Step(
        number=number,
        title=title,
        latex=latex,
        explanation=explanation,
        ascii=ascii_expr or latex,
    )


def equilibrium_solutions(
    h_expr: sp.Expr,
    *,
    variable: sp.Symbol = Y,
    note: str = "Solución de equilibrio perdida al dividir entre h(y).",
) -> list[Solution]:
    """Soluciones constantes donde ``h(y) = 0``."""

    roots = safe_solve_expr(h_expr, variable)
    solutions: list[Solution] = []
    for root in roots:
        if root.has(variable) or root in (sp.zoo, sp.nan, sp.oo, -sp.oo):
            continue
        try:
            if sp.im(sp.N(root)) != 0:
                continue
        except Exception:
            continue
        solutions.append(explicit_solution(root, note=note))
    return solutions


def standard_linear_solution(
    p_expr: sp.Expr,
    q_expr: sp.Expr,
    *,
    independent: sp.Symbol = X,
    dependent: sp.Symbol = Y,
    variable: sp.Symbol = U,
) -> tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
    """Resuelve ``v' + P v = Q`` y devuelve ``(v, mu, integral_P, integral_muQ)``.

    El resultado es explícito en la variable dependiente indicada (por
    defecto ``y``).
    """

    integral_p = safe_integrate(p_expr, independent)
    mu = safe_simplify(sp.exp(integral_p))
    integral_muq = safe_integrate(safe_simplify(mu * q_expr), independent)
    solution = safe_simplify((C + integral_muq) / mu)
    return solution.subs(dependent, variable).subs(variable, dependent), mu, integral_p, integral_muq


def solve_explicit_for(expr_relation: sp.Expr, symbol: sp.Symbol) -> sp.Expr | None:
    """Intenta despejar ``symbol`` de ``expr_relation = 0``."""

    candidates = safe_solve_expr(expr_relation, symbol)
    for candidate in candidates:
        if not candidate.has(symbol) and candidate not in (sp.zoo, sp.nan, sp.oo, -sp.oo):
            return candidate
    return None


__all__ = [
    "safe_simplify",
    "safe_integrate",
    "safe_solve",
    "safe_solve_expr",
    "explicit_solution",
    "implicit_solution",
    "make_step",
    "equilibrium_solutions",
    "standard_linear_solution",
    "solve_explicit_for",
]
