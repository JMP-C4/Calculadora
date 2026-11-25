"""Modelos de datos del motor de EDOs.

Todas las estructuras son ``dataclass`` simples y serializables (salvo los
arreglos NumPy del resultado numérico).  La interfaz pública las devuelve tal
cual, de modo que escritorio, web y scripts comparten el mismo contrato.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import sympy as sp

from odecalc.symbols import C


@dataclass
class Match:
    """Un método que puede aplicarse a la ecuación, con su evidencia."""

    method: str
    name: str
    evidence: str
    priority: int = 100
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class Solution:
    """Solución general o particular.

    ``form == "explicit"``: ``expr`` es el lado derecho de ``y = expr``.
    ``form == "implicit"``: la solución es ``expr = value``; ``value`` vale
    ``C`` para la solución general y una constante concreta para la
    particular.
    """

    form: str
    expr: sp.Expr
    value: sp.Expr | None = None
    constant: sp.Symbol | None = None
    latex: str = ""
    branch_note: str | None = None

    @property
    def is_explicit(self) -> bool:
        return self.form == "explicit"

    @property
    def is_implicit(self) -> bool:
        return self.form == "implicit"


@dataclass
class Step:
    """Un paso del procedimiento, con LaTeX y justificación."""

    number: int
    title: str
    latex: str
    explanation: str
    ascii: str | None = None


@dataclass
class Verification:
    """Resultado de comprobar una solución contra la ecuación original."""

    status: str  # "ok" | "fail" | "unverified"
    residual: sp.Expr | None = None
    simplified_residual: str | None = None
    numeric_checked: bool = False
    points_checked: int = 0
    message: str = ""


@dataclass
class Validity:
    """Dominio e intervalo de validez de una solución."""

    domain: str = ""
    interval: str | None = None
    singular_points: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class NumericResult:
    """Resultado del respaldo numérico."""

    x_arr: np.ndarray | None
    y_arr: np.ndarray | None
    success: bool
    message: str
    method: str = ""
    blow_up: bool = False
    stiff: bool = False
    interval: tuple[float, float] | None = None
    error_estimate: float | None = None


@dataclass
class Attempt:
    """Registro de un método intentado (útil para comparar estrategias)."""

    method: str
    success: bool
    verification_status: str | None = None
    message: str = ""


@dataclass
class SolveResult:
    """Contrato de salida público de ``odecalc.api.solve``."""

    input_text: str
    input_latex: str = ""
    standard_form: str = ""
    classifications: list[Match] = field(default_factory=list)
    chosen_method: str | None = None
    general: Solution | None = None
    particular: Solution | None = None
    steps: list[Step] = field(default_factory=list)
    verification: Verification | None = None
    particular_verification: Verification | None = None
    validity: Validity = field(default_factory=Validity)
    singular_solutions: list[Solution] = field(default_factory=list)
    numeric: NumericResult | None = None
    warnings: list[str] = field(default_factory=list)
    timing_ms: dict[str, float] = field(default_factory=dict)
    attempts: list[Attempt] = field(default_factory=list)
    error: str | None = None


@dataclass
class ParsedODE:
    """Resultado del parser seguro."""

    original: str
    kind: str  # "explicit" | "implicit" | "differential"
    rhs: sp.Expr | None = None
    F: sp.Expr | None = None
    M: sp.Expr | None = None
    N: sp.Expr | None = None
    latex_str: str = ""
    standard_form: str = ""
    dominio: str = ""
    error: str | None = None


__all__ = [
    "Match",
    "Solution",
    "Step",
    "Verification",
    "Validity",
    "NumericResult",
    "Attempt",
    "SolveResult",
    "ParsedODE",
    "C",
]
