"""Verificación simbólica y numérica de soluciones."""

from __future__ import annotations

import cmath
import math
import random
from typing import Iterable

import numpy as np
import scipy.special as scipy_special
import sympy as sp

from odecalc.models import Solution, Verification
from odecalc.symbols import C, DY, X, Y, lambdify_modules


def _is_zero(expr: sp.Expr) -> bool:
    if expr == 0:
        return True
    candidates: list[sp.Expr] = []
    operations = (
        sp.simplify,
        sp.trigsimp,
        sp.cancel,
        sp.expand,
        sp.powsimp,
        sp.radsimp,
    )
    for operation in operations:
        try:
            candidates.append(operation(expr))
            if candidates[-1] == 0:
                return True
        except Exception:
            continue
    return any(candidate == 0 for candidate in candidates)


def simplify_residual(expr: sp.Expr) -> sp.Expr:
    """Simplifica un residuo sin dejar de ser conservador."""

    best = expr
    for operation in (
        sp.simplify,
        sp.trigsimp,
        sp.cancel,
        sp.expand,
        sp.radsimp,
    ):
        try:
            candidate = operation(best)
            if sp.count_ops(candidate) < sp.count_ops(best):
                best = candidate
            if best == 0:
                return sp.Integer(0)
        except Exception:
            continue
    return best


def _modules() -> list[object]:
    return lambdify_modules()


def _is_finite_number(value: object) -> bool:
    try:
        number = complex(value)
    except Exception:
        return False
    return math.isfinite(number.real) and math.isfinite(number.imag)


def _numeric_check_explicit(
    residual: sp.Expr,
    solution: Solution,
    x0: float | None,
) -> tuple[bool, int, str]:
    if residual.has(sp.Integral):
        return False, 0, "El residuo contiene una integral no evaluada."

    constants = sorted(
        (symbol for symbol in solution.expr.free_symbols if symbol not in {X, Y}),
        key=lambda item: item.name,
    )
    try:
        function = sp.lambdify((X, *constants), residual, modules=_modules())
    except Exception as exc:
        return False, 0, f"No se pudo evaluar numéricamente el residuo: {exc}"

    center = float(x0) if x0 is not None else 1.0
    rng = random.Random(20240517)
    x_values = [
        center + 0.37,
        center - 0.41,
        center + 1.13,
        center + 2.27,
        center - 1.71,
        0.5,
        1.5,
        2.5,
        -0.75,
    ]
    x_values.extend(rng.uniform(-3.0, 3.0) for _ in range(10))

    assignments = (
        [{}]
        if not constants
        else [{symbol: value for symbol in constants} for value in (0.7, -1.3, 2.1)]
    )

    finite_points = 0
    checked_points = 0
    for assignment in assignments:
        assignment_small = 0
        assignment_large = 0
        for x_value in x_values:
            try:
                raw = function(x_value, *[assignment[symbol] for symbol in constants])
            except Exception:
                continue
            if not _is_finite_number(raw):
                continue
            value = complex(raw)
            finite_points += 1
            checked_points += 1
            scale = max(1.0, abs(value))
            if abs(value) > 1e-5 * scale:
                assignment_large += 1
            else:
                assignment_small += 1
        if assignment_small >= 3 and assignment_large == 0:
            return True, assignment_small, (
                f"Verificación numérica correcta en {assignment_small} puntos "
                "del dominio (rama principal)."
            )
    if finite_points == 0:
        return False, 0, "No se encontraron puntos finitos para verificar."
    return False, checked_points, (
        "El residuo numérico no se anula en ningún conjunto de puntos de la "
        "rama principal."
    )


def _numeric_check_implicit(
    residual: sp.Expr,
    x0: float | None,
) -> tuple[bool, int, str]:
    if residual.has(sp.Integral):
        return False, 0, "El residuo contiene una integral no evaluada."
    try:
        function = sp.lambdify((X, Y), residual, modules=_modules())
    except Exception as exc:
        return False, 0, f"No se pudo evaluar numéricamente el residuo: {exc}"

    center = float(x0) if x0 is not None else 1.0
    rng = random.Random(20240518)
    points = [
        (center + 0.37, 0.83),
        (center - 0.41, -0.67),
        (center + 1.13, 1.37),
        (center - 1.71, 0.29),
        (0.7, 1.1),
        (1.4, -0.9),
        (-1.2, 1.6),
    ]
    points.extend((rng.uniform(-3, 3), rng.uniform(-3, 3)) for _ in range(10))

    checked = 0
    for x_value, y_value in points:
        try:
            raw = function(x_value, y_value)
        except Exception:
            continue
        if not _is_finite_number(raw):
            continue
        value = complex(raw)
        checked += 1
        if abs(value) > 1e-5 * max(1.0, abs(value)):
            return False, checked, (
                f"El residuo no se anula en (x, y) = ({x_value:.3f}, "
                f"{y_value:.3f}): {value:.3e}."
            )
    if checked == 0:
        return False, 0, "No se encontraron puntos finitos para verificar."
    return True, checked, f"Verificación numérica correcta en {checked} puntos."


