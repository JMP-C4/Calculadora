"""Datos de gráficas para la interfaz web, listos para JSON/Plotly.

La lógica matemática vive en ``odecalc.plotting``; este módulo sólo adapta
los arreglos a una estructura serializable que el navegador dibuja con
Plotly.  No importa tkinter ni Matplotlib.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp

from odecalc.models import SolveResult
from odecalc.plotting import (
    autonomous_rhs_from_result,
    direction_field,
    equilibrium_points,
    family_curves,
    family_expression_from_result,
    isoclines,
    phase_line,
    plot_bounds,
    rhs_from_result,
    solution_curve,
)
from odecalc.symbols import X, Y, lambdify_modules

PLOT_MODES: dict[str, str] = {
    "solution": "Solución y(x)",
    "direction_field": "Campo de direcciones",
    "isoclines": "Isoclinas",
    "family": "Familia de curvas",
    "phase_line": "Línea de fase",
    "equilibria": "Puntos de equilibrio",
    "surface": "Superficie 3D z = f(x,y)",
}

_FAMILY_VALUES = (-2.0, -1.0, 0.0, 1.0, 2.0)
_FAMILY_COLORS = ("#1565c0", "#2e7d32", "#6a1b9a", "#ef6c00", "#00838f")


# ---------------------------------------------------------------------------
# Utilidades de serialización
# ---------------------------------------------------------------------------
def _clean(values: Any) -> list[float | None]:
    """Aplana un arreglo y convierte NaN/Inf en ``None`` para JSON."""

    array = np.asarray(values, dtype=float).reshape(-1)
    return [
        None if not math.isfinite(value) else round(float(value), 8)
        for value in array
    ]


def _clean_grid(values: Any) -> list[list[float | None]]:
    array = np.asarray(values, dtype=float)
    return [
        [
            None if not math.isfinite(value) else round(float(value), 8)
            for value in row
        ]
        for row in array
    ]


def _line(
    x: Any,
    y: Any,
    *,
    label: str | None = None,
    color: str = "#1565c0",
    width: float = 2.0,
    dash: str = "solid",
) -> dict[str, Any]:
    return {
        "type": "line",
        "x": _clean(x),
        "y": _clean(y),
        "label": label,
        "color": color,
        "width": width,
        "dash": dash,
    }


def _points(
    x: Any,
    y: Any,
    *,
    label: str | None = None,
    color: str = "#6a1b9a",
    text: list[str] | None = None,
    size: float = 11.0,
) -> dict[str, Any]:
    return {
        "type": "points",
        "x": _clean(x),
        "y": _clean(y),
        "label": label,
        "color": color,
        "text": text or [],
        "size": size,
    }


def _segments(
    x: Any,
    y: Any,
    u: Any,
    v: Any,
    *,
    scale: float,
    color: str = "#455a64",
    width: float = 1.0,
) -> dict[str, Any]:
    xs: list[float | None] = []
    ys: list[float | None] = []
    for xi, yi, ui, vi in zip(
        np.ravel(x), np.ravel(y), np.ravel(u), np.ravel(v)
    ):
        if not (
            math.isfinite(float(xi))
            and math.isfinite(float(yi))
            and math.isfinite(float(ui))
            and math.isfinite(float(vi))
        ):
            continue
        xs.extend([float(xi - ui * scale / 2), float(xi + ui * scale / 2), None])
        ys.extend([float(yi - vi * scale / 2), float(yi + vi * scale / 2), None])
    return {
        "type": "segments",
        "x": xs,
        "y": ys,
        "label": None,
        "color": color,
        "width": width,
    }


def _figure_2d(
    title: str,
    traces: list[dict[str, Any]],
    *,
    x_label: str = "x",
    y_label: str = "y",
    zero_line: bool = False,
) -> dict[str, Any]:
    return {
        "kind": "2d",
        "title": title,
        "x_label": x_label,
        "y_label": y_label,
        "zero_line": zero_line,
        "traces": traces,
    }


def _figure_3d(title: str, surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "3d",
        "title": title,
        "x_label": "x",
        "y_label": "y",
        "z_label": "z = f(x, y)",
        "surface": surface,
        "traces": [],
    }


def _ok(figure: dict[str, Any], notice: str = "") -> dict[str, Any]:
    return {"available": True, "notice": notice, "figure": figure}


def _unavailable(notice: str) -> dict[str, Any]:
    return {"available": False, "notice": notice, "figure": None}


def _family_traces(
    expression: sp.Expr,
    *,
    x_min: float,
    x_max: float,
) -> list[dict[str, Any]]:
    constants = [
        symbol for symbol in expression.free_symbols if symbol not in {X, Y}
    ]
    traces: list[dict[str, Any]] = []
    if not constants:
        for curve in family_curves(
            expression, constants=(0.0,), x_min=x_min, x_max=x_max
        ):
            traces.append(
                _line(curve["x"], curve["y"], label="Solución general")
            )
        return traces

    for value, color in zip(_FAMILY_VALUES, _FAMILY_COLORS):
        for curve in family_curves(
            expression, constants=(value,), x_min=x_min, x_max=x_max
        ):
            traces.append(
                _line(
                    curve["x"],
                    curve["y"],
                    label=f"C = {value:g}",
                    color=color,
                    width=1.8,
                )
            )
    return traces


def _level_color(level: float) -> str:
    if abs(level + 1.0) < 1e-9:
        return "#6a1b9a"
    if abs(level) < 1e-9:
        return "#2e7d32"
    if abs(level - 1.0) < 1e-9:
        return "#ef6c00"
    return "#1565c0"


# ---------------------------------------------------------------------------
# Constructores por modo
# ---------------------------------------------------------------------------
def _build_solution(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    curve = solution_curve(result, x_min=x_min, x_max=x_max)
    if curve is not None and len(curve["x"]):
        return _ok(
            _figure_2d(
                "Solución de la EDO",
                [_line(curve["x"], curve["y"], label="Solución")],
            )
        )

    expression, note = family_expression_from_result(result)
    if expression is None:
        return _unavailable(
            note
            or (
                "No hay solución particular explícita ni curva numérica "
                "para graficar."
            )
        )
    try:
        traces = _family_traces(expression, x_min=x_min, x_max=x_max)
    except Exception as exc:
        return _unavailable(f"No se pudo construir la familia de soluciones: {exc}")
    if not traces:
        return _unavailable(
            "La expresión de la familia no se pudo evaluar en el intervalo."
        )

    notice = (
        "No hay una solución particular explícita; se muestra la familia "
        "general."
    )
    if note:
        notice = f"{notice} {note}"
    return _ok(_figure_2d("Familia de soluciones", traces), notice)


def _build_direction_field(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    rhs, note = rhs_from_result(result)
    if rhs is None:
        return _unavailable(
            note or "No se pudo obtener y' para el campo de direcciones."
        )

    x_min, x_max, y_min, y_max = plot_bounds(
        result, x_min=x_min, x_max=x_max
    )
    density = 21
    data = direction_field(
        rhs,
        x_min=x_min,
        x_max=x_max,
        y_min=y_min,
        y_max=y_max,
        density=density,
    )
    mask = np.isfinite(data["u"]) & np.isfinite(data["v"])
    if not np.any(mask):
        return _unavailable(
            "No se pudo evaluar el campo de direcciones en el intervalo."
        )

    step_x = (x_max - x_min) / (density - 1)
    step_y = (y_max - y_min) / (density - 1)
    scale = 0.75 * min(abs(step_x), abs(step_y))
    traces = [
        _segments(
            data["x"][mask],
            data["y"][mask],
            data["u"][mask],
            data["v"][mask],
            scale=scale,
        )
    ]
    curve = solution_curve(result, x_min=x_min, x_max=x_max)
    if curve is not None and len(curve["x"]):
        traces.append(
            _line(curve["x"], curve["y"], label="Solución", color="#d84315")
        )
    return _ok(
        _figure_2d("Campo de direcciones", traces), note or ""
    )


def _build_isoclines(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    rhs, note = rhs_from_result(result)
    if rhs is None:
        return _unavailable(
            note or "No se pudo obtener y' para calcular las isoclinas."
        )

    x_min, x_max, y_min, y_max = plot_bounds(
        result, x_min=x_min, x_max=x_max
    )
    lines = isoclines(rhs, levels=(-1.0, 0.0, 1.0), x_min=x_min, x_max=x_max)
    if not lines:
        return _unavailable(
            "No se pudieron calcular isoclinas reales para esta ecuación "
            "en el intervalo indicado."
        )

    traces = [
        _line(
            line["x"],
            line["y"],
            label=f"k = {float(line['level']):g}",
            color=_level_color(float(line["level"])),
            width=1.8,
        )
        for line in lines
    ]
    return _ok(
        _figure_2d("Isoclinas f(x, y) = k", traces), note or ""
    )


def _build_family(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    expression, note = family_expression_from_result(result)
    if expression is None:
        return _unavailable(
            note or "No hay una familia de curvas para graficar."
        )
    try:
        traces = _family_traces(expression, x_min=x_min, x_max=x_max)
    except Exception as exc:
        return _unavailable(f"No se pudo construir la familia de curvas: {exc}")
    if not traces:
        return _unavailable(
            "La expresión de la familia no se pudo evaluar en el intervalo."
        )
    return _ok(_figure_2d("Familia de curvas", traces), note or "")


def _build_phase_line(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    rhs, note = autonomous_rhs_from_result(result)
    if rhs is None:
        return _unavailable(
            note or "No se pudo obtener f(y) para la línea de fase."
        )

    _, _, y_min, y_max = plot_bounds(result, x_min=x_min, x_max=x_max)
    data = phase_line(rhs, y_min=y_min, y_max=y_max)
    mask = np.isfinite(data["f(y)"])
    if not np.any(mask):
        return _unavailable(
            "No se pudo evaluar f(y) en el intervalo de la línea de fase."
        )

    traces = [
        _line(data["y"][mask], data["f(y)"][mask], label="f(y)"),
        _line(
            [y_min, y_max],
            [0.0, 0.0],
            color="#616161",
            width=1.0,
            dash="dash",
        ),
    ]
    return _ok(
        _figure_2d(
            "Línea de fase",
            traces,
            x_label="y",
            y_label="f(y)",
            zero_line=True,
        ),
        note or "",
    )


def _build_equilibria(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    rhs, note = autonomous_rhs_from_result(result)
    if rhs is None:
        return _unavailable(
            note or "No se pudo obtener f(y) para los puntos de equilibrio."
        )

    points = equilibrium_points(rhs)
    if not points:
        return _unavailable(
            "No se encontraron puntos de equilibrio reales para esta EDO "
            "autónoma en el intervalo."
        )

    _, _, y_min, y_max = plot_bounds(result, x_min=x_min, x_max=x_max)
    equilibrium_y = [float(point["y"]) for point in points]
    y_min = min(y_min, min(equilibrium_y) - 1.0)
    y_max = max(y_max, max(equilibrium_y) + 1.0)
    data = phase_line(rhs, y_min=y_min, y_max=y_max)
    mask = np.isfinite(data["f(y)"])

    traces: list[dict[str, Any]] = []
    if np.any(mask):
        traces.append(
            _line(
                data["y"][mask],
                data["f(y)"][mask],
                label="f(y)",
                color="#90a4ae",
                width=1.5,
            )
        )
    colors = {
        "asintóticamente estable": "#2e7d32",
        "inestable": "#c62828",
    }
    for point in points:
        y_value = float(point["y"])
        stability = str(point["stability"])
        traces.append(
            _points(
                [y_value],
                [0.0],
                color=colors.get(stability, "#6a1b9a"),
                text=[f"y = {y_value:g}\n{stability}"],
            )
        )
    traces.append(
        _line(
            [y_min, y_max],
            [0.0, 0.0],
            color="#616161",
            width=1.0,
            dash="dash",
        )
    )
    return _ok(
        _figure_2d(
            "Puntos de equilibrio",
            traces,
            x_label="y",
            y_label="f(y)",
            zero_line=True,
        ),
        note or "",
    )


def _build_surface(
    result: SolveResult, x_min: float, x_max: float
) -> dict[str, Any]:
    rhs, note = rhs_from_result(result)
    if rhs is None:
        return _unavailable(
            note or "No se pudo obtener f(x, y) para la superficie."
        )

    x_min, x_max, y_min, y_max = plot_bounds(
        result, x_min=x_min, x_max=x_max
    )
    grid_size = 50
    x_values = np.linspace(x_min, x_max, grid_size)
    y_values = np.linspace(y_min, y_max, grid_size)
    grid_x, grid_y = np.meshgrid(x_values, y_values)
    try:
        function = sp.lambdify((X, Y), rhs, modules=lambdify_modules())
        with np.errstate(all="ignore"):
            z_values = np.asarray(function(grid_x, grid_y), dtype=float)
        z_values = np.broadcast_to(z_values, grid_x.shape).astype(float)
    except Exception as exc:
        return _unavailable(
            f"No se pudo evaluar f(x, y) para la superficie: {exc}"
        )
    if not np.any(np.isfinite(z_values)):
        return _unavailable(
            "La superficie no tiene valores finitos en el intervalo."
        )

    surface = {
        "x": _clean_grid(grid_x),
        "y": _clean_grid(grid_y),
        "z": _clean_grid(z_values),
    }
    return _ok(_figure_3d("Superficie z = f(x, y)", surface), note or "")


_BUILDERS = {
    "solution": _build_solution,
    "direction_field": _build_direction_field,
    "isoclines": _build_isoclines,
    "family": _build_family,
    "phase_line": _build_phase_line,
    "equilibria": _build_equilibria,
    "surface": _build_surface,
}


def build_plot(
    result: SolveResult,
    mode: str,
    *,
    x_min: float = -5.0,
    x_max: float = 5.0,
) -> dict[str, Any]:
    """Construye la respuesta de ``/plot`` para un modo concreto."""

    if mode not in _BUILDERS:
        raise ValueError(
            "Modo de gráfica desconocido. Usa uno de: "
            + ", ".join(sorted(_BUILDERS))
            + "."
        )
    payload: dict[str, Any] = {"mode": mode, "label": PLOT_MODES[mode]}
    if getattr(result, "error", None):
        payload.update(_unavailable(f"No se puede graficar: {result.error}"))
        return payload
    try:
        payload.update(_BUILDERS[mode](result, float(x_min), float(x_max)))
    except Exception as exc:  # defensa: nunca romper el endpoint
        payload.update(
            _unavailable(
                f"No se pudo graficar: {type(exc).__name__}: {exc}"
            )
        )
    return payload


__all__ = ["PLOT_MODES", "build_plot"]
