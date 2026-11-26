"""Respaldo numérico con SciPy y detección de rigidez/explosión."""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Callable
import warnings

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from odecalc.models import NumericResult
from odecalc.symbols import X, Y, lambdify_modules


class _BudgetExceeded(RuntimeError):
    """Corte interno cuando un segmento excede evaluaciones o tiempo."""


@dataclass(frozen=True)
class SegmentOutcome:
    """Resultado normalizado de integrar un segmento con SciPy."""

    success: bool
    t: np.ndarray
    y: np.ndarray
    method: str
    stiff: bool
    blow_up: bool
    message: str
    nfev: int


def _failure(message: str, *, blow_up: bool = False, method: str = "") -> NumericResult:
    return NumericResult(
        x_arr=None,
        y_arr=None,
        success=False,
        message=message,
        method=method,
        blow_up=blow_up,
    )


def scalar_evaluator(rhs: sp.Expr) -> Callable[[float, float], float]:
    """Compila ``f(x, y)`` en un evaluador escalar seguro en los reales."""

    if rhs.free_symbols - {X, Y}:
        raise ValueError(
            "La expresión contiene símbolos adicionales; sustituye los parámetros "
            "antes de integrar."
        )
    try:
        numeric_rhs = sp.lambdify((X, Y), rhs, modules=lambdify_modules())
    except Exception as exc:
        raise ValueError(f"No se pudo preparar f(x, y): {exc}") from exc

    def evaluate(t: float, y_val: float) -> float:
        with np.errstate(all="ignore"):
            raw = numeric_rhs(t, y_val)
        arr = np.asarray(raw)
        if arr.size != 1:
            raise ValueError("f(x, y) no devolvió un escalar.")
        scalar = complex(arr.reshape(-1)[0])
        if abs(scalar.imag) > 1e-9:
            return math.nan
        if not (math.isfinite(scalar.real) and math.isfinite(scalar.imag)):
            return math.nan
        return float(scalar.real)

    return evaluate


def _prepare_function(rhs: sp.Expr):
    evaluate = scalar_evaluator(rhs)

    def function(t: float, state: np.ndarray) -> np.ndarray:
        val = evaluate(float(t), float(state[0]))
        return np.asarray([val], dtype=float)

    return function


def _extract_event_time(t_events: list[np.ndarray] | None, start: float, end: float) -> float | None:
    if not t_events:
        return None
    direction = 1.0 if end >= start else -1.0
    candidates: list[float] = []
    for arr in t_events:
        if arr is not None and len(arr) > 0:
            val = float(arr[0])
            if math.isfinite(val) and (val - start) * direction > 1e-12:
                candidates.append(val)
    if not candidates:
        return None
    return min(candidates, key=lambda val: abs(val - start))


def _integrate_single_method(
    eval_scalar: Callable[[float, float], float],
    start: float,
    end: float,
    y0: float,
    f0: float,
    *,
    method: str,
    n_points: int,
    rtol: float,
    atol: float,
    max_nfev: int,
    max_seconds: float,
    t_eval_override: np.ndarray | None = None,
) -> tuple[object | None, int, bool, bool, str]:
    y_limit = max(1e15, 1e12 * max(1.0, abs(y0)))
    slope_limit = max(1e18, 1e14 * max(1.0, abs(f0)))
    nfev = 0
    start_wall = time.perf_counter()
    nonfinite_hit = False
    max_y_seen = abs(y0)
    max_f_seen = abs(f0)

    def rhs_wrapped(t: float, state: np.ndarray) -> np.ndarray:
        nonlocal nfev, nonfinite_hit, max_y_seen, max_f_seen
        nfev += 1
        if nfev > max_nfev:
            raise _BudgetExceeded(f"límite de evaluaciones ({max_nfev}) alcanzado")
        if nfev % 256 == 0 and (time.perf_counter() - start_wall) > max_seconds:
            raise _BudgetExceeded(f"tiempo límite por segmento ({max_seconds:.1f} s)")
        y_val = float(state[0])
        if not math.isfinite(y_val):
            nonfinite_hit = True
            return np.array([math.nan], dtype=float)
        abs_y = abs(y_val)
        if abs_y > max_y_seen:
            max_y_seen = abs_y
        try:
            val = eval_scalar(float(t), y_val)
        except Exception:
            nonfinite_hit = True
            return np.array([math.nan], dtype=float)
        if not math.isfinite(val):
            nonfinite_hit = True
            return np.array([math.nan], dtype=float)
        abs_f = abs(val)
        if abs_f > max_f_seen:
            max_f_seen = abs_f
        return np.array([val], dtype=float)

    def ev_y(t: float, state: np.ndarray) -> float:
        y_val = float(state[0])
        return (y_limit - abs(y_val)) if math.isfinite(y_val) else -1.0

    ev_y.terminal = True  # type: ignore[attr-defined]
    ev_y.direction = -1  # type: ignore[attr-defined]

    def ev_slope(t: float, state: np.ndarray) -> float:
        y_val = float(state[0])
        if not math.isfinite(y_val):
            return -1.0
        try:
            val = eval_scalar(float(t), y_val)
        except Exception:
            return -1.0
        return (slope_limit - abs(val)) if math.isfinite(val) else -1.0

    ev_slope.terminal = True  # type: ignore[attr-defined]
    ev_slope.direction = -1  # type: ignore[attr-defined]

    t_eval = (
        t_eval_override
        if t_eval_override is not None
        else np.linspace(start, end, max(int(n_points), 2))
    )
    events = None if t_eval_override is not None else [ev_y, ev_slope]
    try:
        with warnings.catch_warnings(), np.errstate(all="ignore"):
            warnings.simplefilter("ignore")
            solution = solve_ivp(
                rhs_wrapped,
                (start, end),
                [y0],
                method=method,
                t_eval=t_eval,
                rtol=rtol,
                atol=atol,
                events=events,
            )
    except _BudgetExceeded as exc:
        blew_up = (
            nonfinite_hit
            or max_y_seen >= 0.01 * y_limit
            or max_f_seen >= 0.01 * slope_limit
        )
        return None, nfev, blew_up, nonfinite_hit, str(exc)
    except Exception as exc:
        blew_up = nonfinite_hit or any(
            word in str(exc).lower() for word in ("overflow", "too large", "singular")
        )
        return None, nfev, blew_up, nonfinite_hit, str(exc)

    msg = str(solution.message or "")
    msg_lower = msg.lower()
    blew_up = (
        solution.status == 1
        or nonfinite_hit
        or max_y_seen >= 0.01 * y_limit
        or max_f_seen >= 0.01 * slope_limit
        or any(word in msg_lower for word in ("overflow", "too large", "singular"))
    )
    return solution, nfev, blew_up, nonfinite_hit, msg


