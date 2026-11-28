"""Solución mediante factores integrantes μ(x), μ(y), μ(xy), μ(x+y), μ(x²+y²)."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    describe_double_negative,
    explain_derivative_rules,
    explain_integration_rules,
)
from odecalc.methods.common import (
    format_differential_latex,
    implicit_solution,
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
_LATEX_LABELS = {
    "integrating_factor_x": r"\mu(x)",
    "integrating_factor_y": r"\mu(y)",
    "integrating_factor_xy": r"\mu(xy)",
    "integrating_factor_x_plus_y": r"\mu(x+y)",
    "integrating_factor_x2_plus_y2": r"\mu(x^{2}+y^{2})",
}
_RATIO_FORMULAS = {
    "integrating_factor_x": r"\frac{\frac{\partial M}{\partial y} - \frac{\partial N}{\partial x}}{N}",
    "integrating_factor_y": r"\frac{\frac{\partial N}{\partial x} - \frac{\partial M}{\partial y}}{M}",
    "integrating_factor_xy": r"\frac{\frac{\partial N}{\partial x} - \frac{\partial M}{\partial y}}{x M - y N}",
    "integrating_factor_x_plus_y": r"\frac{\frac{\partial N}{\partial x} - \frac{\partial M}{\partial y}}{M - N}",
    "integrating_factor_x2_plus_y2": r"\frac{\frac{\partial N}{\partial x} - \frac{\partial M}{\partial y}}{2(x N - y M)}",
}


def solve(match: Match) -> tuple[Solution, list[Step], list[Solution]]:
    m_expr = safe_simplify(match.data["M"])
    n_expr = safe_simplify(match.data["N"])
    mu = safe_simplify(match.data["mu"])
    u_expr = match.data.get("u", X)
    label = _LABELS.get(match.method, match.method)
    latex_label = _LATEX_LABELS.get(match.method, sp.latex(sp.Symbol("mu")))
    ratio_formula = _RATIO_FORMULAS.get(match.method, r"\frac{\mu'(u)}{\mu(u)}")

    m_mult = safe_simplify(mu * m_expr)
    n_mult = safe_simplify(mu * n_expr)
    m_y = safe_simplify(sp.diff(m_expr, Y))
    n_x = safe_simplify(sp.diff(n_expr, X))
    diff_mn = safe_simplify(m_y - n_x)

    builder = StepBuilder()
    builder.add(
        "Escribir en forma diferencial e identificar M y N",
        format_differential_latex(m_expr, n_expr),
        rf"¿Por qué este método? Escribimos $M\,dx + N\,dy = 0$ con $M = {sp.latex(m_expr)}$ y "
        rf"$N = {sp.latex(n_expr)}$ para comprobar si es exacta.",
    )

    dbl_neg = describe_double_negative(m_y, n_x) or ""
    builder.add(
        "Comprobar que no es exacta",
        rf"\frac{{\partial M}}{{\partial y}} = {sp.latex(m_y)}, \quad "
        rf"\frac{{\partial N}}{{\partial x}} = {sp.latex(n_x)} \quad\Longrightarrow\quad "
        rf"\frac{{\partial M}}{{\partial y}} - \frac{{\partial N}}{{\partial x}} = {sp.latex(diff_mn)} \neq 0",
        explain_derivative_rules(m_expr, Y, label="M")
        + " "
        + explain_derivative_rules(n_expr, X, label="N")
        + f" Como las derivadas cruzadas no coinciden, la ecuación no es exacta. {dbl_neg}".strip(),
    )

    builder.add(
        f"Calcular el factor integrante {label}",
        rf"\frac{{\mu'(u)}}{{\mu(u)}} = {ratio_formula} \quad\Longrightarrow\quad {latex_label} = {sp.latex(mu)}",
        rf"La fórmula de razón correspondiente al ansatz $u = {sp.latex(u_expr)}$ depende únicamente "
        rf"de $u$; integrando respecto a $u$ y exponenciando $\mu(u) = e^{{\int (\mu'/\mu)\,du}}$ se "
        rf"obtiene ${latex_label} = {sp.latex(mu)}$.",
        ascii_expr=f"{label} = {sp.sstr(mu)}",
    )

    add_product_atomic_steps(
        builder,
        mu,
        m_expr,
        m_mult,
        title="Multiplicar M(x,y) por μ",
        lhs_latex=r"\tilde{M}(x,y)",
        intro_explanation=r"Multiplicamos el coeficiente de $dx$ por el factor integrante para obtener $\tilde{M} = \mu M$.",
    )
    add_product_atomic_steps(
        builder,
        mu,
        n_expr,
        n_mult,
        title="Multiplicar N(x,y) por μ",
        lhs_latex=r"\tilde{N}(x,y)",
        intro_explanation=r"Multiplicamos el coeficiente de $dy$ por el factor integrante para obtener $\tilde{N} = \mu N$.",
    )

    tilde_my = safe_simplify(sp.diff(m_mult, Y))
    builder.add(
        "Verificar exactitud de la nueva ecuación",
        rf"{format_differential_latex(m_mult, n_mult)}, \qquad \frac{{\partial \tilde{{M}}}}{{\partial y}} = \frac{{\partial \tilde{{N}}}}{{\partial x}} = {sp.latex(tilde_my)}",
        "Tras cancelar factores comunes y aplicar la regla de signos, las derivadas cruzadas de la "
        "ecuación multiplicada coinciden exactamente: ya es una EDO exacta.",
    )

    from odecalc.methods.exact import exact_potential

    full_potential, potential, g_prime, g_y = exact_potential(m_mult, n_mult)
    gy_tex = sp.latex(g_y)
    sum_fg_tex = (
        f"{sp.latex(potential)} - {gy_tex.lstrip()[1:].lstrip()}"
        if gy_tex.lstrip().startswith("-")
        else f"{sp.latex(potential)} + {gy_tex}"
    )
    builder.add(
        "Construir el potencial F(x,y) de la ecuación exacta",
        rf"F(x,y) = \int \tilde{{M}}\,dx + g(y) = {sum_fg_tex} = {sp.latex(full_potential)}",
        explain_integration_rules(m_mult, X, potential)
        + rf" Igualando $F_y = \tilde{{N}}$ obtenemos $g'(y) = {sp.latex(g_prime)}$ y al integrar $g(y) = {sp.latex(g_y)}$.",
    )
    builder.add(
        "Escribir la solución general implícita",
        rf"{sp.latex(full_potential)} = C",
        r"Las curvas solución son las curvas de nivel $F(x,y) = C$ de la ecuación ya exacta.",
    )
    return implicit_solution(full_potential), builder.steps, []


__all__ = ["solve"]
