"""Solución de EDOs de Riccati ``y' = q₀(x) + q₁(x)y + q₂(x)y²``."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import riccati_coeffs
from odecalc.methods.common import (
    explicit_solution,
    format_linear_equation,
    format_riccati_rhs,
    make_step,
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

    steps: list[Step] = [
        make_step(
            1,
            "Identificar la EDO de Riccati",
            f"y' = {format_riccati_rhs(q0, q1, q2)}",
            r"Es una EDO de Riccati con coeficientes $q_0$, $q_1$ y $q_2$.",
        ),
        make_step(
            2,
            "Encontrar una solución particular",
            sp.latex(sp.Eq(Y, particular)),
            "Se propone un polinomio de grado bajo y se ajustan sus coeficientes "
            "hasta satisfacer la ecuación. Conocida una solución particular, "
            "la ecuación se linealiza.",
        ),
    ]

    p_expr = safe_simplify(q1 + 2 * q2 * particular)
    q_linear = safe_simplify(-q2)
    steps.append(
        make_step(
            3,
            "Sustituir y = yₚ + 1/v",
            format_linear_equation("v'", p_expr, "v", q_linear),
            r"La sustitución $y = y_p + \frac{1}{v}$ transforma la Riccati en una EDO "
            r"lineal para $v$.",
        )
    )

    integral_p = safe_integrate(p_expr, X)
    mu = safe_simplify(sp.exp(integral_p))
    integral_muq = safe_integrate(safe_simplify(mu * q_linear), X)
    v_solution = safe_simplify((C + integral_muq) / mu)
    steps.append(
        make_step(
            4,
            "Resolver la EDO lineal en v",
            rf"v = {sp.latex(v_solution)}",
            "Se aplica el factor integrante a la ecuación lineal resultante.",
        )
    )

    general = safe_simplify(particular + 1 / v_solution)
    steps.append(
        make_step(
            5,
            "Volver a y",
            sp.latex(sp.Eq(Y, general)),
            r"Se despeja $y = y_p + \frac{1}{v}$.",
        )
    )
    return explicit_solution(general), steps, []


__all__ = ["solve", "find_particular"]