def integrate_scipy_segment(
    eval_scalar: Callable[[float, float], float],
    start: float,
    end: float,
    y0: float,
    *,
    n_points: int = 500,
    rtol: float = 1e-9,
    atol: float = 1e-12,
    methods: tuple[str, ...] = ("RK45", "BDF", "Radau", "DOP853", "LSODA"),
    max_nfev: int = 12_000,
    max_seconds: float = 1.2,
) -> SegmentOutcome:
    """Integra un segmento desde ``start`` hasta ``end`` controlando explosiones."""

    try:
        f0 = eval_scalar(float(start), float(y0))
    except Exception as exc:
        return SegmentOutcome(
            success=False,
            t=np.empty(0, dtype=float),
            y=np.empty(0, dtype=float),
            method="",
            stiff=False,
            blow_up=False,
            message=f"{type(exc).__name__}: {exc}",
            nfev=0,
        )
    if not math.isfinite(f0):
        return SegmentOutcome(
            success=False,
            t=np.empty(0, dtype=float),
            y=np.empty(0, dtype=float),
            method="",
            stiff=False,
            blow_up=False,
            message="f(x, y) no es finita en el punto inicial.",
            nfev=0,
        )

    n_points = max(int(n_points), 2)
    last_error = ""
    last_nfev = 0
    stiff = False

    for index, method in enumerate(methods):
        solution, nfev, blew_up, nonfinite_hit, msg = _integrate_single_method(
            eval_scalar,
            start,
            end,
            y0,
            f0,
            method=method,
            n_points=n_points,
            rtol=rtol,
            atol=atol,
            max_nfev=max_nfev,
            max_seconds=max_seconds,
        )
        last_nfev = nfev
        if solution is None:
            last_error = f"{method}: {msg}"
            if blew_up:
                return SegmentOutcome(
                    success=False,
                    t=np.empty(0, dtype=float),
                    y=np.empty(0, dtype=float),
                    method=method,
                    stiff=stiff,
                    blow_up=True,
                    message=last_error,
                    nfev=last_nfev,
                )
            stiff = True
            continue

        t_arr = np.asarray(solution.t, dtype=float)
        y_arr = (
            np.asarray(solution.y[0], dtype=float)
            if solution.y.shape[0] > 0 and solution.y.shape[1] > 0
            else np.empty(0, dtype=float)
        )
        finite_mask = np.isfinite(t_arr) & np.isfinite(y_arr)
        t_fin = t_arr[finite_mask]
        y_fin = y_arr[finite_mask]

        if solution.status == 0 and solution.success and y_fin.size >= 1:
            return SegmentOutcome(
                success=True,
                t=t_fin,
                y=y_fin,
                method=method,
                stiff=index > 0 or stiff,
                blow_up=False,
                message=msg,
                nfev=nfev,
            )

        if solution.status == 1 or (blew_up and y_fin.size >= 2):
            if solution.status == 1 and y_fin.size < 2:
                t_ev = _extract_event_time(getattr(solution, "t_events", None), start, end)
                if t_ev is not None:
                    sub_end = start + 0.9 * (t_ev - start)
                    if abs(sub_end - start) > 1e-12:
                        sub_sol, sub_nfev, _, _, _ = _integrate_single_method(
                            eval_scalar,
                            start,
                            sub_end,
                            y0,
                            f0,
                            method=method,
                            n_points=min(n_points, 200),
                            rtol=rtol,
                            atol=atol,
                            max_nfev=max_nfev,
                            max_seconds=max_seconds,
                            t_eval_override=np.linspace(start, sub_end, min(n_points, 200)),
                        )
                        last_nfev += sub_nfev
                        if sub_sol is not None and sub_sol.y.shape[1] >= 2:
                            sub_t = np.asarray(sub_sol.t, dtype=float)
                            sub_y = np.asarray(sub_sol.y[0], dtype=float)
                            sub_mask = np.isfinite(sub_t) & np.isfinite(sub_y)
                            t_fin = sub_t[sub_mask]
                            y_fin = sub_y[sub_mask]
            if y_fin.size >= 2:
                return SegmentOutcome(
                    success=True,
                    t=t_fin,
                    y=y_fin,
                    method=method,
                    stiff=index > 0 or stiff,
                    blow_up=True,
                    message=(
                        "Posible explosión o frontera de dominio antes de completar el segmento."
                        if not msg
                        else msg
                    ),
                    nfev=last_nfev,
                )
            return SegmentOutcome(
                success=False,
                t=np.empty(0, dtype=float),
                y=np.empty(0, dtype=float),
                method=method,
                stiff=stiff,
                blow_up=True,
                message=msg or "Posible explosión o frontera de dominio.",
                nfev=last_nfev,
            )

        last_error = f"{method}: {msg}" if msg else f"{method}: el integrador no devolvió puntos"
        if blew_up or nonfinite_hit:
            return SegmentOutcome(
                success=False,
                t=np.empty(0, dtype=float),
                y=np.empty(0, dtype=float),
                method=method,
                stiff=stiff,
                blow_up=True,
                message=last_error,
                nfev=last_nfev,
            )
        if index == 0 and "step size" in msg.lower():
            stiff = True

    return SegmentOutcome(
        success=False,
        t=np.empty(0, dtype=float),
        y=np.empty(0, dtype=float),
        method=methods[-1] if methods else "",
        stiff=stiff,
        blow_up="step size" in last_error.lower(),
        message=last_error or "el integrador no devolvió puntos",
        nfev=last_nfev,
    )


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
        eval_scalar = scalar_evaluator(rhs)
    except ValueError as exc:
        return _failure(str(exc))

    try:
        valor_inicial = eval_scalar(x0, y0)
        if not math.isfinite(valor_inicial):
            return _failure(
                "La derivada no es finita en la condición inicial "
                f"(x₀={x0:g}, y₀={y0:g}); se omite la integración numérica. "
                "Revisa el dominio o elige otro punto inicial."
            )
    except Exception as exc:
        return _failure(
            "La derivada no está definida en la condición inicial "
            f"(x₀={x0:g}, y₀={y0:g}): {type(exc).__name__}: {exc}. "
            "Se omite la integración numérica; revisa el dominio o elige otro "
            "punto inicial."
        )

    n_points = max(int(n_points), 2)
    methods = ("RK45", "BDF", "Radau", "DOP853", "LSODA")
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    errors: list[str] = []
    used_methods: list[str] = []
    stiff_flag = False
    blow_up_flag = False

    for label, end in (("hacia atrás", x_min), ("hacia adelante", x_max)):
        if np.isclose(x0, end):
            continue
        outcome = integrate_scipy_segment(
            eval_scalar,
            x0,
            end,
            y0,
            n_points=n_points,
            rtol=rtol,
            atol=atol,
            methods=methods,
        )
        stiff_flag = stiff_flag or outcome.stiff
        blow_up_flag = blow_up_flag or outcome.blow_up
        if not outcome.success:
            errors.append(f"{label}: {outcome.message}")
            continue
        used_methods.append(outcome.method)
        segments.append((outcome.t, outcome.y))

    if not segments:
        detail = "; ".join(errors) if errors else "el intervalo no contiene puntos"
        blow_up = blow_up_flag or any(
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
    if blow_up_flag:
        message += (
            " Se detectó una posible explosión o frontera de dominio antes de "
            "cubrir todo el intervalo."
        )
    if errors:
        message += " Advertencia: " + "; ".join(errors)

    return NumericResult(
        x_arr=x_all,
        y_arr=y_all,
        success=True,
        message=message,
        method=method_name,
        stiff=stiff_flag,
        blow_up=blow_up_flag,
        interval=(float(x_all[0]), float(x_all[-1])),
    )


__all__ = [
    "SegmentOutcome",
    "integrate_scipy_segment",
    "scalar_evaluator",
    "solve_numeric",
]
