"""Parsing y validación de ecuaciones diferenciales de primer orden.

El parser acepta la notación ``dy/dx = f(x, y)`` y ``y' = f(x, y)`` en
sintaxis Python/SymPy. Devuelve el lado derecho como expresión SymPy y una
cadena LaTeX lista para el panel de previsualización.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)

# Funciones y constantes permitidas en el lado derecho.
_ALLOWED_LOCALS: dict[str, object] = {
    "x": x,
    "y": y,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "pi": sp.pi,
    "E": sp.E,
    "oo": sp.oo,
    "Integral": sp.Integral,
}

_FIRST_ORDER_LHS = re.compile(r"^(?:dy/dx|y'|y'\(x\)|dy\(x\)/dx)$")
_HIGHER_ORDER_PATTERNS = (
    re.compile(r"d\^?[2-9]y/dx\^?[2-9]"),
    re.compile(r"d[2-9]y/dx[2-9]"),
    re.compile(r"y'{2,}"),
)


@dataclass
class ParseResult:
    """Resultado del parsing de una EDO."""

    rhs: sp.Expr | None
    latex_str: str
    error: str | None


def _error(message: str) -> ParseResult:
    return ParseResult(rhs=None, latex_str="", error=message)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _has_higher_order(text: str) -> bool:
    compact = _compact(text)
    return any(pattern.search(compact) for pattern in _HIGHER_ORDER_PATTERNS)


def parse_ode(text: str) -> ParseResult:
    """Parsea una EDO de primer orden y devuelve su lado derecho.

    Parameters
    ----------
    text:
        Ecuación en sintaxis Python/SymPy, por ejemplo ``"dy/dx = x + y"``.

    Returns
    -------
    ParseResult
        ``rhs`` y ``latex_str`` poblados si la entrada es válida; en caso
        contrario ``rhs`` es ``None`` y ``error`` contiene una explicación.
    """

    if not isinstance(text, str):
        return _error("La ecuación debe ser una cadena de texto.")

    raw = text.strip()
    if not raw:
        return _error("La ecuación está vacía. Ingresa una EDO de primer orden.")

    if _has_higher_order(raw):
        return _error(
            "Solo se admiten EDOs de primer orden; se detectó una derivada "
            "de orden superior."
        )

    if "=" not in raw:
        return _error(
            "Falta el signo '='. Usa una forma como dy/dx = f(x, y) o y' = f(x, y)."
        )
    if raw.count("=") != 1:
        return _error("La ecuación debe contener exactamente un signo '='.")

    lhs_text, rhs_text = (part.strip() for part in raw.split("=", 1))
    lhs_compact = _compact(lhs_text)

    if not _FIRST_ORDER_LHS.match(lhs_compact):
        return _error(
            "El lado izquierdo debe ser dy/dx o y'. "
            "Ejemplo: dy/dx = x + y."
        )

    if not rhs_text:
        return _error("El lado derecho de la ecuación está vacío.")

    try:
        rhs = sp.sympify(rhs_text, locals=_ALLOWED_LOCALS)
    except (sp.SympifyError, SyntaxError, TypeError, ValueError) as exc:
        return _error(f"Sintaxis inválida en el lado derecho: {exc}")

    if not isinstance(rhs, sp.Expr):
        return _error("El lado derecho no es una expresión matemática válida.")

    if rhs.has(sp.Derivative):
        return _error("El lado derecho no debe contener derivadas.")

    unknown_symbols = {symbol.name for symbol in rhs.free_symbols - {x}}
    if unknown_symbols:
        names = ", ".join(sorted(unknown_symbols))
        return _error(f"Símbolos no permitidos en el lado derecho: {names}.")

    latex_str = r"\frac{dy}{dx} = " + sp.latex(rhs)
    return ParseResult(rhs=rhs, latex_str=latex_str, error=None)


__all__ = ["ParseResult", "parse_ode", "x", "y"]
