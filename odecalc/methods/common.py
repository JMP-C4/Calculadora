"""Utilidades compartidas por los solucionadores por método."""

from __future__ import annotations

import sympy as sp

from odecalc.models import Solution, Step
from odecalc.symbols import C, DY, U, X, Y


def latex_with_prime(expr: sp.Expr) -> str:
    """Convierte ``expr`` a LaTeX reemplazando ``Dy`` por ``y'``."""

    rendered = sp.latex(expr.subs(DY, sp.Symbol("y'")))
    return rendered.replace("y'^{", r"\left(y'\right)^{")


def format_linear_combo_latex(
    a_expr: sp.Expr,
    b_expr: sp.Expr,
    x_var: str = "x",
    y_var: str = "y",
) -> str:
    """Formatea ``a*x + b*y`` en LaTeX evitando coeficientes unitarios ``1x``."""

    def term(coeff: sp.Expr, var: str, *, first: bool) -> str:
        coeff = safe_simplify(coeff)
        if coeff == 0:
            return ""
        tex = sp.latex(coeff)
        if coeff == 1:
            body = var
            sign = "+"
        elif coeff == -1:
            body = var
            sign = "-"
        elif tex.startswith("-"):
            body = f"{tex[1:].lstrip()}\\,{var}" if not isinstance(coeff, sp.Add) else f"\\left({tex[1:].lstrip()}\\right)\\,{var}"
            sign = "-"
        else:
            inner = f"\\left({tex}\\right)" if isinstance(coeff, sp.Add) else tex
            body = f"{inner}{var}" if coeff.is_Integer else f"{inner}\\,{var}"
            sign = "+"
        if first:
            return body if sign == "+" else f"-{body}"
        return f" + {body}" if sign == "+" else f" - {body}"

    first_part = term(a_expr, x_var, first=True)
    second_part = term(b_expr, y_var, first=not first_part)
    return (first_part + second_part) or "0"


def _signed_term_latex(coeff: sp.Expr, dep_latex: str, *, include_plus: bool = True) -> str:
    """Formatea un término ``coeff * dep_latex`` con signo limpio."""

    coeff = safe_simplify(coeff)
    if coeff == 1:
        body = dep_latex
        sign = "+"
    elif coeff == -1:
        body = dep_latex
        sign = "-"
    else:
        tex = sp.latex(coeff)
        if tex.startswith("-"):
            pos_coeff = safe_simplify(-coeff)
            pos_tex = sp.latex(pos_coeff)
            if isinstance(pos_coeff, sp.Add):
                pos_tex = rf"\left({pos_tex}\right)"
            body = dep_latex if pos_coeff == 1 else rf"{pos_tex}\,{dep_latex}"
            sign = "-"
        else:
            if isinstance(coeff, sp.Add):
                tex = rf"\left({tex}\right)"
            body = rf"{tex}\,{dep_latex}"
            sign = "+"
    if sign == "-":
        return f" - {body}"
    return f" + {body}" if include_plus else body


def format_linear_equation(
    deriv_latex: str,
    p_expr: sp.Expr,
    dep_latex: str,
    q_expr: sp.Expr,
) -> str:
    """Formatea ``y' + P(x)y = Q(x)`` sin signos dobles ``+ -`` ni ``1\\,y``."""

    p_clean = safe_simplify(p_expr)
    q_clean = safe_simplify(q_expr)
    lhs = deriv_latex
    if p_clean != 0:
        lhs += _signed_term_latex(p_clean, dep_latex, include_plus=True)
    return f"{lhs} = {sp.latex(q_clean)}"


def format_riccati_rhs(q0: sp.Expr, q1: sp.Expr, q2: sp.Expr) -> str:
    """Formatea ``q0 + q1 y + q2 y^2`` evitando ``+ -``, ``0 y`` y ``1 y``."""

    q0_clean, q1_clean, q2_clean = (safe_simplify(item) for item in (q0, q1, q2))
    parts: list[str] = []
    if q0_clean != 0:
        parts.append(sp.latex(q0_clean))
    if q1_clean != 0:
        term = _signed_term_latex(q1_clean, "y", include_plus=bool(parts))
        parts.append(term.lstrip() if not parts else term)
    if q2_clean != 0:
        term = _signed_term_latex(q2_clean, "y^{2}", include_plus=bool(parts))
        parts.append(term.lstrip() if not parts else term)
    return "".join(parts) or "0"


def format_shift_latex(upper_var: str, lower_var: str, shift: sp.Expr) -> str:
    """Formatea traslaciones ``X = x - h`` sin ``x - -1``."""

    shift_clean = safe_simplify(shift)
    if shift_clean == 0:
        return f"{upper_var} = {lower_var}"
    tex = sp.latex(shift_clean)
    if tex.startswith("-"):
        return f"{upper_var} = {lower_var} + {sp.latex(safe_simplify(-shift_clean))}"
    return f"{upper_var} = {lower_var} - {tex}"


def format_differential_latex(m_expr: sp.Expr, n_expr: sp.Expr) -> str:
    """Formatea ``M(x,y)\\,dx + N(x,y)\\,dy = 0`` con paréntesis necesarios."""

    def _factor(expr: sp.Expr) -> str:
        tex = sp.latex(expr)
        return rf"\left({tex}\right)" if isinstance(expr, sp.Add) else tex

    m_tex = _factor(m_expr)
    if n_expr == 0:
        return rf"{m_tex}\,dx = 0"
    n_tex = sp.latex(n_expr)
    if not isinstance(n_expr, sp.Add) and n_tex.startswith("-"):
        neg_n = _factor(safe_simplify(-n_expr))
        return rf"{m_tex}\,dx - {neg_n}\,dy = 0"
    return rf"{m_tex}\,dx + {_factor(n_expr)}\,dy = 0"


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
            imag = complex(sp.N(root)).imag
            if abs(imag) > 1e-9:
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
    "latex_with_prime",
    "format_linear_combo_latex",
    "format_linear_equation",
    "format_riccati_rhs",
    "format_shift_latex",
    "format_differential_latex",
]
