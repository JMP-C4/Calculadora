"""Solución numérica de EDOs de primer orden con SciPy (RK45)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)


@dataclass
class NumericResult:
    """Resultado de una integración numérica."""

    x_arr: np.ndarray | None
    y_arr: np.ndarray | None
    success: bool
    message: str


def _failure(message: str) -> NumericResult:
    return NumericResult(x_arr=None, y_arr=None, success=False, message=message)


def _integrate_segment(
    function,
    start: float,
    end: float,
    y0: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    t_eval = np.linspace(start, end, n_points)
    solution = solve_ivp(
        function,
        (start, end),
        [y0],
        method="RK45",
        t_eval=t_eval,
        rtol=1e-9,
        atol=1e-12,
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    if solution.y.shape[1] == 0:
        raise RuntimeError("el integrador no devolvió puntos de solución")
    return solution.t, solution.y[0]


def solve_numeric(
    rhs: sp.Expr,
    conditions: Any,
    n_points: int = 500,
) -> NumericResult:
    """Resuelve ``dy/dx = rhs`` numéricamente sobre el intervalo indicado.

    Se integra en ambos sentidos desde ``x0`` para cubrir ``[x_min, x_max]``
    aunque ``x0`` no coincida con un extremo. Si una de las dos direcciones
    falla (por ejemplo, por una singularidad), se conserva la otra y se
    informa la advertencia en ``message``.
    """

    if conditions is None:
        return _failure("No se proporcionaron condiciones para la solución numérica.")

    try:
        x_min = float(conditions.x_min)
        x_max = float(conditions.x_max)
    except (AttributeError, TypeError, ValueError):
        return _failure("El intervalo de integración no es válido.")

    if not (np.isfinite(x_min) and np.isfinite(x_max)):
        return _failure("El intervalo de integración debe ser finito.")
    if x_min >= x_max:
        return _failure(
            "El intervalo no es válido: x_min debe ser estrictamente menor que x_max."
        )

    x0_raw = getattr(conditions, "x0", None)
    y0_raw = getattr(conditions, "y0", None)
    x0 = float(x0_raw) if x0_raw is not None else (x_min + x_max) / 2.0
    y0 = float(y0_raw) if y0_raw is not None else 0.0
    if not (np.isfinite(x0) and np.isfinite(y0)):
        return _failure("La condición inicial debe contener valores numéricos finitos.")

    n_points = max(int(n_points), 2)

    try:
        numeric_rhs = sp.lambdify((x, y), rhs, modules="numpy")
    except Exception as exc:
        return _failure(f"No se pudo preparar la función f(x, y): {exc}")

    def function(t: float, state: np.ndarray) -> np.ndarray:
        value = numeric_rhs(t, state[0])
        return np.asarray(value, dtype=float).reshape(-1)

    segments: list[tuple[np.ndarray, np.ndarray]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for label, end in (("hacia atrás", x_min), ("hacia adelante", x_max)):
        if np.isclose(x0, end):
            continue
        try:
            segments.append(_integrate_segment(function, x0, end, y0, n_points))
        except Exception as exc:
            errors.append(f"{label}: {exc}")

    if not segments:
        detail = "; ".join(errors) if errors else "el intervalo no contiene puntos"
        return _failure(f"La integración numérica falló ({detail}).")

    x_all = np.concatenate([segment[0] for segment in segments])
    y_all = np.concatenate([segment[1] for segment in segments])

    order = np.argsort(x_all, kind="stable")
    x_all = x_all[order]
    y_all = y_all[order]

    unique_x, unique_index = np.unique(x_all, return_index=True)
    x_all = unique_x
    y_all = y_all[unique_index]

    if not (np.all(np.isfinite(x_all)) and np.all(np.isfinite(y_all))):
        return _failure("La solución numérica contiene valores no finitos.")

    if len(segments) == 1 and errors:
        warnings.append(errors[0])

    message = f"Integración numérica exitosa con {len(x_all)} puntos."
    if warnings:
        message += " Advertencia: " + "; ".join(warnings)

    return NumericResult(
        x_arr=x_all,
        y_arr=y_all,
        success=True,
        message=message,
    )


__all__ = ["NumericResult", "solve_numeric", "x", "y"]
