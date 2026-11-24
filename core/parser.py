"""Entrada flexible y segura para EDO-Lab.

Reutiliza el parser endurecido de :mod:`odecalc` (lista blanca, sin ``eval``
inseguro, multiplicación implícita y LaTeX) y añade un intérprete controlado
para familias parametrizadas del tipo ``y' = mu*y - y**2``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from odecalc.parsing import parse_ode
from odecalc.parsing import parser as _motor_parser
from odecalc.symbols import DY, X, Y

from core.tipos import EntradaInvalida, Ecuacion

_PARAMETRO_POR_DEFECTO = "mu"
_IDENTIFICADOR = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
_NOMBRES = re.compile(r"\b[A-Za-z][A-Za-z0-9]*\b")
_LLAMADA_FUNCION = re.compile(r"\b([A-Za-z][A-Za-z0-9]*)\s*\(")
_CARACTERES_PERMITIDOS = re.compile(r"^[0-9A-Za-z_+\-*/^().,=\s]+$")
_NOMBRES_MOTOR = frozenset(_motor_parser._ALLOWED_NAMES)


@dataclass
class EcuacionParametrizada:
    """EDO explícita que depende además de un parámetro real."""

    texto: str
    latex: str
    rhs: sp.Expr
    parametro: sp.Symbol
    parametro_nombre: str
    parsed: object | None = None


def _sugerencia(texto: str) -> str:
    """Propone una corrección concreta para los errores más habituales."""

    sugerencias: list[str] = []
    if re.search(r"\d\s*[A-Za-z(]", texto) and "*" not in texto:
        sugerencias.append("Parece que falta un `*`: ¿quisiste escribir `2*x`?")
    if "'" in texto and "dy/dx" not in texto.lower() and "y'" not in texto:
        sugerencias.append("Para la derivada usa `y'` o `dy/dx`.")
    if texto.count("(") != texto.count(")"):
        sugerencias.append("Revisa los paréntesis: no están balanceados.")
    if not sugerencias:
        sugerencias.append(
            "Usa una forma como `y' = x*y + sin(x)` o `dy/dx = y*(1-y)`."
        )
    return " ".join(sugerencias)


def _despejar_rhs(parsed, texto: str) -> sp.Expr:
    """Obtiene ``f(x, y)`` de una forma implícita cuando sea posible."""

    if parsed.rhs is not None:
        return sp.simplify(parsed.rhs)
    if parsed.F is None:
        raise EntradaInvalida(
            "No se pudo interpretar la ecuación. " + _sugerencia(texto)
        )
    try:
        ramas = sp.solve(sp.Eq(parsed.F, 0), DY)
    except Exception:
        ramas = []
    validas = [
        sp.simplify(rama)
        for rama in ramas
        if isinstance(rama, sp.Expr) and not rama.has(DY)
    ]
    if not validas:
        raise EntradaInvalida(
            "La ecuación es implícita y no se pudo despejar y'. "
            "Prueba a escribirla como `y' = f(x, y)`."
        )
    return validas[0]


def parsear(texto: str) -> Ecuacion:
    """Convierte el texto del usuario en una :class:`core.tipos.Ecuacion`.

    Acepta ``y' = f(x,y)``, ``dy/dx = f(x,y)``, formas diferenciales, LaTeX
    habitual, ``^`` como potencia y multiplicación implícita.  Nunca evalúa
    código arbitrario.
    """

    if not isinstance(texto, str) or not texto.strip():
        raise EntradaInvalida("Escribe una ecuación diferencial para comenzar.")

    parsed = parse_ode(texto.strip())
    if parsed.error is not None:
        raise EntradaInvalida(f"{parsed.error} {_sugerencia(texto)}".strip())

    rhs = _despejar_rhs(parsed, texto)
    if rhs.free_symbols - {X, Y}:
        nombres = ", ".join(sorted(str(s) for s in rhs.free_symbols - {X, Y}))
        raise EntradaInvalida(
            f"Sólo se admiten las variables x e y; aparecen: {nombres}."
        )

    try:
        coeficiente = sp.simplify(sp.diff(rhs, Y))
        es_lineal = not coeficiente.has(Y)
    except Exception:
        es_lineal = False

    return Ecuacion(
        texto=texto.strip(),
        latex=parsed.latex_str or sp.latex(rhs),
        rhs=rhs,
        parsed=parsed,
        es_autonoma=not rhs.has(X),
        es_lineal=es_lineal,
    )


def parsear_con_parametros(texto: str) -> Ecuacion:
    """Interpreta una EDO explícita con parámetros simbólicos reales.

    Se usa en los análisis que *necesitan* parámetros (Monte Carlo, Sobol y
    barridos), no para resolver la ecuación: el orquestador híbrido sigue
    exigiendo que la EDO dependa sólo de ``x`` e ``y``.
    """

    if not isinstance(texto, str) or not texto.strip():
        raise EntradaInvalida("Escribe una ecuación diferencial para comenzar.")
    preparado = _normalizar_derivadas(texto.strip())
    if not _CARACTERES_PERMITIDOS.match(preparado):
        raise EntradaInvalida(
            "La ecuación contiene caracteres no permitidos. Usa sólo números, "
            "letras, paréntesis y los operadores + - * / ^."
        )
    seguridad = _motor_parser._security_check(preparado)
    if seguridad is not None:
        raise EntradaInvalida(seguridad)
    if "__" in preparado or "[" in preparado or "]" in preparado:
        raise EntradaInvalida("La entrada contiene construcciones no permitidas.")
    if preparado.count("=") != 1:
        raise EntradaInvalida(
            "Escribe exactamente una igualdad, por ejemplo `y' = r*y`."
        )

    desconocidas = [
        nombre
        for nombre in _LLAMADA_FUNCION.findall(preparado)
        if nombre not in _NOMBRES_MOTOR
    ]
    if desconocidas:
        raise EntradaInvalida(
            "Funciones no permitidas: " + ", ".join(sorted(set(desconocidas))) + "."
        )

    parametros = sorted(
        nombre
        for nombre in set(_NOMBRES.findall(preparado))
        if nombre not in _NOMBRES_MOTOR
    )
    local_dict: dict[str, object] = dict(_motor_parser._ALLOWED_NAMES)
    simbolos = {nombre: sp.Symbol(nombre, real=True) for nombre in parametros}
    local_dict.update(simbolos)

    izquierda, derecha = (parte.strip() for parte in preparado.split("=", 1))
    if not izquierda or not derecha:
        raise EntradaInvalida("Los dos lados de la ecuación deben estar completos.")
    try:
        lhs = parse_expr(
            izquierda,
            local_dict=local_dict,
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
        rhs = parse_expr(
            derecha,
            local_dict=local_dict,
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
    except Exception as exc:
        raise EntradaInvalida(
            f"No se pudo interpretar la ecuación: {exc}. " + _sugerencia(texto)
        ) from exc
    if not isinstance(lhs, sp.Expr) or not isinstance(rhs, sp.Expr):
        raise EntradaInvalida("La ecuación no es una expresión matemática válida.")

    expresion = sp.simplify(lhs - rhs)
    permitidos = {X, Y, DY, *simbolos.values()}
    if expresion.free_symbols - permitidos:
        nombres = ", ".join(
            sorted(str(simbolo) for simbolo in expresion.free_symbols - permitidos)
        )
        raise EntradaInvalida(f"Símbolos no permitidos en la ecuación: {nombres}.")

    if expresion.has(DY):
        try:
            ramas = sp.solve(sp.Eq(expresion, 0), DY)
        except Exception:
            ramas = []
        rhs_expr = next(
            (
                sp.simplify(rama)
                for rama in ramas
                if isinstance(rama, sp.Expr) and not rama.has(DY)
            ),
            None,
        )
        if rhs_expr is None:
            raise EntradaInvalida(
                "No se pudo despejar y'. Escribe la ecuación como `y' = f(x, y)`."
            )
    elif lhs == DY:
        rhs_expr = sp.simplify(rhs)
    else:
        raise EntradaInvalida(
            "No se detectó y'. Usa `y' = f(x, y)` o `dy/dx = f(x, y)`."
        )

    try:
        lineal = not sp.diff(rhs_expr, Y).has(Y)
    except Exception:
        lineal = False
    return Ecuacion(
        texto=texto.strip(),
        latex=sp.latex(sp.Eq(DY, rhs_expr)),
        rhs=rhs_expr,
        parsed=None,
        es_autonoma=not rhs_expr.has(X),
        es_lineal=lineal,
        parametros=tuple(parametros),
    )


def _normalizar_derivadas(texto: str) -> str:
    """Convierte ``y'`` y ``dy/dx`` en el símbolo seguro ``Dy``."""

    normalizado = re.sub(r"d\s*y\s*/\s*d\s*x", "Dy", texto, flags=re.IGNORECASE)
    normalizado = normalizado.replace("y′", "Dy").replace("y'", "Dy")
    return normalizado


