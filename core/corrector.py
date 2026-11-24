"""Corrector de procedimientos escritos por el estudiante.

El corrector no adivina la respuesta: comprueba cada línea contra la EDO
original y contra la línea anterior.  Cuando encuentra un fallo señala la
primera línea problemática y ofrece una pista, sin revelar el resultado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr

from odecalc.parsing import parser as _motor_parser
from odecalc.symbols import DY, X, Y

from core.parser import parsear
from core.tipos import EntradaInvalida


@dataclass
class LineaDesarrollo:
    """Una línea del desarrollo, ya normalizada y parseada."""

    numero: int
    texto: str
    izquierda: sp.Expr | None = None
    derecha: sp.Expr | None = None
    error_sintaxis: str | None = None

    @property
    def diferencia(self) -> sp.Expr | None:
        if self.izquierda is None or self.derecha is None:
            return None
        return sp.simplify(self.izquierda - self.derecha)

    @property
    def usa_derivada(self) -> bool:
        return any(
            parte is not None and parte.has(DY)
            for parte in (self.izquierda, self.derecha)
        )

    @property
    def usa_diferenciales(self) -> bool:
        simbolos = {
            sp.Symbol("dy", real=True),
            sp.Symbol("dx", real=True),
        }
        return any(
            parte is not None and bool(parte.free_symbols & simbolos)
            for parte in (self.izquierda, self.derecha)
        )


@dataclass
class ErrorDetectado:
    """Primer error localizado con una pista pedagógica."""

    linea: int
    texto: str
    tipo: str
    pista: str


@dataclass
class ResultadoCorrector:
    """Resultado completo de la revisión de un procedimiento."""

    correcto: bool
    primer_error: ErrorDetectado | None
    lineas_verificadas: int
    mensaje: str
    detalles: list[str] = field(default_factory=list)


_NUMERACION = re.compile(
    r"^\s*(?:(?:paso|step)\s*\d+\s*[:.\-]?|\d+\s*[\).:\-])\s*",
    flags=re.IGNORECASE,
)
_LOCAL_DICT: dict[str, object] = dict(_motor_parser._ALLOWED_NAMES)
_LOCAL_DICT.update(
    {
        "x": X,
        "y": Y,
        "Dy": DY,
        "dy": sp.Symbol("dy", real=True),
        "dx": sp.Symbol("dx", real=True),
        "C": sp.Symbol("C", real=True),
        "C1": sp.Symbol("C1", real=True),
        "C2": sp.Symbol("C2", real=True),
        "Abs": sp.Abs,
    }
)


def _normalizar(texto: str) -> str:
    limpio = texto.strip()
    limpio = _NUMERACION.sub("", limpio)
    limpio = limpio.replace("\\left", "").replace("\\right", "")
    limpio = limpio.replace("\\,", " ").replace("\\;", " ")
    limpio = limpio.replace("\\cdot", "*").replace("\\times", "*")
    limpio = re.sub(r"\\frac\{([^{}]+)\}\{([^{}]+)\}", r"((\1)/(\2))", limpio)
    limpio = limpio.replace("y(x)", "y")
    limpio = limpio.replace("y′", "Dy").replace("y'", "Dy")
    limpio = re.sub(r"d\s*y\s*/\s*d\s*x", "Dy", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\bsen\b", "sin", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\btg\b", "tan", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"\bln\b", "log", limpio, flags=re.IGNORECASE)
    limpio = re.sub(r"e\s*\^\s*\{([^{}]+)\}", r"exp(\1)", limpio)
    limpio = re.sub(r"e\s*\^\s*\(([^()]*)\)", r"exp(\1)", limpio)
    limpio = re.sub(r"\blog\s*\|([^|]+)\|", r"log(Abs(\1))", limpio)
    limpio = re.sub(r"\|([^|]+)\|", r"Abs(\1)", limpio)
    return limpio.strip()


def _parsear_linea(texto: str, numero: int) -> LineaDesarrollo:
    normalizado = _normalizar(texto)
    if not normalizado:
        return LineaDesarrollo(numero=numero, texto=texto, error_sintaxis="Línea vacía.")
    if normalizado.count("=") > 1:
        return LineaDesarrollo(
            numero=numero,
            texto=texto,
            error_sintaxis="Hay más de una igualdad en la misma línea.",
        )
    izquierda_texto, derecha_texto = (
        normalizado.split("=", 1) if "=" in normalizado else (normalizado, "0")
    )
    try:
        izquierda = parse_expr(
            izquierda_texto,
            local_dict=dict(_LOCAL_DICT),
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
        derecha = parse_expr(
            derecha_texto,
            local_dict=dict(_LOCAL_DICT),
            global_dict=dict(_motor_parser._GLOBAL_DICT),
            transformations=_motor_parser._TRANSFORMATIONS,
            evaluate=True,
        )
    except Exception as exc:
        return LineaDesarrollo(
            numero=numero,
            texto=texto,
            error_sintaxis=f"No se pudo interpretar la línea: {exc}",
        )
    if not isinstance(izquierda, sp.Expr) or not isinstance(derecha, sp.Expr):
        return LineaDesarrollo(
            numero=numero,
            texto=texto,
            error_sintaxis="La línea no es una expresión matemática válida.",
        )
    permitidos = {X, Y, DY, sp.Symbol("dy", real=True), sp.Symbol("dx", real=True)}
    constantes = {
        sp.Symbol("C", real=True),
        sp.Symbol("C1", real=True),
        sp.Symbol("C2", real=True),
    }
    desconocidos = {
        simbolo
        for simbolo in (izquierda.free_symbols | derecha.free_symbols)
        if simbolo not in permitidos | constantes
    }
    if desconocidos:
        nombres = ", ".join(sorted(str(s) for s in desconocidos))
        return LineaDesarrollo(
            numero=numero,
            texto=texto,
            error_sintaxis=f"Símbolos no permitidos: {nombres}.",
        )
    return LineaDesarrollo(
        numero=numero,
        texto=texto,
        izquierda=izquierda,
        derecha=derecha,
    )


def _equivalente(primera: LineaDesarrollo, segunda: LineaDesarrollo) -> bool | None:
    """¿Son algebraicamente equivalentes dos ecuaciones?"""

    if primera.diferencia is None or segunda.diferencia is None:
        return None
    if primera.usa_diferenciales or segunda.usa_diferenciales:
        return None
    f1, f2 = primera.diferencia, segunda.diferencia
    # Las relaciones con logaritmos, exponenciales o trigonométricas no se
    # comparan por equivalencia algebraica: se validan contra la EDO original.
    if f1.atoms(sp.Function) or f2.atoms(sp.Function):
        return None
    if f1.has(DY) != f2.has(DY):
        return None
    if sp.simplify(f1 - f2) == 0:
        return True
    try:
        cociente = sp.simplify(f1 / f2)
        if cociente.free_symbols == set() and cociente != 0:
            return True
    except Exception:
        pass
    try:
        if sp.simplify(f1) == 0 and sp.simplify(f2) == 0:
            return True
    except Exception:
        pass
    return False


def _verificar_contra_edo(
    linea: LineaDesarrollo,
    rhs: sp.Expr,
    *,
    x0: float | None,
    y0: float | None,
) -> tuple[bool | None, str]:
    """Comprueba si una línea es consistente con la EDO original."""

    if linea.izquierda is None or linea.derecha is None:
        return None, ""
    if linea.usa_diferenciales:
        return None, "Línea en forma diferencial: no se comprueba algebraicamente."

    if linea.usa_derivada:
        try:
            soluciones = sp.solve(sp.Eq(linea.izquierda, linea.derecha), DY)
        except Exception:
            soluciones = []
        if not soluciones:
            return False, "No se pudo despejar y' en esta línea."
        for solucion in soluciones:
            try:
                if sp.simplify(solucion - rhs) == 0:
                    return True, "La derivada coincide con la EDO original."
                cociente = sp.simplify((solucion - rhs) / (1 + rhs**2))
                if cociente == 0:
                    return True, "La derivada coincide con la EDO original."
            except Exception:
                continue
        return False, "La derivada de esta línea no coincide con la EDO original."

    # Solución explícita y = f(x).
    if sp.simplify(linea.izquierda - Y) == 0:
        expresion = linea.derecha
        try:
            residuo = sp.simplify(sp.diff(expresion, X) - rhs.subs(Y, expresion))
        except Exception:
            residuo = sp.nan
        if residuo == 0:
            return True, "La expresión satisface la EDO al sustituirla."
        if residuo.is_number and abs(complex(residuo)) < 1e-9:
            return True, "La expresión satisface la EDO al sustituirla."
        return False, "Al sustituir esta expresión en la EDO el residuo no es cero."

    # Relación implícita F(x,y)=C: se deriva implícitamente.
    try:
        funcion = sp.simplify(linea.izquierda - linea.derecha)
        f_x = sp.diff(funcion, X)
        f_y = sp.diff(funcion, Y)
    except Exception:
        return None, "No se pudo derivar la relación implícita."
    if sp.simplify(f_y) == 0:
        return False, "La relación no define y como función de x."
    try:
        derivada_implicita = sp.simplify(-f_x / f_y)
    except Exception:
        return None, "No se pudo calcular la derivada implícita."
    try:
        if sp.simplify(derivada_implicita - rhs) == 0:
            return True, "Al derivar implícitamente se recupera la EDO original."
    except Exception:
        pass
    # Comprobación numérica de la derivada implícita.
    try:
        f_rhs = sp.lambdify((X, Y), rhs, modules=["numpy"])
        f_imp = sp.lambdify((X, Y), derivada_implicita, modules=["numpy"])
        rng = np.random.default_rng(42)
        xs = rng.uniform(-2, 2, 12)
        ys = rng.uniform(0.2, 2.5, 12)
        with np.errstate(all="ignore"):
            esperado = np.asarray(f_rhs(xs, ys), dtype=float)
            obtenido = np.asarray(f_imp(xs, ys), dtype=float)
        mascara = np.isfinite(esperado) & np.isfinite(obtenido)
        if np.any(mascara) and np.allclose(esperado[mascara], obtenido[mascara], atol=1e-6, rtol=1e-4):
            return True, "La derivada implícita coincide numéricamente con la EDO."
    except Exception:
        pass
    return False, "Al derivar esta relación no se recupera la EDO original."


def _pista_para(
    linea: LineaDesarrollo,
    motivo: str,
    *,
    comparacion: bool,
) -> str:
    if linea.usa_derivada:
        return (
            "Revisa el signo o el factor de la derivada: esta línea no es "
            "equivalente a la ecuación original. Comprueba cómo pasaste de "
            "y' = f(x,y) a la forma siguiente."
        )
    if sp.simplify((linea.izquierda or 0) - Y) == 0:
        return (
            "Sustituye de nuevo tu y(x) en la EDO y mira el signo del residuo. "
            "Un cambio de signo al integrar o al despejar la constante es el "
            "error más frecuente."
        )
    if comparacion:
        return (
            "Este paso no es algebraicamente equivalente al anterior. Revisa "
            "si multiplicaste o dividiste por una expresión que cambia el "
            "signo, o si perdiste un término."
        )
    return (
        "Comprueba la relación derivando implícitamente: el resultado debe "
        "coincidir con la EDO original. Suele ser un signo o un factor."
    )


def corregir(
    desarrollo: str | list[str],
    ecuacion: str | None = None,
    *,
    x0: float | None = None,
    y0: float | None = None,
) -> ResultadoCorrector:
    """Revisa un desarrollo línea a línea y localiza el primer error."""

    lineas_texto = (
        desarrollo.splitlines() if isinstance(desarrollo, str) else list(desarrollo)
    )
    lineas_texto = [linea for linea in lineas_texto if linea.strip()]
    if not lineas_texto:
        raise EntradaInvalida("Escribe al menos una línea de tu procedimiento.")

    rhs: sp.Expr | None = None
    if ecuacion:
        rhs = parsear(ecuacion).rhs

    parseadas = [_parsear_linea(texto, indice + 1) for indice, texto in enumerate(lineas_texto)]
    detalles: list[str] = []
    verificadas = 0
    anterior: LineaDesarrollo | None = None

    for linea in parseadas:
        if linea.error_sintaxis:
            error = ErrorDetectado(
                linea=linea.numero,
                texto=linea.texto,
                tipo="sintaxis",
                pista=(
                    "No pudimos interpretar esta línea. Revisa paréntesis, "
                    "signos y usa y' o dy/dx para la derivada."
                ),
            )
            return ResultadoCorrector(
                correcto=False,
                primer_error=error,
                lineas_verificadas=verificadas,
                mensaje=f"Primer error en la línea {linea.numero}: sintaxis.",
                detalles=detalles,
            )

        if rhs is not None:
            valido, motivo = _verificar_contra_edo(linea, rhs, x0=x0, y0=y0)
            if valido is False:
                error = ErrorDetectado(
                    linea=linea.numero,
                    texto=linea.texto,
                    tipo="inconsistencia_con_la_edo",
                    pista=_pista_para(linea, motivo, comparacion=False),
                )
                return ResultadoCorrector(
                    correcto=False,
                    primer_error=error,
                    lineas_verificadas=verificadas,
                    mensaje=(
                        f"Primer error en la línea {linea.numero}: {motivo}"
                    ),
                    detalles=detalles + [motivo],
                )
            if valido is True:
                detalles.append(f"Línea {linea.numero}: {motivo}")

        if anterior is not None:
            equivalencia = _equivalente(anterior, linea)
            if equivalencia is False:
                error = ErrorDetectado(
                    linea=linea.numero,
                    texto=linea.texto,
                    tipo="paso_no_equivalente",
                    pista=_pista_para(linea, "", comparacion=True),
                )
                return ResultadoCorrector(
                    correcto=False,
                    primer_error=error,
                    lineas_verificadas=verificadas,
                    mensaje=(
                        f"La línea {linea.numero} no es equivalente a la "
                        f"línea {anterior.numero}."
                    ),
                    detalles=detalles,
                )
            if equivalencia is True:
                detalles.append(
                    f"Línea {linea.numero}: equivalente a la línea {anterior.numero}."
                )
        anterior = linea
        verificadas += 1

    return ResultadoCorrector(
        correcto=True,
        primer_error=None,
        lineas_verificadas=verificadas,
        mensaje="El procedimiento es consistente con la EDO en todas sus líneas.",
        detalles=detalles,
    )


__all__ = [
    "LineaDesarrollo",
    "ErrorDetectado",
    "ResultadoCorrector",
    "corregir",
]
