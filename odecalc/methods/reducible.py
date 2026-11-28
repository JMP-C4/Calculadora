"""EDOs reducibles a homogéneas mediante traslación o sustitución lineal."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import reducible_linear_coeffs
from odecalc.methods.atomic_steps import (
    StepBuilder,
    add_product_atomic_steps,
    add_transposition_step,
    describe_double_negative,
    explain_integration_rules,
)
from odecalc.methods.common import (
    _signed_term_latex,
    explicit_solution,
    format_linear_combo_latex,
    format_shift_latex,
    implicit_solution,
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
    prod1 = safe_simplify(a1 * b2)
    prod2 = safe_simplify(a2 * b1)
    determinant = safe_simplify(prod1 - prod2)

    builder = StepBuilder()
    det_dbl = describe_double_negative(prod1, prod2) or ""
    builder.add(
        "Identificar el cociente de rectas y calcular su determinante",
        rf"y' = \frac{{{sp.latex(a1 * X + b1 * Y + c1)}}}{{{sp.latex(a2 * X + b2 * Y + c2)}}}, \qquad "
        rf"D = a_1 b_2 - a_2 b_1 = ({sp.latex(a1)})({sp.latex(b2)}) - ({sp.latex(a2)})({sp.latex(b1)}) = {sp.latex(determinant)}",
        "El lado derecho es un cociente de rectas. Calculamos el determinante $D = a_1 b_2 - a_2 b_1$ "
        "para decidir si las rectas se cortan ($D \\neq 0$, traslación) o son paralelas ($D = 0$, sustitución lineal). "
        + det_dbl,
    )

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

        shift_notes = [
            "Resolvemos el sistema $a_1 h + b_1 k + c_1 = 0, a_2 h + b_2 k + c_2 = 0$ para hallar "
            rf"la intersección $(h, k) = ({sp.latex(x_shift)}, {sp.latex(y_shift)})$ y trasladamos "
            r"$X = x - h, Y = y - k$."
        ]
        for msg in (describe_double_negative(X, x_shift), describe_double_negative(Y, y_shift)):
            if msg:
                shift_notes.append(msg)

        builder.add(
            "Trasladar el origen a la intersección",
            rf"{format_shift_latex('X', 'x', x_shift)}, \qquad "
            rf"{format_shift_latex('Y', 'y', y_shift)}",
            " ".join(shift_notes) + " Esto anula las constantes y deja una EDO homogénea ($\\frac{dY}{dX} = \\frac{a_1 X + b_1 Y}{a_2 X + b_2 Y}$).",
        )

        # Tras la traslación las rectas pasan por el origen, de modo que el
        # cociente sólo depende de v = Y/X.
        transformed = safe_simplify((a1 + b1 * V) / (a2 + b2 * V))
        builder.add(
            "Aplicar la sustitución homogénea Y = v X",
            rf"v + X\frac{{dv}}{{dX}} = \frac{{{sp.latex(a1 + b1 * V)}}}{{{sp.latex(a2 + b2 * V)}}} = {sp.latex(transformed)}",
            r"Al sustituir $Y = vX$ y $\frac{dY}{dX} = v + X\frac{dv}{dX}$ se cancela $X$ en "
            r"numerador y denominador (simplificando signos comunes si los hubiera).",
        )

        difference = safe_simplify(transformed - V)
        if difference == 0:
            builder.add(
                "Integrar dv/dX = 0",
                r"v = C \quad\Longrightarrow\quad y = k + C(x - h)",
                r"Si $v$ es constante, la solución es una recta que pasa por la "
                "intersección de las dos rectas originales.",
            )
            solution = safe_simplify(y_shift + C * (X - x_shift))
            return explicit_solution(solution), builder.steps, []

        add_transposition_step(
            builder,
            r"v + X\frac{dv}{dX}",
            transformed,
            V,
            rf"X\frac{{dv}}{{dX}} = {sp.latex(difference)}",
            title="Aislar X·(dv/dX) restando v",
            from_left=True,
        )

        inv_diff = safe_simplify(1 / difference)
        left = safe_integrate(inv_diff, V)
        relation = safe_simplify(left - sp.log(X - x_shift) - C)
        builder.add(
            "Separar variables e integrar",
            rf"\left({sp.latex(inv_diff)}\right)\,dv = \frac{{dX}}{{X}} \quad\Longrightarrow\quad "
            rf"{sp.latex(left)} = \ln\left|{sp.latex(X - x_shift)}\right| + C",
            explain_integration_rules(inv_diff, V, left)
            + r" En el lado derecho $\int \frac{dX}{X} = \ln|X| + C$.",
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
            builder.add(
                "Volver a las variables originales x, y",
                sp.latex(sp.Eq(Y, solution)),
                r"Sustituimos $v = \frac{Y}{X} = \frac{y - k}{x - h}$ y despejamos $y$.",
            )
            return explicit_solution(solution), builder.steps, []

        potential = safe_simplify(
            left.subs(V, (Y - y_shift) / (X - x_shift))
            - sp.log(X - x_shift)
        )
        builder.add(
            "Escribir la solución implícita",
            sp.latex(potential) + " = C",
            r"Sustituimos $v = \frac{y - k}{x - h}$; no se pudo despejar $y$ explícitamente, "
            "por lo que se conserva la relación implícita.",
        )
        return implicit_solution(potential), builder.steps, []

    # Rectas paralelas: u = a1 x + b1 y reduce a separable.
    if b1 == 0:
        raise ValueError("Caso paralelo degenerado; no se puede usar u = a1 x + b1 y.")
    scale = safe_simplify(a2 / a1) if a1 != 0 else safe_simplify(b2 / b1)
    transformed = safe_simplify((U + c1) / (scale * U + c2))
    builder.add(
        "Usar la sustitución u = a₁x + b₁y (rectas paralelas)",
        rf"u = {format_linear_combo_latex(a1, b1)}",
        rf"Como $D = 0$, las rectas son paralelas ($a_2 x + b_2 y = {sp.latex(scale)}(a_1 x + b_1 y)$) "
        rf"y el cociente depende únicamente de $u = a_1 x + b_1 y$.",
    )
    frac_tex = rf"\frac{{{sp.latex(U + c1)}}}{{{sp.latex(scale * U + c2)}}}"
    b1_term = _signed_term_latex(b1, frac_tex, include_plus=True)
    builder.add(
        "Derivar u y sustituir en la EDO",
        rf"\frac{{du}}{{dx}} = {sp.latex(a1)}{b1_term}",
        r"Al derivar $u = a_1 x + b_1 y$ se usa $\frac{du}{dx} = a_1 + b_1 y'$ y se sustituye $y'$.",
    )

    denominator = safe_simplify(a1 + b1 * transformed)
    if denominator == 0:
        raise ValueError("La sustitución paralela conduce a u' = 0; caso degenerado.")
    add_product_atomic_steps(
        builder,
        b1,
        transformed,
        safe_simplify(b1 * transformed),
        title="Simplificar el miembro derecho en función de u",
        lhs_latex=r"\frac{du}{dx} - " + sp.latex(a1),
        intro_explanation=r"Efectuamos la multiplicación por $b_1$ y sumamos $a_1$ usando denominador común.",
    )
    inv_den = safe_simplify(1 / denominator)
    integral = safe_integrate(inv_den, U)
    relation = safe_simplify(integral - X - C)
    builder.add(
        "Separar variables e integrar",
        rf"\left({sp.latex(inv_den)}\right)\,du = dx \quad\Longrightarrow\quad {sp.latex(integral)} = x + C",
        "La EDO resultante es separable en $u$ y $x$. "
        + explain_integration_rules(inv_den, U, integral),
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
        builder.add(
            "Volver a y",
            sp.latex(sp.Eq(Y, solution)),
            r"Reemplazamos $u = a_1 x + b_1 y$ y despejamos $y$.",
        )
        return explicit_solution(solution), builder.steps, []

    potential = safe_simplify(integral.subs(U, a1 * X + b1 * Y) - X)
    builder.add(
        "Escribir la solución implícita",
        sp.latex(potential) + " = C",
        r"No se pudo despejar $u$; se conserva la relación implícita en $x$ e $y$.",
    )
    return implicit_solution(potential), builder.steps, []


__all__ = ["solve"]
