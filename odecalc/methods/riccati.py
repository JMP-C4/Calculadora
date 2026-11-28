"""Solución de EDOs de Riccati ``y' = q₀(x) + q₁(x)y + q₂(x)y²``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import riccati_coeffs
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    describe_double_negative,
    explain_integration_rules,
)
from odecalc.methods.common import (
    explicit_solution,
    format_linear_equation,
    format_riccati_rhs,
    safe_integrate,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, X, Y


def _residual(particular: sp.Expr, q0: sp.Expr, q1: sp.Expr, q2: sp.Expr) -> sp.Expr:
    return safe_simplify(
        sp.diff(particular, X)
        - (q0 + q1 * particular + q2 * particular**2)
    )


def find_particular(q0: sp.Expr, q1: sp.Expr, q2: sp.Expr) -> sp.Expr | None:
    """Busca una solución particular polinómica de la ecuación de Riccati."""

    candidates: list[sp.Expr] = []

    # Constante.
    for root in sp.solve(sp.Eq(q0 + q1 * Y + q2 * Y**2, 0), Y):
        if not root.has(Y) and not root.has(X):
            candidates.append(safe_simplify(root))

    # Lineal y = a x + b.
    a, b = sp.symbols("a b", real=True)
    linear = a * X + b
    polynomial = sp.Poly(sp.expand(_residual(linear, q0, q1, q2)), X)
    equations = [sp.Eq(coefficient, 0) for coefficient in polynomial.all_coeffs()]
    for solution in sp.solve(equations, [a, b], dict=True):
        candidate = safe_simplify(linear.subs(solution))
        if not candidate.has(a, b):
            candidates.append(candidate)

    # Cuadrática y = a x² + b x + c.
    c = sp.Symbol("c", real=True)
    quadratic = a * X**2 + b * X + c
    polynomial = sp.Poly(sp.expand(_residual(quadratic, q0, q1, q2)), X)
    equations = [sp.Eq(coefficient, 0) for coefficient in polynomial.all_coeffs()]
    for solution in sp.solve(equations, [a, b, c], dict=True):
        candidate = safe_simplify(quadratic.subs(solution))
        if not candidate.has(a, b, c):
            candidates.append(candidate)

    for candidate in candidates:
        if candidate in (sp.zoo, sp.nan, sp.oo, -sp.oo):
            continue
        if _residual(candidate, q0, q1, q2) == 0:
            return candidate
    return None


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    coeffs = None
    if match is not None:
        if match.data.get("q0") is not None:
            coeffs = (match.data["q0"], match.data["q1"], match.data["q2"])
    if coeffs is None:
        coeffs = riccati_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es de Riccati.")

    q0, q1, q2 = (safe_simplify(item) for item in coeffs)
    particular = find_particular(q0, q1, q2)
    if particular is None:
        raise ValueError(
            "No se encontró una solución particular polinómica; se intentará "
            "otro método o el respaldo simbólico."
        )

    builder = StepBuilder()
    builder.add(
        "Identificar la EDO de Riccati y su fórmula de linealización",
        f"y' = {format_riccati_rhs(q0, q1, q2)}",
        rf"¿Por qué este método? Tiene forma cuadrática en $y$: "
        rf"$y' = q_0(x) + q_1(x)y + q_2(x)y^2$ con $q_0 = {sp.latex(q0)}$, "
        rf"$q_1 = {sp.latex(q1)}$ y $q_2 = {sp.latex(q2)} \neq 0$. "
        r"Fórmula: conocida una solución particular $y_p$, la sustitución "
        r"$y = y_p + \frac{1}{v}$ transforma la ecuación en lineal en $v$.",
    )

    yp_deriv = safe_simplify(sp.diff(particular, X))
    builder.add(
        "Encontrar y comprobar una solución particular yₚ(x)",
        rf"y_p(x) = {sp.latex(particular)}, \qquad y_p' = {sp.latex(yp_deriv)}",
        "Probamos soluciones polinómicas de grado bajo ($c$, $ax+b$, $ax^2+bx+c$) igualando "
        "coeficientes hasta verificar $y_p' - (q_0 + q_1 y_p + q_2 y_p^2) = 0$.",
    )

    p_expr = safe_simplify(q1 + 2 * q2 * particular)
    q_linear = safe_simplify(-q2)
    dbl_neg_q = describe_double_negative(sp.Integer(0), q2) or ""
    builder.add(
        "Sustituir y = yₚ + 1/v y reducir a EDO lineal en v",
        rf"y' = y_p' - \frac{{v'}}{{v^2}} \quad\Longrightarrow\quad {format_linear_equation('v\'', p_expr, 'v', q_linear)}",
        r"Al reemplazar $y = y_p + v^{-1}$ y $y' = y_p' - v^{-2}v'$, los términos sin $v$ "
        r"($y_p' - q_0 - q_1 y_p - q_2 y_p^2 = 0$) se cancelan. Multiplicando ambos miembros "
        r"por $-v^2$ (regla de signos $-v^2\cdot(-v^{-2}v') = +v'$) queda "
        rf"$v' + \left(q_1 + 2q_2 y_p\right)v = -q_2$, con $P_v = {sp.latex(p_expr)}$ y $Q_v = {sp.latex(q_linear)}$. "
        + dbl_neg_q,
    )

    integral_p = safe_integrate(p_expr, X)
    mu = safe_simplify(sp.exp(integral_p))
    mu_q = safe_simplify(mu * q_linear)
    add_product_atomic_steps(
        builder,
        mu,
        q_linear,
        mu_q,
        title="Calcular μ(x) y el producto μ(x)·Qᵥ(x)",
        lhs_latex=r"\left(\mu(x)\,v\right)'",
        intro_explanation=rf"Factor integrante $\mu(x) = e^{{\int ({sp.latex(p_expr)})\,dx}} = {sp.latex(mu)}$. "
        + explain_integration_rules(p_expr, X, integral_p)
        + r" Multiplicamos ahora por $Q_v(x) = -q_2(x)$.",
    )

    integral_muq = safe_integrate(mu_q, X)
    v_solution = safe_simplify((C + integral_muq) / mu)
    builder.add(
        "Integrar y obtener v(x)",
        rf"\mu(x)v = {sp.latex(integral_muq)} + C \quad\Longrightarrow\quad v = {sp.latex(v_solution)}",
        explain_integration_rules(mu_q, X, integral_muq)
        + r" Luego despejamos $v(x)$ dividiendo entre $\mu(x)$.",
    )

    general = safe_simplify(particular + 1 / v_solution)
    builder.add(
        "Volver a y = yₚ + 1/v",
        sp.latex(sp.Eq(Y, general)),
        r"Reemplazamos $\frac{1}{v}$ en $y = y_p + \frac{1}{v}$ y simplificamos fracciones.",
    )
    return explicit_solution(general), builder.steps, []


__all__ = ["solve", "find_particular"]
