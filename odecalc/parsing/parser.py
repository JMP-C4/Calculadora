"""Parser seguro para EDOs de primer orden.

Acepta, entre otras, estas formas de libro:

* ``y' = f(x, y)`` y ``dy/dx = f(x, y)``
* ``y' + P(x) y = Q(x)``
* ``M(x, y) dx + N(x, y) dy = 0``
* formas implícitas ``F(x, y, y') = 0`` (Clairaut, Lagrange)

La entrada se valida con una lista blanca de caracteres, nombres y funciones
antes de llamar a ``parse_expr``.  Nunca se ejecuta código arbitrario del
usuario: los atributos, importaciones, subíndices y literales de cadena se
rechazan de forma explícita.
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from odecalc.models import ParsedODE
from odecalc.symbols import DX, DY, DY_DIFF, X, Y

_ALLOWED_NAMES: dict[str, object] = {
    "x": X,
    "y": Y,
    "Dy": DY,
    "Dx": DX,
    "Dyy": DY_DIFF,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "cot": sp.cot,
    "sec": sp.sec,
    "csc": sp.csc,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "acot": sp.acot,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "asinh": sp.asinh,
    "acosh": sp.acosh,
    "atanh": sp.atanh,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.log,
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "sign": sp.sign,
    "floor": sp.floor,
    "ceil": sp.ceiling,
    "pi": sp.pi,
    "E": sp.E,
    "e": sp.E,
    "oo": sp.oo,
    "erf": sp.erf,
    "erfi": sp.erfi,
    "Ei": sp.Ei,
    "Si": sp.Si,
    "Ci": sp.Ci,
    "Integral": sp.Integral,
}

# ``parse_expr`` evalúa las transformaciones en un diccionario global.  Se
# eliminan los builtins y sólo se exponen las piezas imprescindibles de SymPy.
_GLOBAL_DICT: dict[str, object] = {
    "__builtins__": {},
    "Symbol": sp.Symbol,
    "Integer": sp.Integer,
    "Float": sp.Float,
    "Rational": sp.Rational,
    "Function": sp.Function,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "exp": sp.exp,
    "log": sp.log,
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "pi": sp.pi,
    "E": sp.E,
    "I": sp.I,
    "Integral": sp.Integral,
}

_TRANSFORMATIONS = standard_transformations + (
    convert_xor,
    implicit_multiplication_application,
)

_LATEX_FRACTIONS = {"frac", "dfrac", "tfrac", "cfrac"}
_LATEX_WRAPPERS = {
    "mathrm",
    "mathbf",
    "mathit",
    "mathsf",
    "mathtt",
    "text",
    "textrm",
    "operatorname",
}
_LATEX_FUNCTIONS = {
    "sin",
    "cos",
    "tan",
    "cot",
    "sec",
    "csc",
    "asin",
    "acos",
    "atan",
    "acot",
    "sinh",
    "cosh",
    "tanh",
    "asinh",
    "acosh",
    "atanh",
    "exp",
    "ln",
    "log",
}
_LATEX_SIMPLE = {
    "cdot": "*",
    "times": "*",
    "ast": "*",
    "div": "/",
    "pi": "pi",
    "infty": "oo",
    "quad": " ",
    "qquad": " ",
    ",": " ",
    ";": " ",
    ":": " ",
    "!": "",
    " ": " ",
}

_FORBIDDEN_CHARACTERS = re.compile(r"[\[\]{};@#\\\"`]")
_ATTRIBUTE_ACCESS = re.compile(r"\.\s*[A-Za-z_]")
_UNDERSCORE_NAMES = re.compile(r"\b\w*_\w*\b")
_DANGEROUS_WORDS = re.compile(
    r"\b(import|eval|exec|compile|globals|locals|getattr|setattr|delattr|"
    r"lambda|open|class|def|return|yield|raise|try|except|with|as|from)\b",
    re.IGNORECASE,
)

_HIGHER_ORDER_PATTERNS = (
    re.compile(r"d\s*\^?\s*[2-9]\s*y\s*/\s*dx\s*\^?\s*[2-9]"),
    re.compile(r"d\s*[2-9]\s*y\s*/\s*dx\s*[2-9]"),
    re.compile(r"y\s*'{2,}"),
    re.compile(r"y\s*\(\s*[2-9]\s*\)"),
    re.compile(r"\bDerivative\b"),
)

_DERIVATIVE_LHS = re.compile(r"^\s*(?:dy\s*/\s*dx|y\s*'\s*(?:\(\s*x\s*\))?)\s*$")
_PRIME = re.compile(r"y\s*'\s*(?:\(\s*x\s*\))?")
_DY_DX = re.compile(r"d\s*y\s*/\s*d\s*x")
_STANDALONE_DIFF = re.compile(r"(?<![A-Za-z_])d\s*([xy])(?![A-Za-z_])")
# Acotaciones habituales que acompañan al enunciado, p. ej. ``x > 0``.
# Sólo se acepta esta forma cerrada al final: cualquier otro texto sigue
# rechazándose por la lista blanca.
_DOMINIO_FINAL = re.compile(
    r"\s*[,;]?\s*x\s*(?P<operador>>=|≥|\\ge|\\geq|>)\s*0\s*\.?\s*$",
    re.IGNORECASE,
)


def _separar_dominio(texto: str) -> tuple[str, str]:
    """Separa una acotación final ``x > 0`` de la ecuación misma."""

    encontrado = _DOMINIO_FINAL.search(texto)
    if encontrado is None:
        return texto, ""
    operador = encontrado.group("operador")
    if operador in {"≥", r"\ge", r"\geq"}:
        operador = ">="
    return texto[: encontrado.start()].rstrip(), f"x {operador} 0"


def _error(message: str) -> ParsedODE:
    return ParsedODE(original="", kind="", error=message)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _strip_latex_delimiters(text: str) -> str:
    """Quita los delimitadores matemáticos ``$$...$$``, ``$...$``, ``\\[...\\]``."""

    stripped = text.strip()
    for opening, closing in (("$$", "$$"), ("$", "$"), (r"\[", r"\]"), (r"\(", r"\)")):
        if (
            stripped.startswith(opening)
            and stripped.endswith(closing)
            and len(stripped) > len(opening) + len(closing)
        ):
            return stripped[len(opening) : -len(closing)].strip()
    return stripped


def _read_latex_command(text: str, index: int) -> tuple[str, int]:
    """Lee ``\\comando`` y devuelve el nombre sin la barra y el índice final."""

    position = index + 1
    if position >= len(text):
        return "", position
    if text[position].isalpha():
        start = position
        while position < len(text) and text[position].isalpha():
            position += 1
        return text[start:position], position
    return text[position], position + 1


def _read_latex_braced(text: str, index: int) -> tuple[str, int]:
    """Extrae el contenido de ``{...}`` respetando llaves anidadas."""

    depth = 0
    position = index
    while position < len(text):
        char = text[position]
        if char == "\\":
            position += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[index + 1 : position], position + 1
        position += 1
    raise ValueError("Hay una llave LaTeX sin cerrar. Revisa la ecuación.")


def _read_latex_group(text: str, index: int) -> tuple[str, int]:
    """Lee un argumento LaTeX: ``{...}``, ``(...)``, ``\\comando`` o un carácter."""

    position = index
    while position < len(text) and text[position].isspace():
        position += 1
    if position >= len(text):
        return "", position
    if text[position] == "{":
        return _read_latex_braced(text, position)
    if text[position] == "(":
        return _read_latex_parentheses(text, position)
    if text[position] == "\\":
        _, end = _read_latex_command(text, position)
        return text[position:end], end
    return text[position], position + 1


def _read_latex_parentheses(text: str, index: int) -> tuple[str, int]:
    """Extrae el contenido de ``(...)`` respetando paréntesis anidados."""

    depth = 0
    position = index
    while position < len(text):
        char = text[position]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[index + 1 : position], position + 1
        position += 1
    raise ValueError("Hay un paréntesis sin cerrar. Revisa la ecuación.")


def _derivative_fraction(numerator: str, denominator: str) -> str | None:
    """Reconoce ``\\frac{dy}{dx}`` y sus derivadas de orden superior."""

    top = _compact(numerator)
    bottom = _compact(denominator)
    top_match = re.fullmatch(r"d(?:\*\*\(?(\d+)\)?)?([xy])", top)
    bottom_match = re.fullmatch(r"d([xy])(?:\*\*\(?(\d+)\)?)?", bottom)
    if top_match is None or bottom_match is None:
        return None
    top_order = int(top_match.group(1) or 1)
    bottom_order = int(bottom_match.group(2) or 1)
    if top_match.group(2) != "y" or bottom_match.group(1) != "x":
        return None
    if top_order != bottom_order:
        return None
    if top_order == 1:
        return "dy/dx"
    return f"d{top_order}y/dx{top_order}"


def _latex_to_plain(text: str) -> str:
    """Convierte notación LaTeX habitual en la sintaxis que entiende el motor.

    El objetivo es aceptar fórmulas copiadas de un libro o de un editor como
    ``$$\\frac{dy}{dx} = \\frac{x^2}{y}$$`` sin relajar las comprobaciones de
    seguridad: todo el texto convertido sigue pasando por la lista blanca.
    """

    source = _strip_latex_delimiters(text)
    output: list[str] = []
    position = 0

    while position < len(source):
        char = source[position]

        if char == "$":
            position += 1
            continue

        if char == "%":
            while position < len(source) and source[position] != "\n":
                position += 1
            continue

        if char == "^":
            argument, position = _read_latex_group(source, position + 1)
            output.append(f"**({_latex_to_plain(argument)})")
            continue

        if char == "{":
            output.append("(")
            position += 1
            continue

        if char == "}":
            output.append(")")
            position += 1
            continue

        if char == "~":
            output.append(" ")
            position += 1
            continue

        if char != "\\":
            output.append(char)
            position += 1
            continue

        command, position = _read_latex_command(source, position)

        if command in _LATEX_FRACTIONS:
            numerator_raw, position = _read_latex_group(source, position)
            denominator_raw, position = _read_latex_group(source, position)
            numerator = _latex_to_plain(numerator_raw)
            denominator = _latex_to_plain(denominator_raw)
            derivative = _derivative_fraction(numerator, denominator)
            if derivative is not None:
                output.append(derivative)
            else:
                output.append(f"(({numerator})/({denominator}))")
            continue

        if command == "sqrt":
            cursor = position
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            index_raw = None
            if cursor < len(source) and source[cursor] == "[":
                closing = source.find("]", cursor)
                if closing == -1:
                    raise ValueError("Hay un índice de raíz LaTeX sin cerrar.")
                index_raw = source[cursor + 1 : closing]
                position = closing + 1
            radicand_raw, position = _read_latex_group(source, position)
            radicand = _latex_to_plain(radicand_raw)
            if index_raw is None:
                output.append(f"sqrt({radicand})")
            else:
                index = _latex_to_plain(index_raw)
                output.append(f"(({radicand})**(1/({index})))")
            continue

        if command in _LATEX_WRAPPERS:
            content, position = _read_latex_group(source, position)
            output.append(f" {_latex_to_plain(content)} ")
            continue

        if command in _LATEX_FUNCTIONS:
            cursor = position
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            exponent = None
            if cursor < len(source) and source[cursor] == "^":
                exponent_raw, cursor = _read_latex_group(source, cursor + 1)
                exponent = _latex_to_plain(exponent_raw)
                position = cursor
            argument = None
            if cursor < len(source) and source[cursor] == "(":
                argument_raw, position = _read_latex_parentheses(source, cursor)
                argument = _latex_to_plain(argument_raw)
            elif cursor < len(source) and source[cursor] == "{":
                argument_raw, position = _read_latex_braced(source, cursor)
                argument = _latex_to_plain(argument_raw)
            elif cursor < len(source) and source[cursor] in "xyz0123456789":
                argument = source[cursor]
                position = cursor + 1
            if argument is None:
                core = command
            else:
                core = f"{command}({argument})"
            if exponent is not None:
                core = f"({core})**({exponent})"
            output.append(core)
            continue

        if command in ("left", "right"):
            cursor = position
            while cursor < len(source) and source[cursor].isspace():
                cursor += 1
            if cursor < len(source):
                delimiter = source[cursor]
                if delimiter != ".":
                    output.append(delimiter)
                position = cursor + 1
            continue

        if command in _LATEX_SIMPLE:
            output.append(_LATEX_SIMPLE[command])
            continue

        # Comando desconocido: se conserva para que la comprobación de
        # seguridad lo rechace con un mensaje claro.
        output.append(f"\\{command}")

    return "".join(output)


def _normalise(text: str) -> str:
    """Normaliza signos y notación Unicode habitual en apuntes."""

    replacements = {
        "−": "-",
        "–": "-",
        "—": "-",
        "·": "*",
        "×": "*",
        "²": "**2",
        "³": "**3",
        "√": "sqrt",
        "∞": "oo",
        "π": "pi",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text.strip()


def _contains_higher_order(text: str) -> bool:
    compact = _compact(text)
    return any(pattern.search(compact) for pattern in _HIGHER_ORDER_PATTERNS)


def _security_check(text: str) -> str | None:
    if _FORBIDDEN_CHARACTERS.search(text):
        return (
            "La ecuación contiene caracteres no permitidos. "
            "Usa sólo números, variables, operadores y funciones matemáticas."
        )
    if _UNDERSCORE_NAMES.search(text):
        return (
            "Los identificadores con guion bajo no están permitidos. "
            "Escribe las funciones matemáticas habituales (sin, cos, exp...)."
        )
    if _ATTRIBUTE_ACCESS.search(text):
        return (
            "El acceso a atributos no está permitido en una ecuación. "
            "Usa notación matemática, por ejemplo 2*x en lugar de objetos."
        )
    if _DANGEROUS_WORDS.search(text):
        return (
            "La ecuación contiene una palabra reservada no permitida. "
            "Sólo se admiten expresiones matemáticas."
        )
    return None


def _safe_parse(text: str) -> sp.Expr:
    """Convierte texto a expresión SymPy sin exponer builtins."""

    return parse_expr(
        text,
        local_dict=_ALLOWED_NAMES,
        global_dict=_GLOBAL_DICT,
        transformations=_TRANSFORMATIONS,
        evaluate=True,
    )


def _unknown_symbols(expr: sp.Expr, allowed: set[sp.Symbol]) -> set[str]:
    return {
        symbol.name
        for symbol in expr.free_symbols
        if symbol not in allowed and getattr(symbol, "is_Symbol", False)
    }


def _linear_in(expr: sp.Expr, symbol: sp.Symbol) -> tuple[sp.Expr, sp.Expr] | None:
    """Devuelve ``(A, B)`` si ``expr = A*symbol + B`` y A no contiene symbol."""

    coefficient = sp.simplify(sp.diff(expr, symbol))
    remainder = sp.simplify(expr - coefficient * symbol)
    if coefficient.has(symbol) or remainder.has(symbol):
        return None
    if coefficient == 0:
        return None
    return coefficient, remainder


def _latex_explicit(rhs: sp.Expr) -> str:
    return r"\frac{dy}{dx} = " + sp.latex(rhs)


def _latex_implicit(expr: sp.Expr) -> str:
    return sp.latex(expr) + " = 0"


def parse_ode(text: str) -> ParsedODE:
    """Parsea una EDO de primer orden y devuelve su representación interna.

    El resultado contiene ``rhs`` para formas explícitas, ``M``/``N`` para la
    forma diferencial o ``F`` para formas implícitas.  Si hay un error, sólo
    ``error`` está poblado y el resto queda en ``None``.
    """

    if not isinstance(text, str):
        return _error("La ecuación debe ser una cadena de texto.")

    raw = _normalise(text)
    if not raw:
        return _error("La ecuación está vacía. Ingresa una EDO de primer orden.")

    try:
        raw = _latex_to_plain(raw)
    except ValueError as exc:
        return _error(str(exc))
    raw, dominio = _separar_dominio(raw)
    if not raw.strip():
        return _error("La ecuación está vacía. Ingresa una EDO de primer orden.")

    if _contains_higher_order(raw):
        return _error(
            "Solo se admiten EDOs de primer orden; se detectó una derivada "
            "de orden superior."
        )

    if "=" not in raw:
        return _error(
            "Falta el signo '='. Usa una forma como dy/dx = f(x, y), "
            "y' = f(x, y) o M(x,y) dx + N(x,y) dy = 0."
        )
    if raw.count("=") != 1:
        return _error("La ecuación debe contener exactamente un signo '='.")

    # Normalización de derivadas antes del control de seguridad: la prima de
    # y' se transforma en el símbolo interno Dy.
    prepared = _DY_DX.sub("Dy", raw)
    prepared = _PRIME.sub("Dy", prepared)

    # Los diferenciales sueltos sólo se interpretan si no hay Dy explícito.
    has_derivative = "Dy" in prepared
    if not has_derivative:
        prepared = _STANDALONE_DIFF.sub(
            lambda match: "Dx" if match.group(1) == "x" else "Dyy",
            prepared,
        )

    security_error = _security_check(prepared)
    if security_error is not None:
        return _error(security_error)

    lhs_text, rhs_text = (part.strip() for part in prepared.split("=", 1))
    if not lhs_text:
        return _error("El lado izquierdo de la ecuación está vacío.")
    if not rhs_text:
        return _error("El lado derecho de la ecuación está vacío.")

    try:
        lhs = _safe_parse(lhs_text)
        rhs = _safe_parse(rhs_text)
    except Exception as exc:  # parse_expr lanza tipos variados
        return _error(f"Sintaxis inválida en la ecuación: {exc}")

    if not isinstance(lhs, sp.Expr) or not isinstance(rhs, sp.Expr):
        return _error("La ecuación no es una expresión matemática válida.")

    expression = sp.simplify(lhs - rhs)

    allowed = {X, Y, DY, DX, DY_DIFF}
    unknown = _unknown_symbols(expression, allowed)
    if unknown:
        names = ", ".join(sorted(unknown))
        return _error(f"Símbolos o funciones no permitidos: {names}.")

    if expression.has(sp.Derivative):
        return _error("La ecuación no debe contener derivadas simbólicas.")

    # --- Forma diferencial M dx + N dy = 0 --------------------------------
    if DX in expression.free_symbols or DY_DIFF in expression.free_symbols:
        m_expr = sp.simplify(sp.diff(expression, DX)) if DX in expression.free_symbols else sp.Integer(0)
        n_expr = (
            sp.simplify(sp.diff(expression, DY_DIFF))
            if DY_DIFF in expression.free_symbols
            else sp.Integer(0)
        )
        remainder = sp.simplify(expression - m_expr * DX - n_expr * DY_DIFF)
        if remainder != 0:
            return _error(
                "La forma diferencial debe ser lineal en dx y dy: "
                "M(x, y) dx + N(x, y) dy = 0."
            )
        if m_expr == 0 and n_expr == 0:
            return _error("La forma diferencial no contiene términos en dx ni dy.")
        if n_expr == 0:
            return _error(
                "La forma diferencial debe contener dy para poder despejar y'. "
                "Revisa la ecuación."
            )
        rhs_explicit = sp.simplify(-m_expr / n_expr)
        standard = f"{sp.sstr(m_expr)} dx + {sp.sstr(n_expr)} dy = 0"
        return ParsedODE(
            original=text,
            kind="differential",
            rhs=rhs_explicit,
            F=expression,
            M=m_expr,
            N=n_expr,
            latex_str=(
                sp.latex(m_expr)
                + r"\,dx + "
                + sp.latex(n_expr)
                + r"\,dy = 0"
            ),
            standard_form=standard,
            dominio=dominio,
        )

    # --- Formas con derivada ---------------------------------------------
    if DY in expression.free_symbols:
        linear = _linear_in(expression, DY)
        if linear is not None:
            coefficient, remainder = linear
            rhs_explicit = sp.simplify(-remainder / coefficient)
            return ParsedODE(
                original=text,
                kind="explicit",
                rhs=rhs_explicit,
                F=expression,
                latex_str=_latex_explicit(rhs_explicit),
                standard_form=f"dy/dx = {sp.sstr(rhs_explicit)}",
                dominio=dominio,
            )
        return ParsedODE(
            original=text,
            kind="implicit",
            F=expression,
            latex_str=_latex_implicit(expression),
            standard_form=f"{sp.sstr(expression)} = 0",
            dominio=dominio,
        )

    # Sin derivada ni diferenciales: no es una EDO.
    if _DERIVATIVE_LHS.match(_compact(text)):
        return _error(
            "El lado derecho de la ecuación está vacío o no es una expresión válida."
        )
    return _error(
        "No se detectó una derivada. Usa y', dy/dx o la forma "
        "M(x,y) dx + N(x,y) dy = 0."
    )


__all__ = ["parse_ode", "latex_to_plain"]

latex_to_plain = _latex_to_plain
