"""Datos para gráficas, sin dependencias de interfaz.

Las funciones de este subpaquete devuelven arreglos/listas que cualquier
frontend (tkinter, web, cuaderno) puede dibujar con Matplotlib, Plotly o SVG.
"""

from odecalc.plotting.data import (
    direction_field,
    equilibrium_points,
    family_curves,
    isoclines,
    phase_line,
    solution_curve,
)
from odecalc.plotting.prepare import (
    autonomous_rhs_from_result,
    family_expression_from_result,
    plot_bounds,
    rhs_from_result,
)

__all__ = [
    "direction_field",
    "equilibrium_points",
    "family_curves",
    "isoclines",
    "phase_line",
    "solution_curve",
    "autonomous_rhs_from_result",
    "family_expression_from_result",
    "plot_bounds",
    "rhs_from_result",
]
