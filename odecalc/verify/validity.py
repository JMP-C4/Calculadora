"""Análisis de dominio, singularidades e intervalo de validez."""

from __future__ import annotations

import math

import sympy as sp

from odecalc.models import Solution, Validity
from odecalc.symbols import X, Y


def _real_points(expressions: list[sp.Expr]) -> list[float]:
    points: list[float] = []
    for expression in expressions:
        try:
            if expression.free_symbols - {X}:
                continue
            value = complex(sp.N(expression))
        except Exception:
            continue
        if abs(value.imag) > 1e-10 or not math.isfinite(value.real):
            continue
        if not any(abs(value.real - existing) < 1e-9 for existing in points):
            points.append(float(value.real))
    points.sort()
    return points


def _denominator_zero_candidates(expr: sp.Expr) -> list[sp.Expr]:
    candidates: list[sp.Expr] = []
    try:
        numerator, denominator = sp.fraction(sp.together(expr))
    except Exception:
        return candidates
    if denominator != 1 and denominator != 0:
        try:
            candidates.extend(sp.solve(sp.Eq(denominator, 0), X))
        except Exception:
            pass
    # Argumentos de logaritmos y raíces que pueden restringir el dominio.
    for atom in sp.preorder_traversal(expr):
        if isinstance(atom, sp.log):
            argument = atom.args[0]
            try:
                candidates.extend(sp.solve(sp.Eq(argument, 0), X))
            except Exception:
                pass
    return candidates


def analyze_validity(
    rhs: sp.Expr | None,
    solution: Solution | None,
    *,
    x0: float | None = None,
    y0: float | None = None,
) -> Validity:
    del y0
    notes: list[str] = []
    singular_points: list[str] = []
    numeric_singularities: list[float] = []

    if rhs is not None:
        try:
            rhs_denominator = sp.fraction(sp.together(rhs))[1]
            if rhs_denominator not in (1, 0):
                notes.append(
                    "f(x,y) contiene denominadores; la solución puede dejar de "
                    "existir donde éstos se anulan."
                )
        except Exception:
            pass

    if solution is not None:
        candidates = _denominator_zero_candidates(solution.expr)
        numeric_singularities = _real_points(candidates)
        for point in numeric_singularities:
            singular_points.append(f"x = {point:g}")
        if numeric_singularities:
            notes.append(
                "Hay singularidades reales de la solución en "
                + ", ".join(f"x = {point:g}" for point in numeric_singularities)
                + "."
            )
        if solution.branch_note:
            notes.append(solution.branch_note)
        if solution.expr.has(sp.Integral):
            notes.append(
                "La solución conserva una integral no elemental; el dominio "
                "debe interpretarse en sentido local."
            )

    interval: str | None = None
    if x0 is not None and numeric_singularities:
        left = max((point for point in numeric_singularities if point < x0), default=None)
        right = min((point for point in numeric_singularities if point > x0), default=None)
        if left is not None and right is not None:
            interval = f"({left:g}, {right:g})"
        elif left is not None:
            interval = f"({left:g}, ∞)"
        elif right is not None:
            interval = f"(-∞, {right:g})"
        if interval:
            notes.append(
                f"Intervalo de validez que contiene x₀ = {x0:g}: {interval}."
            )
    elif x0 is not None:
        interval = "(-∞, ∞) en ausencia de otras singularidades"
        notes.append(
            "No se detectaron singularidades reales de la solución en la "
            "variable independiente."
        )

    if solution is not None and solution.is_implicit:
        domain = "Dominio definido implícitamente por F(x,y) = C."
    else:
        domain = "x real donde la solución y sus derivadas están definidas."
    return Validity(
        domain=domain,
        interval=interval,
        singular_points=singular_points,
        notes=notes,
    )


__all__ = ["analyze_validity"]
