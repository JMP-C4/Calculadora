"""Serialización JSON del contrato ``SolveResult``.

Las interfaces web y los registros de cálculo necesitan un formato estable,
sin objetos SymPy ni arreglos NumPy.  Este módulo centraliza esa conversión.
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

import numpy as np
import sympy as sp

from odecalc.models import SolveResult


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, sp.Expr):
        return sp.sstr(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if is_dataclass(value):
        return {
            field: _jsonable(getattr(value, field))
            for field in value.__dataclass_fields__
        }
    return str(value)


def solution_to_dict(solution) -> dict[str, Any] | None:
    if solution is None:
        return None
    return {
        "form": solution.form,
        "is_explicit": solution.is_explicit,
        "expr": sp.sstr(solution.expr),
        "latex": solution.latex,
        "value": _jsonable(solution.value),
        "branch_note": solution.branch_note,
    }


def result_to_dict(result: SolveResult) -> dict[str, Any]:
    """Convierte el resultado completo en estructuras JSON-serializables."""

    return {
        "input_text": result.input_text,
        "input_latex": result.input_latex,
        "standard_form": result.standard_form,
        "classifications": [
            {
                "method": match.method,
                "name": match.name,
                "evidence": match.evidence,
                "priority": match.priority,
                "data": _jsonable(match.data),
            }
            for match in result.classifications
        ],
        "chosen_method": result.chosen_method,
        "general": solution_to_dict(result.general),
        "particular": solution_to_dict(result.particular),
        "steps": [
            {
                "number": step.number,
                "title": step.title,
                "latex": step.latex,
                "explanation": step.explanation,
                "ascii": step.ascii,
            }
            for step in result.steps
        ],
        "verification": _jsonable(result.verification),
        "particular_verification": _jsonable(result.particular_verification),
        "validity": _jsonable(result.validity),
        "singular_solutions": [
            solution_to_dict(solution) for solution in result.singular_solutions
        ],
        "numeric": _jsonable(result.numeric),
        "warnings": list(result.warnings),
        "timing_ms": {key: round(float(value), 4) for key, value in result.timing_ms.items()},
        "attempts": _jsonable(result.attempts),
        "error": result.error,
    }


__all__ = ["result_to_dict", "solution_to_dict"]
