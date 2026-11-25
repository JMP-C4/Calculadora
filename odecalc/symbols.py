"""Símbolos compartidos por el motor ``odecalc``.

La variable independiente es ``x`` y la dependiente se representa con el
símbolo ``y`` durante el cálculo simbólico.  ``DY`` representa ``dy/dx`` en
las formas implícitas y ``DX``/``DY_DIFF`` representan los diferenciales de
la forma ``M(x, y) dx + N(x, y) dy = 0``.
"""

from __future__ import annotations

import sympy as sp

X = sp.Symbol("x", real=True)
Y = sp.Symbol("y", real=True)
DY = sp.Symbol("Dy")
DX = sp.Symbol("Dx")
DY_DIFF = sp.Symbol("Dy_diff")
C = sp.Symbol("C", real=True)
C1 = sp.Symbol("C1", real=True)

# Variables de integración internas (no se exponen al usuario).
U = sp.Symbol("u", real=True)
V = sp.Symbol("v", real=True)
P = sp.Symbol("p", real=True)

__all__ = ["X", "Y", "DY", "DX", "DY_DIFF", "C", "C1", "U", "V", "P"]
