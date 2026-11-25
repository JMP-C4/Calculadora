"""EDOs reducibles a homogéneas mediante traslación o sustitución lineal."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import reducible_linear_coeffs
from odecalc.methods.common import (
    explicit_solution,
    implicit_solution,
    make_step,
    safe_integrate,
    safe_solve_expr,
    safe_simplify,
)
from odecalc.models import Match, Solution, Step
from odecalc.symbols import C, U, V, X, Y


def solve(rhs: sp.Expr, match: Match | None = None) -> tuple[Solution, list[Step], list[Solution]]:
    coeffs = None
    if match is not None and match.data.get("a1") is not None:
        data = match.data
        coeffs = (
            data["a1"],
            data["b1"],
            data["c1"],
            data["a2"],
            data["b2"],
            data["c2"],
        )
    if coeffs is None:
        coeffs = reducible_linear_coeffs(rhs)
    if coeffs is None:
        raise ValueError("La ecuación no es reducible a homogénea.")

    a1, b1, c1, a2, b2, c2 = (safe_simplify(item) for item in coeffs)
    determinant = safe_simplify(a1 * b2 - a2 * b1)
    steps: list[Step] = [
        make_step(
            1,
            "Identificar el cociente de rectas",
            sp.latex(
                sp.Eq(
                    sp.Symbol("y'"),
                    (a1 * X + b1 * Y + c1) / (a2 * X + b2 * Y + c2),
                )
            ),
            "El lado derecho es un cociente de dos rectas. El determinante "
            f"a₁b₂ − a₂b₁ = {sp.sstr(determinant)} decide la sustitución.",
        )
    ]

    if determinant != 0:
        intersection = sp.solve(
            [
                sp.Eq(a1 * X + b1 * Y + c1, 0),
                sp.Eq(a2 * X + b2 * Y + c2, 0),
            ],
            [X, Y],
            dict=True,
        )
        if not intersection:
            raise ValueError("No se pudieron encontrar las rectas de intersección.")
        point = intersection[0]
        x_shift = safe_simplify(point[X])
        y_shift = safe_simplify(point[Y])
        steps.append(
            make_step(
                2,
                "Trasladar el origen a la intersección",
                rf"X = x - {sp.latex(x_shift)}, \qquad Y = y - {sp.latex(y_shift)}",
                "Con las rectas cortándose en (h,k), la traslación elimina los "
                "términos constantes y deja una EDO homogénea.",
            )
        )

        # Tras la traslación las rectas pasan por el origen, de modo que el
        # cociente sólo depende de v = Y/X.
        transformed = safe_simplify((a1 + b1 * V) / (a2 + b2 * V))
        steps.append(
            make_step(
                3,
                "Aplicar Y = v X",
                f"v + X\\frac{{dv}}{{dX}} = {sp.latex(transformed)}",
                "La ecuación ya es homogénea; se usa la sustitución estándar.",
            )
        )

        difference = safe_simplify(transformed - V)
        if difference == 0:
            steps.append(
                make_step(
                    4,
                    "Integrar",
                    r"v = C \quad\Longrightarrow\quad y = k + C(x - h)",
                    "Si v es constante, la solución es una recta que pasa por la "
                    "intersección de las dos rectas originales.",
                )
            )
            solution = safe_simplify(y_shift + C * (X - x_shift))
            return explicit_solution(solution), steps, []

        # X dv/dX = difference  =>  dv/difference = dX/X
        left = safe_integrate(1 / difference, V)
        relation = safe_simplify(left - sp.log(X - x_shift) - C)
        steps.append(
            make_step(
                4,
                "Separar e integrar",
                f"{sp.latex(left)} = \\ln\\left|{sp.latex(X - x_shift)}\\right| + C",
                "Se separan las variables v y X y se integra cada lado.",
            )
        )

        explicit_v = next(
            (
                item
                for item in safe_solve_expr(relation, V)
                if not item.has(V) and item not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
            ),
            None,
        )
        if explicit_v is not None:
            solution = safe_simplify(y_shift + explicit_v * (X - x_shift))
            steps.append(
                make_step(
                    5,
                    "Volver a x, y",
                    sp.latex(sp.Eq(Y, solution)),
                    "Se sustituye v = (y-k)/(x-h) y se despeja y.",
                )
            )
            return explicit_solution(solution), steps, []

        potential = safe_simplify(
            left.subs(V, (Y - y_shift) / (X - x_shift))
            - sp.log(X - x_shift)
        )
        steps.append(
            make_step(
                5,
                "Escribir la solución implícita",
                sp.latex(potential) + " = C",
                "No se pudo despejar v; se conserva la relación implícita.",
            )
        )
        return implicit_solution(potential), steps, []

    # Rectas paralelas: u = a1 x + b1 y reduce a separable.
    if b1 == 0:
        raise ValueError("Caso paralelo degenerado; no se puede usar u = a1 x + b1 y.")
    scale = safe_simplify(a2 / a1) if a1 != 0 else safe_simplify(b2 / b1)
    transformed = safe_simplify((U + c1) / (scale * U + c2))
    steps.append(
        make_step(
            2,
            "Usar la sustitución u = a₁x + b₁y",
            rf"u = {sp.latex(a1)}x + {sp.latex(b1)}y",
            "Como las rectas son paralelas, el cociente depende sólo de "
            "u = a₁x + b₁y.",
        )
    )
    steps.append(
        make_step(
            3,
            "Transformar la EDO",
            f"\\frac{{du}}{{dx}} = {sp.latex(a1)} + {sp.latex(b1)}"
            f"\\cdot\\frac{{{sp.latex(U + c1)}}}{{{sp.latex(scale * U + c2)}}}",
            "Se deriva u y se sustituye el lado derecho original.",
        )
    )

    denominator = safe_simplify(a1 + b1 * transformed)
    if denominator == 0:
        raise ValueError("La sustitución paralela conduce a u' = 0; caso degenerado.")
    integral = safe_integrate(1 / denominator, U)
    relation = safe_simplify(integral - X - C)
    steps.append(
        make_step(
            4,
            "Separar e integrar",
            f"{sp.latex(integral)} = x + C",
            "La EDO resultante es separable en u y x.",
        )
    )
    explicit_u = next(
        (
            item
            for item in safe_solve_expr(relation, U)
            if not item.has(U) and item not in (sp.zoo, sp.nan, sp.oo, -sp.oo)
        ),
        None,
    )
    if explicit_u is not None:
        solution = safe_simplify((explicit_u - a1 * X) / b1)
        steps.append(
            make_step(
                5,
                "Volver a y",
                sp.latex(sp.Eq(Y, solution)),
                "Se despeja y de u = a₁x + b₁y.",
            )
        )
        return explicit_solution(solution), steps, []

    potential = safe_simplify(integral.subs(U, a1 * X + b1 * Y) - X)
    steps.append(
        make_step(
            5,
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            "No se pudo despejar u; se conserva la relación implícita.",
        )
    )
    return implicit_solution(potential), steps, []


__all__ = ["solve"]
