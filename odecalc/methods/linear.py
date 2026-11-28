"""Solución de EDOs lineales de primer orden con factor integrante."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import linear_coeffs
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    add_transposition_step,
    explain_integration_rules,
)
from odecalc.methods.common import (
    explicit_solution,
    format_linear_equation,
    safe_integrate,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    coeffs = None
    if match is not None:
        if match.data.get("P") is not None:
            coeffs = (match.data["P"], match.data["Q"])
    if coeffs is None:
        coeffs = linear_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es lineal de primer orden.")

    p_expr, q_expr = (safe_simplify(item) for item in coeffs)
    std_eq = format_linear_equation("y'", p_expr, "y", q_expr)
    builder = StepBuilder()

    builder.add(
        "Escribir la forma estándar e identificar método y fórmula",
        std_eq,
        rf"¿Por qué este método? Tanto $y$ como $y'$ aparecen sólo a la primera potencia: "
        rf"es lineal de primer orden $y' + P(x)y = Q(x)$ con $P(x) = {sp.latex(p_expr)}$ y "
        rf"$Q(x) = {sp.latex(q_expr)}$. Fórmulas que usaremos: factor integrante "
        rf"$\mu(x) = e^{{\int P(x)\,dx}}$ y solución general "
        r"$y(x) = \frac{1}{\mu(x)}\left(\int \mu(x)Q(x)\,dx + C\right)$.",
        ascii_expr=f"y' + ({sp.sstr(p_expr)}) y = {sp.sstr(q_expr)}",
    )

    moved_rhs_term = safe_simplify(-p_expr * Y)
    if p_expr != 0 and safe_simplify(rhs - (moved_rhs_term + q_expr)) == 0:
        add_transposition_step(builder, "y'", rhs, moved_rhs_term, std_eq)

    integral_p = safe_integrate(p_expr, X)
    builder.add(
        "Integrar P(x) para el exponente del factor integrante",
        rf"\int P(x)\,dx = \int \left({sp.latex(p_expr)}\right)\,dx = {sp.latex(integral_p)}",
        explain_integration_rules(p_expr, X, integral_p),
    )

    mu = safe_simplify(sp.exp(integral_p))
    builder.add(
        "Calcular el factor integrante μ(x)",
        rf"\mu(x) = e^{{\int P(x)\,dx}} = e^{{{sp.latex(integral_p)}}} = {sp.latex(mu)}",
        r"Elevamos $e$ al resultado de $\int P(x)\,dx$. Por la regla de la cadena, "
        r"$\mu'(x) = \mu(x)P(x)$, lo que convierte el lado izquierdo multiplicado por $\mu$ en "
        r"una derivada exacta del producto: $\mu y' + \mu P y = (\mu y)'$.",
        ascii_expr=f"mu(x) = exp({sp.sstr(integral_p)}) = {sp.sstr(mu)}",
    )

    mu_q = safe_simplify(mu * q_expr)
    add_product_atomic_steps(
        builder,
        mu,
        q_expr,
        mu_q,
        title="Multiplicar la ecuación por μ(x)",
        lhs_latex=r"\left(\mu(x)\,y\right)'",
        intro_explanation=(
            r"Multiplicamos ambos miembros por $\mu(x) = " + sp.latex(mu) + r"$. "
            r"El lado izquierdo colapsa a $(\mu(x)y)'$ por regla del producto; en el derecho "
            r"calculamos $\mu(x)\cdot Q(x)$."
        ),
    )

    integral_muq = safe_integrate(mu_q, X)
    builder.add(
        "Integrar ambos miembros respecto a x",
        rf"\mu(x)y = \int \left({sp.latex(mu_q)}\right)\,dx = {sp.latex(integral_muq)} + C",
        r"La integral de la derivada $(\mu y)'$ es $\mu(x)y$. Para el miembro derecho: "
        + explain_integration_rules(mu_q, X, integral_muq)
        + r" Añadimos la constante de integración $+C$.",
        ascii_expr=f"mu*y = {sp.sstr(integral_muq)} + C",
    )

    inv_mu = safe_simplify(1 / mu)
    general = safe_simplify((C + integral_muq) / mu)
    add_product_atomic_steps(
        builder,
        inv_mu,
        C + integral_muq,
        general,
        title="Despejar y dividiendo entre μ(x)",
        lhs_latex="y",
        intro_explanation=(
            r"Dividimos entre $\mu(x)$ (equivalente a multiplicar por $\mu(x)^{-1} = "
            + sp.latex(inv_mu)
            + r"$, que cambia el signo del exponente si $\mu$ es exponencial). "
            r"Nótese que $e^{(\cdot)}$ nunca se anula en $\mathbb{R}$."
        ),
    )

    if integral_muq.has(sp.Integral):
        builder.add(
            "Nota sobre la integral no elemental",
            sp.latex(integral_muq),
            r"La integral $\int \mu(x)Q(x)\,dx$ no admite primitiva elemental; se conserva como "
            r"integral explícita en $x$ sin $y(x)$ en el integrando.",
        )

    return explicit_solution(general), builder.steps, []


__all__ = ["solve"]
