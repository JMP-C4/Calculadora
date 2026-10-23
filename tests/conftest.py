"""Estrategias compartidas de Hypothesis para ODE Calculator.

Los nombres de las estrategias coinciden con los usados en ``tasks.md`` y
``design.md`` para que los tests de propiedades puedan reutilizarlas.
"""

from __future__ import annotations

import sympy as sp
from hypothesis import strategies as st

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)

# --- Ecuaciones válidas de primer orden en sintaxis Python/SymPy -------------
VALID_ODE_TEXTS: tuple[str, ...] = (
    "dy/dx = x + y",
    "y' = sin(x)*y",
    "dy/dx = y",
    "dy/dx = x",
    "dy/dx = x*y",
    "dy/dx = exp(-x)*y",
    "dy/dx = y**2 - y",
    "dy/dx = y/x",
    "dy/dx = sqrt(x)",
    "dy/dx = cos(x) + tan(x)",
    "dy/dx = log(x) + 1",
    "dy/dx = Integral(x, x)",
)

# --- Entradas que deben rechazarse ------------------------------------------
INVALID_ODE_TEXTS: tuple[str, ...] = (
    "",
    "   ",
    "dy/dx",
    "x + y",
    "dy/dx = ",
    "= x + y",
    "d2y/dx2 = y",
    "y'' = x",
    "dy/dx = x + y + z",
    "dy/dx = ___",
    "dy/dx = x = y",
)

valid_ode_texts = st.sampled_from(VALID_ODE_TEXTS)

invalid_ode_texts = st.one_of(
    st.sampled_from(INVALID_ODE_TEXTS),
    st.text(max_size=8).filter(lambda value: "=" not in value),
    st.from_regex(r"d[2-9]y/dx[2-9]\s*=\s*[a-z]+", fullmatch=True),
)

# --- EDOs resolubles por el solver simbólico --------------------------------
# Cada entrada es (rhs, tipo esperado). Se usan expresiones SymPy puras para
# evitar depender del parser en las propiedades del solver.
SOLVABLE_ODES: tuple[tuple[sp.Expr, str], ...] = (
    (y, "separable"),
    (x * y, "separable"),
    (sp.sin(x) * y, "separable"),
    (x, "linear"),
    (x + y, "linear"),
    (sp.exp(x) - y, "linear"),
    (y / x, "homogeneous"),
    ((x + y) / x, "homogeneous"),
    (y**2 - y, "bernoulli"),
    (sp.exp(-x) * y**2, "bernoulli"),
    (-(2 * x + y) / (x + 2 * y), "exact"),
)

solvable_odes = st.sampled_from(SOLVABLE_ODES)

# --- EDOs para el solver numérico -------------------------------------------
# (rhs, x0, y0, x_min, x_max)
NUMERIC_ODES: tuple[tuple[sp.Expr, float, float, float, float], ...] = (
    (y, 0.0, 1.0, 0.0, 2.0),
    (-2.0 * y, 0.0, 1.0, 0.0, 1.5),
    (sp.sin(x), 0.0, 0.0, 0.0, 3.0),
    (x + y, 0.0, 1.0, 0.0, 1.0),
    (y**2 - y, 0.0, 2.0, 0.0, 0.5),
    (sp.exp(-x) * y, 0.0, 1.0, 0.0, 2.0),
)

numeric_odes = st.sampled_from(NUMERIC_ODES)

# --- RHS válidos para Direction Field / Surface 3D --------------------------
VALID_RHS_EXPRS: tuple[sp.Expr, ...] = (
    x + y,
    x * y,
    sp.sin(x) * y,
    x**2 - y,
    sp.exp(-x) * y,
    y / x,
    sp.cos(x) + y,
)

valid_rhs_exprs = st.sampled_from(VALID_RHS_EXPRS)

# --- Atajos de teclado ------------------------------------------------------
# clave Tk -> (token insertado, colocar cursor dentro de paréntesis)
SHORTCUT_MAP: dict[str, tuple[str, bool]] = {
    "<Control-d>": ("dy/dx", False),
    "<Control-i>": ("Integral", False),
    "<Control-Shift-I>": ("oo", False),
    "<Control-e>": ("exp()", True),
    "<Control-Shift-S>": ("sqrt()", True),
    "<Control-p>": ("pi", False),
}
