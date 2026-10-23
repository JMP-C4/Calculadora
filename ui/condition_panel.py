"""Panel de condiciones iniciales y de visualización.

Solo se define aquí el contenedor de datos; el widget ``ConditionPanel`` se
implementa en la tarea correspondiente de la UI.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SolverConditions:
    """Condiciones iniciales e intervalo usado por solvers y gráficas."""

    x0: float | None = None
    y0: float | None = None
    x_min: float = -5.0
    x_max: float = 5.0
    y_min: float | None = None
    y_max: float | None = None


__all__ = ["SolverConditions"]