def verify_solution(
    solution: Solution,
    rhs: sp.Expr | None = None,
    original_F: sp.Expr | None = None,
    x0: float | None = None,
) -> Verification:
    """Comprueba una solución por sustitución simbólica y, si hace falta, numérica."""

    try:
        if solution.is_explicit:
            if rhs is not None:
                residual = sp.diff(solution.expr, X) - rhs.subs(Y, solution.expr)
            elif original_F is not None:
                residual = original_F.subs(
                    {Y: solution.expr, DY: sp.diff(solution.expr, X)}
                )
            else:
                return Verification(
                    status="unverified",
                    message="No hay ecuación original para verificar la solución.",
                )
        else:
            if rhs is None:
                if original_F is None:
                    return Verification(
                        status="unverified",
                        message="No hay ecuación original para verificar la solución.",
                    )
                f_x = sp.diff(solution.expr, X)
                f_y = sp.diff(solution.expr, Y)
                if f_y == 0:
                    return Verification(
                        status="fail",
                        message="La solución implícita no define y como función de x.",
                    )
                residual = original_F.subs(
                    {DY: sp.simplify(-f_x / f_y), Y: Y}
                )
            else:
                residual = sp.diff(solution.expr, X) + sp.diff(solution.expr, Y) * rhs
    except Exception as exc:
        return Verification(
            status="fail",
            residual=None,
            message=f"No se pudo construir el residuo: {exc}",
        )

    simplified = simplify_residual(residual)
    if simplified == 0 or _is_zero(simplified):
        return Verification(
            status="ok",
            residual=residual,
            simplified_residual="0",
            message="La solución satisface la EDO (residuo simbólico idénticamente nulo).",
        )

    if solution.is_explicit:
        passed, points, message = _numeric_check_explicit(residual, solution, x0)
    else:
        passed, points, message = _numeric_check_implicit(residual, x0)

    if passed:
        return Verification(
            status="ok",
            residual=residual,
            simplified_residual=sp.sstr(simplified),
            numeric_checked=True,
            points_checked=points,
            message=message,
        )
    return Verification(
        status="fail",
        residual=residual,
        simplified_residual=sp.sstr(simplified),
        numeric_checked=points > 0,
        points_checked=points,
        message=message,
    )


def _with_definite_integrals(expr: sp.Expr, x0: float) -> sp.Expr:
    """Convierte ``∫f(x)dx`` en ``∫_{x0}^{x}f(t)dt``.

    Así la constante de integración absorbe el valor en ``x₀`` y el PVI puede
    resolverse aunque la primitiva no sea elemental.
    """

    indefinite = []
    for atom in expr.atoms(sp.Integral):
        if len(atom.args) != 2:
            continue
        limits = atom.args[1]
        if not isinstance(limits, (tuple, sp.Tuple)) or len(limits) != 1:
            continue
        if limits[0] == X:
            indefinite.append(atom)
    if not indefinite:
        return expr

    result = expr
    for index, atom in enumerate(indefinite):
        tau = sp.Symbol(f"_tau{index}", real=True)
        integrand = atom.args[0].subs(X, tau)
        result = result.subs(
            atom,
            sp.Integral(integrand, (tau, x0, X)),
        )
    return result


