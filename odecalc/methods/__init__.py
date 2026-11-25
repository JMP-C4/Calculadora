"""Registro de solucionadores por método."""

from __future__ import annotations

from typing import Callable

from odecalc.methods import (
    bernoulli,
    clairaut,
    dsolve_fallback,
    exact,
    homogeneous,
    integrating_factor,
    lagrange,
    linear,
    reducible,
    riccati,
    separable,
    substitution,
)
from odecalc.models import Match, ParsedODE, Solution, Step

MethodReturn = tuple[Solution, list[Step], list[Solution]]


def solve_method(method: str, parsed: ParsedODE, match: Match) -> MethodReturn:
    if method == "exact":
        return exact.solve(parsed, match)
    if method.startswith("integrating_factor_"):
        return integrating_factor.solve(match)
    if method == "clairaut":
        return clairaut.solve(match)
    if method == "lagrange":
        return lagrange.solve(match)
    if parsed.rhs is None:
        raise ValueError(f"El método {method} requiere una forma explícita y' = f(x,y).")
    if method == "linear":
        return linear.solve(parsed.rhs, match)
    if method == "separable":
        return separable.solve(parsed.rhs, match)
    if method == "bernoulli":
        return bernoulli.solve(parsed.rhs, match)
    if method == "homogeneous":
        return homogeneous.solve(parsed.rhs, match)
    if method == "reducible_homogeneous":
        return reducible.solve(parsed.rhs, match)
    if method == "substitution_linear_combo":
        return substitution.solve(parsed.rhs, match)
    if method == "riccati":
        return riccati.solve(parsed.rhs, match)
    raise ValueError(f"Método desconocido: {method}")


def solve_with_dsolve(parsed: ParsedODE) -> MethodReturn:
    return dsolve_fallback.solve(parsed)


__all__ = ["solve_method", "solve_with_dsolve", "MethodReturn"]
