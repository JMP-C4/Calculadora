"""Ecuaciones de Lagrange ``y = x φ(y') + ψ(y')``.

La forma general requiere una solución paramétrica en p = y'.  El motor
puede clasificarla y dejarla al respaldo simbólico; esta primera versión no
inventa una solución explícita si no puede verificarla.
"""

from __future__ import annotations

from odecalc.models import Match, Solution, Step


def solve(match: Match) -> tuple[Solution, list[Step], list[Solution]]:
    del match
    raise ValueError(
        "La ecuación es de Lagrange. La solución paramétrica general todavía "
        "no está implementada; se intentará el respaldo simbólico."
    )


__all__ = ["solve"]
