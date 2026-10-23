"""Solución simbólica de EDOs de primer orden mediante SymPy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import sympy as sp

from math_engine.step_generator import (
    StepByStepResult,
    classify_ode,
    generate_steps,
)

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)


@dataclass
class SymbolicResult:
    """Resultado de una resolución simbólica."""

    general_solution: sp.Eq | None
    particular_solution: sp.Eq | None
    latex_general: str
    latex_particular: str
    error: str | None
    ode_type: str | None
    step_by_step: StepByStepResult | None = None


def _first_solution(raw: Any) -> sp.Eq | None:
    """Normaliza la salida de ``dsolve`` (puede ser una lista de soluciones)."""

    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    if isinstance(raw, sp.Eq):
        return raw
    return None


def _apply_conditions(
    general: sp.Eq,
    ode: sp.Eq,
    conditions: Any,
) -> sp.Eq | None:
    x0 = getattr(conditions, "x0", None)
    y0 = getattr(conditions, "y0", None)
    if x0 is None or y0 is None:
        return None

    expression = general.rhs
    constants = [
        symbol
        for symbol in expression.free_symbols
        if symbol != x and getattr(symbol, "is_Symbol", False)
    ]

    if not constants:
        evaluated = sp.simplify(expression.subs(x, x0))
        return general if sp.simplify(evaluated - y0) == 0 else None

    constant = constants[0]
    equation = sp.Eq(expression.subs(x, x0), y0)
    try:
        solutions = sp.solve(equation, constant)
    except Exception:
        solutions = []

    if solutions:
        particular = sp.simplify(expression.subs(constant, solutions[0]))
        return sp.Eq(y, particular)

    try:
        raw = sp.dsolve(ode, y, ics={y.subs(x, x0): y0})
        return _first_solution(raw)
    except Exception:
        return None


def solve_symbolic(
    rhs: sp.Expr,
    conditions: Any = None,
) -> SymbolicResult:
    """Resuelve ``dy/dx = rhs`` de forma simbólica.

    Parameters
    ----------
    rhs:
        Lado derecho de la EDO como expresión SymPy.
    conditions:
        Objeto con atributos ``x0`` y ``y0`` (por ejemplo
        ``SolverConditions``). Si se proporciona, se calcula la solución
        particular.
    """

    ode_type = classify_ode(rhs)
    ode = sp.Eq(sp.Derivative(y, x), rhs)

    try:
        raw_solution = sp.dsolve(ode, y)
    except Exception as exc:  # dsolve puede lanzar distintos errores
        error = (
            "No se pudo encontrar una solución simbólica para la EDO: "
            f"{exc}. Se recomienda intentar la solución numérica."
        )
        result = SymbolicResult(
            general_solution=None,
            particular_solution=None,
            latex_general="",
            latex_particular="",
            error=error,
            ode_type=ode_type,
            step_by_step=None,
        )
        result.step_by_step = generate_steps(
            rhs,
            symbolic_result=result,
            conditions=conditions,
            ode_type=ode_type,
        )
        return result

    general = _first_solution(raw_solution)
    if general is None:
        error = (
            "SymPy no devolvió una solución simbólica explícita para la EDO. "
            "Se recomienda intentar la solución numérica."
        )
        result = SymbolicResult(
            general_solution=None,
            particular_solution=None,
            latex_general="",
            latex_particular="",
            error=error,
            ode_type=ode_type,
            step_by_step=None,
        )
        result.step_by_step = generate_steps(
            rhs,
            symbolic_result=result,
            conditions=conditions,
            ode_type=ode_type,
        )
        return result

    particular = _apply_conditions(general, ode, conditions)

    result = SymbolicResult(
        general_solution=general,
        particular_solution=particular,
        latex_general=sp.latex(general),
        latex_particular=sp.latex(particular) if particular is not None else "",
        error=None,
        ode_type=ode_type,
        step_by_step=None,
    )
    result.step_by_step = generate_steps(
        rhs,
        symbolic_result=result,
        conditions=conditions,
        ode_type=ode_type,
    )
    return result


__all__ = ["SymbolicResult", "solve_symbolic", "x", "y"]