def parsear_parametrizada(
    texto: str,
    parametro: str = _PARAMETRO_POR_DEFECTO,
) -> EcuacionParametrizada:
    """Interpreta una EDO explícita con un parámetro real (por ejemplo ``mu``).

    Sólo se permiten los símbolos ``x``, ``y``, ``y'`` y el parámetro.  El
    resultado se usa en diagramas de bifurcación y barridos paramétricos.
    """

    if not isinstance(texto, str) or not texto.strip():
        raise EntradaInvalida("Escribe una familia de ecuaciones para analizar.")
    if not _IDENTIFICADOR.match(parametro):
        raise EntradaInvalida(
            "El nombre del parámetro debe ser un identificador simple, por "
            "ejemplo `mu`."
        )
    if parametro in {"x", "y", "Dy"}:
        raise EntradaInvalida("El parámetro no puede llamarse x, y ni Dy.")

    preparado = _normalizar_derivadas(texto.strip())
    if not _CARACTERES_PERMITIDOS.match(preparado):
        raise EntradaInvalida(
            "La familia contiene caracteres no permitidos. Usa sólo números, "
            "letras, paréntesis y los operadores + - * / ^."
        )
    if "__" in preparado or "[" in preparado or "]" in preparado:
        raise EntradaInvalida("La entrada contiene construcciones no permitidas.")
    if preparado.count("=") != 1:
        raise EntradaInvalida(
            "Escribe exactamente una igualdad, por ejemplo `y' = mu*y - y**2`."
        )

    parametro_simbolo = sp.Symbol(parametro, real=True)
    local_dict: dict[str, object] = dict(_motor_parser._ALLOWED_NAMES)
    local_dict.update(
        {
            "Dy": DY,
            "x": X,
            "y": Y,
            str(parametro): parametro_simbolo,
        }
    )
    izquierda, derecha = (parte.strip() for parte in preparado.split("=", 1))
    if not izquierda or not derecha:
        raise EntradaInvalida("Los dos lados de la ecuación deben estar completos.")

    try:
        lhs = parse_expr(
            izquierda,
            local_dict=local_dict,
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
        rhs = parse_expr(
            derecha,
            local_dict=local_dict,
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
    except Exception as exc:
        raise EntradaInvalida(
            f"No se pudo interpretar la familia: {exc}. " + _sugerencia(texto)
        ) from exc

    if not isinstance(lhs, sp.Expr) or not isinstance(rhs, sp.Expr):
        raise EntradaInvalida("La familia no es una expresión matemática válida.")

    permitidos = {X, Y, DY, parametro_simbolo}
    desconocidos = {
        simbolo
        for simbolo in (lhs.free_symbols | rhs.free_symbols)
        if simbolo not in permitidos
    }
    if desconocidos:
        nombres = ", ".join(sorted(str(s) for s in desconocidos))
        raise EntradaInvalida(
            f"Símbolos no permitidos en la familia: {nombres}. "
            f"Sólo se admiten x, y y {parametro}."
        )

    expresion = sp.simplify(lhs - rhs)
    if expresion.has(DY):
        try:
            soluciones = sp.solve(sp.Eq(expresion, 0), DY)
        except Exception:
            soluciones = []
        rhs_expr = next(
            (
                sp.simplify(sol)
                for sol in soluciones
                if isinstance(sol, sp.Expr) and not sol.has(DY)
            ),
            None,
        )
        if rhs_expr is None:
            raise EntradaInvalida(
                "No se pudo despejar y' en la familia. Escríbela como "
                "`y' = f(y, mu)`."
            )
    elif lhs == DY:
        rhs_expr = sp.simplify(rhs)
    else:
        raise EntradaInvalida(
            "No se detectó y' en el lado izquierdo. Usa `y' = f(y, mu)`."
        )

    return EcuacionParametrizada(
        texto=texto.strip(),
        latex=sp.latex(sp.Eq(DY, rhs_expr)),
        rhs=rhs_expr,
        parametro=parametro_simbolo,
        parametro_nombre=parametro,
    )


def rhs_de_texto(texto: str) -> sp.Expr:
    """Atajo que devuelve sólo ``f(x, y)``."""

    return parsear(texto).rhs


__all__ = [
    "EcuacionParametrizada",
    "parsear",
    "parsear_con_parametros",
    "parsear_parametrizada",
    "rhs_de_texto",
]
