"""Respaldo basado en ``sympy.dsolve`` (siempre marcado como tal)."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.common import (
    explicit_solution,
    implicit_solution,
    make_step,
    safe_simplify,
)
from odecalc.models import ParsedODE, Solution, Step
from odecalc.symbols import C, DY, X, Y


def solve(parsed: ParsedODE) -> tuple[Solution, list[Step], list[Solution]]:
    y_func = sp.Function("y")(X)
    derivative = sp.Derivative(y_func, X)

    if parsed.rhs is not None:
        ode = sp.Eq(derivative, parsed.rhs.subs(Y, y_func))
    elif parsed.F is not None:
        implicit = parsed.F.subs({DY: derivative, Y: y_func})
        ode = sp.Eq(implicit, 0)
    else:
        raise ValueError("No hay una ecuación utilizable para dsolve.")

    raw = sp.dsolve(ode, y_func)
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    if not isinstance(raw, sp.Eq):
        raise ValueError("dsolve no devolvió una ecuación utilizable.")

    steps = [
        make_step(
            1,
            "Respaldo simbólico: sympy.dsolve",
            sp.latex(raw),
            r"Ningún método propio produjo una solución verificable. Se usa $\mathrm{dsolve}$ "
            "como respaldo; el resultado se verificará antes de presentarlo como correcto.",
        )
    ]

    if raw.lhs == y_func:
        solution = explicit_solution(raw.rhs)
    elif raw.rhs == y_func:
        solution = explicit_solution(raw.lhs)
    else:
        # Forma implícita: se intenta identificar el potencial y la constante.
        lhs = raw.lhs
        rhs = raw.rhs
        if lhs.has(y_func) and not rhs.has(y_func):
            potential = lhs.subs(y_func, Y)
            solution = implicit_solution(potential)
        elif rhs.has(y_func) and not lhs.has(y_func):
            potential = rhs.subs(y_func, Y)
            solution = implicit_solution(potential)
        else:
            raise ValueError("La forma devuelta por dsolve no es reconocible.")

    return solution, steps, []


__all__ = ["solve"]
