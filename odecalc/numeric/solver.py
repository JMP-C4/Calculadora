"""Respaldo numérico con SciPy y detección de rigidez/explosión."""

from __future__ import annotations

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from odecalc.models import NumericResult
from odecalc.symbols import X, Y


def _failure(message: str, *, blow_up: bool = False, method: str = "") -> NumericResult:
    return NumericResult(
        x_arr=None,
        y_arr=None,
        success=False,
        message=message,
        method=method,
        blow_up=blow_up,
    )


def _prepare_function(rhs: sp.Expr):
    try:
        numeric_rhs = sp.lambdify((X, Y), rhs, modules=["numpy"])
    except Exception as exc:
        raise ValueError(f"No se pudo preparar f(x, y): {exc}") from exc

    def function(t: float, state: np.ndarray) -> np.ndarray:
        value = numeric_rhs(t, state[0])
        return np.asarray(value, dtype=float).reshape(-1)

    return function


def _integrate_segment(
    function,
    start: float,
    end: float,
    y0: float,
    n_points: int,
    rtol: float,
    atol: float,
    methods: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray, str, bool]:
    t_eval = np.linspace(start, end, n_points)
    last_error = ""
    stiff = False
    for index, method in enumerate(methods):
        try:
            solution = solve_ivp(
                function,
                (start, end),
                [y0],
                method=method,
                t_eval=t_eval,
                rtol=rtol,
                atol=atol,
            )
        except Exception as exc:
            last_error = str(exc)
            continue
        if not solution.success or solution.y.shape[1] == 0:
            last_error = solution.message
            if index == 0 and "step size" in solution.message.lower():
                stiff = True
            continue
        if index > 0:
            stiff = True
        return solution.t, solution.y[0], method, stiff
    raise RuntimeError(last_error or "el integrador no devolvió puntos")


def solve_numeric(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_min: float,
    x_max: float,
    *,
    n_points: int = 500,
    rtol: float = 1e-9,
    atol: float = 1e-12,
) -> NumericResult:
    """Integra ``y' = rhs`` desde ``(x0, y0)`` sobre ``[x_min, x_max]``."""

    try:
        x_min = float(x_min)
        x_max = float(x_max)
        x0 = float(x0)
        y0 = float(y0)
    except (TypeError, ValueError):
        return _failure("Las condiciones y el intervalo deben ser numéricos.")

    if not all(np.isfinite(item) for item in (x_min, x_max, x0, y0)):
        return _failure("Las condiciones y el intervalo deben ser finitos.")
    if x_min >= x_max:
        return _failure(
            "El intervalo no es válido: x_min debe ser estrictamente menor que x_max."
        )
    if not (x_min <= x0 <= x_max):
        return _failure("La condición inicial x₀ debe pertenecer al intervalo.")

    try:
        function = _prepare_function(rhs)
    except ValueError as exc:
        return _failure(str(exc))

    n_points = max(int(n_points), 2)
    methods = ("RK45", "LSODA", "Radau", "BDF", "DOP853")
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    errors: list[str] = []
    used_methods: list[str] = []
    stiff_flag = False

    for label, end in (("hacia atrás", x_min), ("hacia adelante", x_max)):
        if np.isclose(x0, end):
            continue
        try:
            t_values, y_values, method, stiff = _integrate_segment(
                function, x0, end, y0, n_points, rtol, atol, methods
            )
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            continue
        used_methods.append(method)
        stiff_flag = stiff_flag or stiff
        segments.append((t_values, y_values))

    if not segments:
        detail = "; ".join(errors) if errors else "el intervalo no contiene puntos"
        blow_up = any(
            word in detail.lower()
            for word in ("step size", "overflow", "too large", "singular")
        )
        return _failure(f"La integración numérica falló ({detail}).", blow_up=blow_up)

    x_all = np.concatenate([segment[0] for segment in segments])
    y_all = np.concatenate([segment[1] for segment in segments])
    order = np.argsort(x_all, kind="stable")
    x_all = x_all[order]
    y_all = y_all[order]
    unique_x, unique_index = np.unique(x_all, return_index=True)
    x_all = unique_x
    y_all = y_all[unique_index]

    if not (np.all(np.isfinite(x_all)) and np.all(np.isfinite(y_all))):
        return _failure("La solución numérica contiene valores no finitos.", blow_up=True)

    method_name = used_methods[0] if len(set(used_methods)) == 1 else "auto"
    message = f"Integración numérica exitosa con {len(x_all)} puntos ({method_name})."
    if stiff_flag:
        message += " Se detectó rigidez y se cambió a un integrador implícito."
    if errors:
        message += " Advertencia: " + "; ".join(errors)

    return NumericResult(
        x_arr=x_all,
        y_arr=y_all,
        success=True,
        message=message,
        method=method_name,
        stiff=stiff_flag,
        interval=(float(x_all[0]), float(x_all[-1])),
    )


__all__ = ["solve_numeric"]
