"""Preparación de expresiones y límites para las gráficas.

Concentra la lógica que comparten las interfaces (escritorio y web) para
obtener ``y'`` a partir de una ecuación resuelta, despejar familias
implícitas y calcular límites razonables para los ejes.  No depende de
tkinter ni de Matplotlib.
"""

from __future__ import annotations

import numpy as np
import sympy as sp

from odecalc.models import SolveResult
from odecalc.parsing import parse_ode
from odecalc.plotting.data import solution_curve
from odecalc.symbols import DY, X, Y


def rhs_from_result(result: SolveResult) -> tuple[sp.Expr | None, str | None]:
    """Devuelve ``f(x, y)`` y un aviso opcional para ``dy/dx = f``.

    Acepta formas explícitas y formas implícitas/Clairaut en las que sea
    posible despejar ``y'`` con SymPy.
    """

    parsed = parse_ode(getattr(result, "input_text", "") or "")
    if parsed.error is not None:
        return None, f"No se pudo interpretar la ecuación: {parsed.error}"
    if parsed.rhs is not None:
        return parsed.rhs, None
    if parsed.F is None:
        return None, "La ecuación no tiene una forma utilizable para graficar."

    try:
        branches = sp.solve(sp.Eq(parsed.F, 0), DY)
    except Exception:
        branches = []
    usable = [
        branch
        for branch in branches
        if isinstance(branch, sp.Expr) and not branch.has(DY)
    ]
    if not usable:
        return None, (
            "La ecuación es implícita y no se pudo despejar y' para "
            "esta gráfica."
        )
    note = None
    if len(usable) > 1:
        note = "La ecuación tiene varias ramas de y'; se grafica la primera."
    return sp.simplify(usable[0]), note


def autonomous_rhs_from_result(
    result: SolveResult,
) -> tuple[sp.Expr | None, str | None]:
    """Devuelve ``f(y)`` si la EDO es autónoma; si no, un aviso."""

    rhs, note = rhs_from_result(result)
    if rhs is None:
        return None, note
    if rhs.has(X):
        return None, (
            "Esta gráfica solo está disponible para EDOs autónomas "
            "de la forma y' = f(y)."
        )
    return rhs, note


def family_expression_from_result(
    result: SolveResult,
) -> tuple[sp.Expr | None, str | None]:
    """Devuelve una expresión explícita ``y = f(x, C)`` para la familia."""

    general = getattr(result, "general", None)
    if general is None:
        return None, "No hay solución general para construir la familia de curvas."

    expression = general.expr
    if general.is_explicit:
        return expression, None

    target = general.value if general.value is not None else sp.Integer(0)
    try:
        branches = sp.solve(sp.Eq(expression, target), Y)
    except Exception:
        branches = []
    for branch in branches:
        if isinstance(branch, sp.Expr) and not branch.has(Y):
            return branch, (
                "La solución general era implícita; se grafica una rama "
                "explícita."
            )
    return None, (
        "La solución general es implícita y no se pudo despejar y(x) "
        "para graficar la familia."
    )


def plot_bounds(
    result: SolveResult,
    *,
    x_min: float = -5.0,
    x_max: float = 5.0,
) -> tuple[float, float, float, float]:
    """Calcula ``(x_min, x_max, y_min, y_max)`` a partir de la solución."""

    if not (np.isfinite(x_min) and np.isfinite(x_max) and x_min < x_max):
        x_min, x_max = -5.0, 5.0

    y_values: list[np.ndarray] = []
    numeric = getattr(result, "numeric", None)
    if numeric is not None and getattr(numeric, "success", False):
        x_arr = getattr(numeric, "x_arr", None)
        y_arr = getattr(numeric, "y_arr", None)
        if x_arr is not None and y_arr is not None:
            y_values.append(np.asarray(y_arr, dtype=float))
    curve = solution_curve(result, x_min=x_min, x_max=x_max)
    if curve is not None:
        y_values.append(np.asarray(curve["y"], dtype=float))

    finite = [values[np.isfinite(values)] for values in y_values]
    finite = [values for values in finite if values.size]
    if finite:
        values = np.concatenate(finite)
        y_low = float(np.min(values))
        y_high = float(np.max(values))
        if not np.isfinite(y_low) or not np.isfinite(y_high):
            return x_min, x_max, -5.0, 5.0
        if abs(y_high - y_low) < 1e-9:
            y_low -= 1.0
            y_high += 1.0
        padding = 0.10 * (y_high - y_low)
        return x_min, x_max, y_low - padding, y_high + padding
    return x_min, x_max, -5.0, 5.0


__all__ = [
    "rhs_from_result",
    "autonomous_rhs_from_result",
    "family_expression_from_result",
    "plot_bounds",
]
