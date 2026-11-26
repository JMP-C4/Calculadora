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


def lambdify_modules() -> list[object]:
    """Devuelve módulos compartidos (SciPy special + NumPy) para ``sp.lambdify``."""

    import numpy as np
    import scipy.special as scipy_special

    def _si(value):
        return scipy_special.sici(value)[0]

    def _ci(value):
        return scipy_special.sici(value)[1]

    def _acot(value):
        arr = np.asarray(value)
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(arr == 0, np.pi / 2, np.arctan(1.0 / arr))
        return out.item() if np.ndim(value) == 0 else out

    return [
        {
            "erf": scipy_special.erf,
            "erfi": scipy_special.erfi,
            "Ei": scipy_special.expi,
            "Si": _si,
            "Ci": _ci,
            "acot": _acot,
        },
        "numpy",
    ]


__all__ = ["X", "Y", "DY", "DX", "DY_DIFF", "C", "C1", "U", "V", "P", "lambdify_modules"]