def _solve_for_constant(
    equation: sp.Eq,
    constant: sp.Symbol,
    *,
    scale: float = 1.0,
) -> list[sp.Expr]:
    """Despeja la constante con varias estrategias conservadoras."""

    strategies = (
        lambda: sp.solve(equation, constant),
        lambda: sp.solve(sp.Eq(sp.simplify(equation.lhs - equation.rhs), 0), constant),
        lambda: list(
            sp.solveset(
                sp.simplify(equation.lhs - equation.rhs),
                constant,
                domain=sp.S.Reals,
            )
        ),
    )
    for strategy in strategies:
        try:
            candidates = [
                item
                for item in strategy()
                if item.free_symbols <= {constant}
            ]
        except Exception:
            continue
        if candidates:
            return candidates

    # Respaldo numérico: busca raíces reales de f(C) = 0 probando varios
    # puntos iniciales.  Sólo se usa cuando los métodos simbólicos fallan.
    try:
        expression = sp.lambdify(constant, equation.lhs - equation.rhs, modules=["math"])
    except Exception:
        return []
    candidates = []
    for guess in (-4.0, -2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0, 4.0):
        try:
            root = sp.nsolve(equation, constant, guess)
            value = complex(root)
        except Exception:
            continue
        if abs(value.imag) > 1e-8:
            continue
        rounded = sp.nsimplify(value.real, rational=False)
        if any(sp.simplify(rounded - item) == 0 for item in candidates):
            continue
        try:
            residual = float(expression(float(value.real)))
        except Exception:
            residual = float("nan")
        if math.isfinite(residual) and abs(residual) < 1e-6 * max(1.0, abs(scale)):
            candidates.append(rounded)
    return candidates


def _real_log_branch(expr: sp.Expr, subs_dict: dict[sp.Symbol, object]) -> sp.Expr:
    """Selecciona la rama real ``ln(-u)`` cuando ``u`` es real negativo en el PVI.

    Como ``d/du ln(-u) = 1/u = d/du ln(u)``, cambiar el signo del argumento del
    logaritmo mantiene invariante el residuo diferencial y evita constantes ``+ i*pi``.
    """

    if not expr.has(sp.log):
        return expr
    allowed = set(subs_dict)
    replacements: list[tuple[sp.Expr, sp.Expr]] = []
    for atom in expr.atoms(sp.log):
        argument = atom.args[0]
        if argument.free_symbols - allowed:
            continue
        try:
            evaluated = complex(sp.N(argument.subs(subs_dict)))
        except Exception:
            continue
        if (
            math.isfinite(evaluated.real)
            and math.isfinite(evaluated.imag)
            and abs(evaluated.imag) < 1e-10
            and evaluated.real < -1e-15
        ):
            replacements.append((atom, sp.log(-argument)))
    updated = expr
    for old, new in replacements:
        updated = updated.subs(old, new)
    return updated


def _reparameterize_exp_constant(
    expr: sp.Expr,
    constant: sp.Symbol,
) -> tuple[sp.Expr, sp.Symbol] | None:
    """Reemplaza ``exp(k*C + r)`` por ``K * exp(r)`` cuando ``C`` solo aparece en ``exp``."""

    if not expr.has(sp.exp):
        return None
    k_symbol = sp.Symbol("_K_const", real=True)
    found_coeff: sp.Expr | None = None
    updated = expr
    for atom in list(expr.atoms(sp.exp)):
        arg = atom.args[0]
        if not arg.has(constant):
            continue
        try:
            arg_exp = sp.expand(arg)
            coeff = sp.simplify(sp.diff(arg_exp, constant))
            rem = sp.simplify(arg_exp - coeff * constant)
        except Exception:
            return None
        if coeff == 0 or coeff.has(X, Y, constant) or rem.has(constant):
            return None
        if found_coeff is None:
            found_coeff = coeff
        elif sp.simplify(found_coeff - coeff) != 0:
            return None
        updated = updated.subs(atom, k_symbol * sp.exp(rem))
    if found_coeff is None or updated.has(constant):
        return None
    return updated, k_symbol


def _exact_ic_value(value: float) -> sp.Expr:
    rounded = round(float(value))
    if abs(float(value) - rounded) < 1e-12:
        return sp.Integer(rounded)
    return sp.Float(value)


