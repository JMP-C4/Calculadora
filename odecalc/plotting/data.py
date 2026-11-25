"""Generación de datos para campo de direcciones, curvas y análisis fase."""

from __future__ import annotations

import math

import numpy as np
import sympy as sp

from odecalc.models import SolveResult
from odecalc.symbols import X, Y


def _lambdify(rhs: sp.Expr):
    function = sp.lambdify((X, Y), rhs, modules=["numpy"])

    def evaluate(x_values, y_values):
        with np.errstate(all="ignore"):
            values = function(x_values, y_values)
        return np.asarray(values, dtype=float)

    return evaluate


def direction_field(
    rhs: sp.Expr,
    *,
    x_min: float = -5.0,
    x_max: float = 5.0,
    y_min: float = -5.0,
    y_max: float = 5.0,
    density: int = 21,
    normalize: bool = True,
) -> dict[str, np.ndarray]:
    """Devuelve ``x, y, u, v`` para dibujar el campo ``dy/dx = f(x,y)``."""

    density = max(int(density), 2)
    x_values = np.linspace(float(x_min), float(x_max), density)
    y_values = np.linspace(float(y_min), float(y_max), density)
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    function = _lambdify(rhs)
    slopes = function(grid_x, grid_y)
    if slopes.shape != grid_x.shape:
        slopes = np.broadcast_to(slopes, grid_x.shape).astype(float)
    length = np.hypot(1.0, slopes)
    if normalize:
        u = 1.0 / length
        v = slopes / length
    else:
        u = np.ones_like(grid_x)
        v = slopes
    return {"x": grid_x, "y": grid_y, "u": u, "v": v, "slopes": slopes}


def solution_curve(
    result: SolveResult,
    *,
    x_min: float = -5.0,
    x_max: float = 5.0,
    n_points: int = 500,
) -> dict[str, np.ndarray] | None:
    """Extrae la curva numérica o evalúa la solución particular simbólica."""

    if result.numeric is not None and result.numeric.success:
        if result.numeric.x_arr is None or result.numeric.y_arr is None:
            return None
        return {
            "x": np.asarray(result.numeric.x_arr, dtype=float),
            "y": np.asarray(result.numeric.y_arr, dtype=float),
        }
    solution = result.particular
    if solution is None or not solution.is_explicit:
        return None
    constants = [
        symbol for symbol in solution.expr.free_symbols if symbol not in {X, Y}
    ]
    if constants:
        return None
    function = sp.lambdify(X, solution.expr, modules=["numpy"])
    x_values = np.linspace(float(x_min), float(x_max), max(int(n_points), 2))
    with np.errstate(all="ignore"):
        y_values = np.asarray(function(x_values), dtype=float)
    if y_values.shape != x_values.shape:
        y_values = np.broadcast_to(y_values, x_values.shape).astype(float)
    mask = np.isfinite(y_values)
    return {"x": x_values[mask], "y": y_values[mask]}


def family_curves(
    expr: sp.Expr,
    *,
    constants: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0),
    x_min: float = -5.0,
    x_max: float = 5.0,
    n_points: int = 300,
) -> list[dict[str, np.ndarray]]:
    """Evalúa una familia explícita ``y = expr(x, C)`` para varios valores de C."""

    constants_in_expr = sorted(
        (symbol for symbol in expr.free_symbols if symbol not in {X, Y}),
        key=lambda item: item.name,
    )
    if len(constants_in_expr) > 1:
        raise ValueError("La familia debe tener como máximo una constante libre.")
    x_values = np.linspace(float(x_min), float(x_max), max(int(n_points), 2))
    curves: list[dict[str, np.ndarray]] = []
    for value in constants:
        substitution = (
            {constants_in_expr[0]: value} if constants_in_expr else {}
        )
        try:
            function = sp.lambdify(X, expr.subs(substitution), modules=["numpy"])
            with np.errstate(all="ignore"):
                y_values = np.asarray(function(x_values), dtype=float)
            if y_values.shape != x_values.shape:
                y_values = np.broadcast_to(y_values, x_values.shape).astype(float)
        except Exception:
            continue
        mask = np.isfinite(y_values)
        if np.any(mask):
            curves.append({"x": x_values[mask], "y": y_values[mask]})
    return curves


def isoclines(
    rhs: sp.Expr,
    *,
    levels: tuple[float, ...] = (-1.0, 0.0, 1.0),
    x_min: float = -5.0,
    x_max: float = 5.0,
    n_points: int = 300,
) -> list[dict[str, object]]:
    """Curvas ``f(x,y) = k`` (isoclinas) como listas de puntos."""

    results: list[dict[str, object]] = []
    x_values = np.linspace(float(x_min), float(x_max), max(int(n_points), 2))
    for level in levels:
        substituted = sp.simplify(rhs - level)
        try:
            solved = sp.solve(sp.Eq(substituted, 0), Y)
        except Exception:
            solved = []
        for branch in solved:
            try:
                function = sp.lambdify(X, branch, modules=["numpy"])
                with np.errstate(all="ignore"):
                    y_values = np.asarray(function(x_values), dtype=float)
                if y_values.shape != x_values.shape:
                    y_values = np.broadcast_to(y_values, x_values.shape).astype(float)
            except Exception:
                continue
            mask = np.isfinite(y_values)
            if np.any(mask):
                results.append(
                    {
                        "level": level,
                        "x": x_values[mask],
                        "y": y_values[mask],
                    }
                )
    return results


def equilibrium_points(rhs: sp.Expr) -> list[dict[str, object]]:
    """Puntos de equilibrio de una EDO autónoma ``y' = f(y)`` y su estabilidad."""

    if rhs.has(X):
        return []
    points: list[dict[str, object]] = []
    try:
        roots = sp.solve(sp.Eq(rhs, 0), Y)
    except Exception:
        return []
    derivative = sp.diff(rhs, Y)
    for root in roots:
        if root.has(Y) or root in (sp.zoo, sp.nan, sp.oo, -sp.oo):
            continue
        try:
            if sp.im(sp.N(root)) != 0:
                continue
            slope = complex(sp.N(derivative.subs(Y, root)))
        except Exception:
            continue
        if not math.isfinite(slope.real):
            continue
        if slope.real < 0:
            stability = "asintóticamente estable"
        elif slope.real > 0:
            stability = "inestable"
        else:
            stability = "indeterminado (linealización nula)"
        points.append(
            {
                "y": float(sp.N(root)),
                "f'(y)": slope.real,
                "stability": stability,
            }
        )
    points.sort(key=lambda item: item["y"])
    return points


def phase_line(
    rhs: sp.Expr,
    *,
    y_min: float = -5.0,
    y_max: float = 5.0,
    n_points: int = 200,
) -> dict[str, np.ndarray]:
    """Datos para la línea de fase de una EDO autónoma."""

    if rhs.has(X):
        raise ValueError("La línea de fase requiere una EDO autónoma y' = f(y).")
    y_values = np.linspace(float(y_min), float(y_max), max(int(n_points), 2))
    function = _lambdify(rhs)
    slopes = function(np.zeros_like(y_values), y_values)
    if slopes.shape != y_values.shape:
        slopes = np.broadcast_to(slopes, y_values.shape).astype(float)
    return {"y": y_values, "f(y)": slopes}


__all__ = [
    "direction_field",
    "solution_curve",
    "family_curves",
    "isoclines",
    "equilibrium_points",
    "phase_line",
]
