"""Solución de EDOs de Bernoulli ``y' + P(x)y = Q(x)yⁿ`` para n real."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import bernoulli_coeffs
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    describe_double_negative,
    explain_integration_rules,
)
from odecalc.methods.common import (
    _signed_term_latex,
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
            coeffs = (match.data["P"], match.data["Q"], match.data["n"])
    if coeffs is None:
        coeffs = bernoulli_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es de Bernoulli.")

    p_expr, q_expr, n = (safe_simplify(item) for item in coeffs)
    alpha = safe_simplify(1 - n)
    if alpha == 0:
        raise ValueError("n = 1 no es una EDO de Bernoulli.")

    lhs_bernoulli = format_linear_equation("y'", p_expr, "y", sp.Integer(0)).rsplit(" =", 1)[0]
    rhs_bernoulli = _signed_term_latex(q_expr, rf"y^{{{sp.latex(n)}}}", include_plus=False).lstrip()

    builder = StepBuilder()
    builder.add(
        "Identificar la EDO de Bernoulli y su fórmula",
        f"{lhs_bernoulli} = {rhs_bernoulli}",
        rf"¿Por qué este método? Tiene la estructura de Bernoulli $y' + P(x)y = Q(x)y^n$ con "
        rf"$P(x) = {sp.latex(p_expr)}$, $Q(x) = {sp.latex(q_expr)}$ y exponente $n = {sp.latex(n)} \neq 0, 1$. "
        r"Fórmula de linealización: el cambio $v = y^{1-n}$ convierte la ecuación en lineal en $v$.",
    )

    neg_n_note = describe_double_negative(sp.Integer(1), n) or ""
    builder.add(
        "Calcular 1 − n y plantear la sustitución v = y^(1−n)",
        rf"v = y^{{1 - \left({sp.latex(n)}\right)}} = y^{{{sp.latex(alpha)}}}, \qquad "
        rf"\frac{{dv}}{{dx}} = \left({sp.latex(alpha)}\right)y^{{-\left({sp.latex(n)}\right)}} y'",
        rf"Evaluamos $1 - n = 1 - ({sp.latex(n)}) = {sp.latex(alpha)}$. {neg_n_note} "
        r"Por la regla de la cadena, derivar $v = y^{1-n}$ introduce el factor $(1-n)y^{-n}y'$. "
        r"Dividiendo la EDO original entre $y^n$ se obtiene $y^{-n}y' + P(x)y^{1-n} = Q(x)$.".strip(),
    )

    p_transformed = safe_simplify(alpha * p_expr)
    q_transformed = safe_simplify(alpha * q_expr)
    if p_expr != 0:
        add_product_atomic_steps(
            builder,
            alpha,
            p_expr,
            p_transformed,
            title="Calcular el coeficiente lineal (1−n)·P(x)",
            lhs_latex="P_v(x)",
            intro_explanation=r"Al multiplicar toda la ecuación por $1-n$ para formar $v'$, multiplicamos $P(x)$ por $1-n$.",
        )
    add_product_atomic_steps(
        builder,
        alpha,
        q_expr,
        q_transformed,
        title="Calcular el término independiente (1−n)·Q(x)",
        lhs_latex="Q_v(x)",
        intro_explanation=r"De igual forma multiplicamos $Q(x)$ por $1-n$ obteniendo la EDO lineal $v' + P_v(x)v = Q_v(x)$.",
    )
    builder.add(
        "Escribir la EDO lineal transformada en v",
        format_linear_equation("v'", p_transformed, "v", q_transformed),
        r"Ya es una ecuación lineal estándar en la incógnita $v(x)$, lista para el factor integrante.",
    )

    integral_p = safe_integrate(p_transformed, X)
    mu = safe_simplify(sp.exp(integral_p))
    mu_q = safe_simplify(mu * q_transformed)
    integral_muq = safe_integrate(mu_q, X)
    v_solution = safe_simplify((C + integral_muq) / mu)
    builder.add(
        "Resolver la EDO lineal en v mediante factor integrante",
        rf"\mu(x) = e^{{\int ({sp.latex(p_transformed)})\,dx}} = {sp.latex(mu)} \quad\Longrightarrow\quad v = {sp.latex(v_solution)}",
        "En $\\mu(x)$ — "
        + explain_integration_rules(p_transformed, X, integral_p)
        + " En $\\int \\mu(x)Q_v(x)\\,dx$ — "
        + explain_integration_rules(mu_q, X, integral_muq)
        + rf" Despejamos $v = \frac{{{sp.latex(C + integral_muq)}}}{{{sp.latex(mu)}}}$.",
    )

    exponent = safe_simplify(1 / alpha)
    y_solution = safe_simplify(v_solution**exponent)
    builder.add(
        "Volver a la variable original y = v^(1/(1−n))",
        sp.latex(sp.Eq(Y, y_solution)),
        rf"Como $v = y^{{{sp.latex(alpha)}}}$, elevamos ambos lados al recíproco $\frac{{1}}{{1-n}} = {sp.latex(exponent)}$ "
        r"para despejar $y(x)$. Deben respetarse las ramas reales de la potencia.",
    )

    singular: list[Solution] = []
    try:
        if n.is_positive:
            singular.append(
                explicit_solution(
                    0,
                    note="y = 0 es una solución de equilibrio que se pierde al "
                    "dividir entre yⁿ.",
                )
            )
            builder.add(
                "Registrar solución de equilibrio y = 0",
                r"y = 0",
                rf"Como $n = {sp.latex(n)} > 0$, la función constante $y = 0$ cumple $0 + 0 = 0$ en la "
                r"ecuación original y se perdió al dividir entre $y^n$.",
            )
    except Exception:
        pass
    return (
        explicit_solution(
            y_solution,
            note="La potencia final puede requerir elegir la rama real; "
            "la verificación numérica comprueba la rama principal.",
        ),
        builder.steps,
        singular,
    )


__all__ = ["solve"]
