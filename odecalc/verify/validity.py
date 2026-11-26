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


def _is_even_rational(exponent: sp.Expr) -> bool:
    if isinstance(exponent, sp.Rational):
        return int(exponent.q) % 2 == 0
    return False


def _domain_boundaries(
    expr: sp.Expr,
    *,
    x0: float | None = None,
) -> tuple[list[sp.Expr], list[str]]:
    candidates: list[sp.Expr] = []
    domain_errors: list[str] = []
    try:
        _, denominator = sp.fraction(sp.together(expr))
    except Exception:
        denominator = sp.Integer(1)
    if denominator != 1 and denominator != 0:
        try:
            candidates.extend(sp.solve(sp.Eq(denominator, 0), X))
        except Exception:
            pass

    for atom in sp.preorder_traversal(expr):
        if isinstance(atom, sp.log):
            argument = atom.args[0]
            try:
                candidates.extend(sp.solve(sp.Eq(argument, 0), X))
            except Exception:
                pass
            if x0 is not None and not (argument.free_symbols - {X}):
                try:
                    val = complex(sp.N(argument.subs(X, x0)))
                    if abs(val.imag) < 1e-10 and val.real <= 0:
                        domain_errors.append(
                            "El punto inicial x₀ está fuera del dominio del logaritmo."
                        )
                except Exception:
                    pass
        elif isinstance(atom, sp.Pow) and _is_even_rational(atom.exp):
            base = atom.args[0]
            try:
                candidates.extend(sp.solve(sp.Eq(base, 0), X))
            except Exception:
                pass
            if x0 is not None and not (base.free_symbols - {X}):
                try:
                    val = complex(sp.N(base.subs(X, x0)))
                    if abs(val.imag) < 1e-10 and (
                        val.real < -1e-12
                        or (atom.exp.is_negative and abs(val.real) < 1e-12)
                    ):
                        domain_errors.append(
                            "El punto inicial x₀ está fuera del dominio real de la raíz de índice par."
                        )
                except Exception:
                    pass
        elif isinstance(atom, (sp.asin, sp.acos)):
            argument = atom.args[0]
            for bound in (-1, 1):
                try:
                    candidates.extend(sp.solve(sp.Eq(argument - bound, 0), X))
                except Exception:
                    pass
            if x0 is not None and not (argument.free_symbols - {X}):
                try:
                    val = complex(sp.N(argument.subs(X, x0)))
                    if abs(val.imag) < 1e-10 and abs(val.real) > 1.0 + 1e-12:
                        domain_errors.append(
                            "El punto inicial x₀ está fuera del dominio [-1, 1] de la función inversa."
                        )
                except Exception:
                    pass
        elif isinstance(atom, (sp.tan, sp.sec, sp.cot, sp.csc)):
            argument = atom.args[0]
            if not (argument.free_symbols - {X}):
                offset = sp.pi / 2 if isinstance(atom, (sp.tan, sp.sec)) else sp.Integer(0)
                center_k = 0
                if x0 is not None:
                    try:
                        arg_val = float(sp.N(argument.subs(X, x0)))
                        center_k = round((arg_val - float(offset)) / math.pi)
                    except Exception:
                        center_k = 0
                for k in range(center_k - 2, center_k + 3):
                    try:
                        candidates.extend(
                            sp.solve(sp.Eq(argument, offset + k * sp.pi), X)
                        )
                    except Exception:
                        pass
    return candidates, domain_errors


def _denominator_zero_candidates(expr: sp.Expr) -> list[sp.Expr]:
    candidates, _ = _domain_boundaries(expr)
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
    domain_errors: list[str] = []

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
        rhs_candidates, rhs_errors = _domain_boundaries(rhs, x0=x0)
        domain_errors.extend(rhs_errors)
        numeric_singularities.extend(
            pt
            for pt in _real_points(rhs_candidates)
            if not any(abs(pt - existing) < 1e-9 for existing in numeric_singularities)
        )

    if solution is not None:
        candidates, sol_errors = _domain_boundaries(solution.expr, x0=x0)
        domain_errors.extend(sol_errors)
        for pt in _real_points(candidates):
            if not any(abs(pt - existing) < 1e-9 for existing in numeric_singularities):
                numeric_singularities.append(pt)
        numeric_singularities.sort()
        for point in numeric_singularities:
            singular_points.append(f"x = {point:g}")
        if numeric_singularities:
            notes.append(
                "Hay singularidades reales o fronteras de dominio en "
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
    elif numeric_singularities:
        numeric_singularities.sort()
        for point in numeric_singularities:
            singular_points.append(f"x = {point:g}")

    notes.extend(dict.fromkeys(domain_errors))
    interval: str | None = None
    if domain_errors and x0 is not None:
        interval = f"No definido en los reales en x₀ = {x0:g}"
    elif x0 is not None and numeric_singularities:
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