def apply_initial_conditions(
    solution: Solution,
    x0: float,
    y0: float,
    *,
    rhs: sp.Expr | None = None,
    original_F: sp.Expr | None = None,
) -> tuple[Solution | None, list[str]]:
    """Aplica el PVI y devuelve la solución particular y advertencias."""

    warnings: list[str] = []

    if solution.is_implicit:
        expr_real = _real_log_branch(solution.expr, {X: x0, Y: y0})
        x0_sym = _exact_ic_value(x0)
        y0_sym = _exact_ic_value(y0)
        try:
            value = sp.simplify(expr_real.subs({X: x0_sym, Y: y0_sym}))
        except Exception as exc:
            return None, [f"No se pudo evaluar la condición inicial: {exc}"]
        if value in (sp.zoo, sp.nan, sp.oo, -sp.oo) or not _is_finite_number(sp.N(value)):
            return None, [
                "La condición inicial no es finita en la solución implícita; "
                "el PVI puede no tener solución en esa rama."
            ]
        particular = Solution(
            form="implicit",
            expr=expr_real,
            value=value,
            constant=solution.constant,
            latex=sp.latex(expr_real) + " = " + sp.latex(value),
            branch_note=solution.branch_note,
        )
        return particular, warnings

    constants = sorted(
        (symbol for symbol in solution.expr.free_symbols if symbol not in {X, Y}),
        key=lambda item: item.name,
    )
    if not constants:
        expr_real = _real_log_branch(solution.expr, {X: x0})
        try:
            value = complex(sp.N(expr_real.subs(X, x0)))
        except Exception as exc:
            return None, [f"No se pudo evaluar la solución en x₀: {exc}"]
        if abs(value - complex(y0)) > 1e-7:
            warnings.append(
                "La solución general no contiene una constante libre y no "
                "satisface la condición inicial; el PVI no tiene solución en "
                "esta rama."
            )
            return None, warnings
        if expr_real != solution.expr:
            return (
                Solution(
                    form="explicit",
                    expr=expr_real,
                    latex=sp.latex(sp.Eq(Y, expr_real)),
                    branch_note=solution.branch_note,
                ),
                warnings,
            )
        return solution, warnings

    constant = constants[0]
    # Las integrales no elementales se reescriben como integrales definidas
    # desde x₀.  El valor de la integral en x₀ es cero, así que la constante
    # puede calcularse sin conocer una primitiva.
    adapted = _with_definite_integrals(_real_log_branch(solution.expr, {X: x0}), x0)
    x0_sym = _exact_ic_value(x0)
    y0_sym = _exact_ic_value(y0)
    valid: list[sp.Expr] = []

    def _try_solve(expr_to_solve: sp.Expr, target_symbol: sp.Symbol) -> list[sp.Expr]:
        try:
            equation = sp.Eq(expr_to_solve.subs(X, x0_sym), y0_sym)
            candidates = _solve_for_constant(equation, target_symbol, scale=float(y0))
        except Exception:
            return []
        found: list[sp.Expr] = []
        for candidate in candidates:
            try:
                substituted = sp.simplify(expr_to_solve.subs(target_symbol, candidate))
                value = complex(sp.N(substituted.subs(X, x0)))
            except Exception:
                continue
            if (
                math.isfinite(value.real)
                and math.isfinite(value.imag)
                and abs(value.imag) < 1e-7
                and abs(value.real - float(y0)) < 1e-6
            ):
                found.append(substituted)
        return found

    valid = _try_solve(adapted, constant)
    if not valid:
        reparam = _reparameterize_exp_constant(adapted, constant)
        if reparam is not None:
            adapted_k, k_symbol = reparam
            valid = _try_solve(adapted_k, k_symbol)

    if not valid:
        warnings.append(
            "La condición inicial no permitió determinar una constante real "
            "para esta solución general; revisa el dominio o la rama."
        )
        return None, warnings

    if len(valid) > 1:
        warnings.append(
            "El PVI admite más de una rama local; se eligió la primera rama "
            "que satisface la condición inicial. Puede no ser única."
        )

    particular_candidates = [
        Solution(
            form="explicit",
            expr=safe_expr(candidate),
            latex=sp.latex(sp.Eq(Y, safe_expr(candidate))),
            branch_note=solution.branch_note,
        )
        for candidate in valid
    ]

    if rhs is not None or original_F is not None:
        for candidate in particular_candidates:
            if verify_solution(
                candidate,
                rhs=rhs,
                original_F=original_F,
                x0=x0,
            ).status == "ok":
                return candidate, warnings
        warnings.append(
            "La rama particular obtenida no pudo verificarse simbólicamente ni "
            "numéricamente; se muestra con advertencia."
        )

    return particular_candidates[0], warnings


def safe_expr(expr: sp.Expr) -> sp.Expr:
    try:
        return sp.simplify(expr)
    except Exception:
        return expr


__all__ = [
    "verify_solution",
    "apply_initial_conditions",
    "simplify_residual",
]
