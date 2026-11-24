"""Existencia, unicidad, singularidades y explosión en tiempo finito.

Aplica el teorema de Picard-Lindelöf de forma didáctica: comprueba que ``f`` y
``∂f/∂y`` sean continuas cerca del punto inicial, busca singularidades y
detecta los casos clásicos de no unicidad (por ejemplo ``y' = y^(1/3)`` en
``y=0``) y de explosión (por ejemplo ``y' = y²``).
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp

from odecalc.symbols import X, Y

from core.tipos import InfoExistencia


def _a_float(valor: object) -> float | None:
    try:
        numero = complex(sp.N(valor))  # type: ignore[arg-type]
    except Exception:
        return None
    if not (math.isfinite(numero.real) and math.isfinite(numero.imag)):
        return None
    if abs(numero.imag) > 1e-9:
        return None
    return float(numero.real)


def _evaluar(expr: sp.Expr, x: float, y: float) -> float | None:
    return _a_float(expr.subs({X: x, Y: y}))


def _continua_en_entorno(
    expr: sp.Expr,
    x0: float | None,
    y0: float | None,
    *,
    radio: float = 1.0,
) -> bool | None:
    if x0 is None or y0 is None:
        return None
    puntos = [0.0, 0.25, 0.5, 1.0]
    for factor in puntos:
        for signo_x, signo_y in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
            x = x0 + signo_x * radio * factor
            y = y0 + signo_y * radio * factor
            if _evaluar(expr, x, y) is None:
                return False
    return True


def _puntos_singulares(rhs: sp.Expr) -> tuple[list[str], list[str]]:
    """Devuelve singularidades de f y notas sobre restricciones de dominio."""

    puntos: list[str] = []
    notas: list[str] = []
    try:
        numerador, denominador = sp.fraction(sp.together(rhs))
    except Exception:
        return puntos, notas
    if denominador not in (0, 1):
        for variable, nombre in ((X, "x"), (Y, "y")):
            try:
                soluciones = sp.solve(sp.Eq(denominador, 0), variable)
            except Exception:
                soluciones = []
            for solucion in soluciones:
                valor = _a_float(solucion)
                if valor is not None and not any(
                    f"{nombre} = {valor:g}" == item for item in puntos
                ):
                    puntos.append(f"{nombre} = {valor:g}")
        if not puntos:
            notas.append(
                "f(x,y) contiene denominadores; puede haber singularidades "
                "donde éstos se anulan."
            )
    for atomo in sp.preorder_traversal(rhs):
        if isinstance(atomo, sp.log):
            notas.append(
                "El logaritmo restringe el dominio al argumento estrictamente "
                "positivo."
            )
            break
        if isinstance(atomo, sp.Pow) and atomo.exp == sp.Rational(1, 2):
            notas.append(
                "La raíz cuadrada restringe el dominio al radicando no negativo."
            )
            break
    return puntos, notas


def _tiene_potencia_fraccionaria(rhs: sp.Expr, y0: float) -> bool:
    """Detecta ``(y-y0)^α`` con 0 < α < 1, fuente típica de no unicidad."""

    for atomo in sp.preorder_traversal(rhs):
        if not isinstance(atomo, sp.Pow):
            continue
        base, exponente = atomo.args
        if exponente.is_number:
            valor = float(sp.N(exponente))
            if 0.0 < valor < 1.0:
                try:
                    if sp.simplify(base.subs(Y, y0)) == 0:
                        return True
                except Exception:
                    continue
    return False


def estimar_explosion(
    rhs: sp.Expr,
    x0: float,
    y0: float,
) -> tuple[bool, float | None, str | None]:
    """Estima el tiempo de explosión para una EDO autónoma.

    Para ``y' = f(y)`` la solución explota cuando diverge la integral
    ``∫ dy/f(y)``.  Si la integral converge, el tiempo se suma a ``x0``.
    """

    try:
        f_y = sp.simplify(rhs.subs(X, x0))
    except Exception:
        return False, None, None
    if f_y.has(X):
        return False, None, None

    valor = _evaluar(f_y, x0, y0)
    if valor is None or abs(valor) < 1e-14:
        return False, None, None

    # La solución escapa hacia +∞ si y0 > 0 y hacia -∞ si y0 < 0.  El signo
    # de la integral decide si el escape ocurre hacia delante o hacia atrás.
    limite = sp.oo if y0 > 0 else -sp.oo

    # Si f(y) se anula entre y0 y el límite, la integral impropia diverge y
    # la solución se acerca asintóticamente al equilibrio en lugar de explotar.
    try:
        raices = sp.solve(sp.Eq(f_y, 0), Y)
    except Exception:
        raices = []
    for raiz in raices:
        raiz_valor = _a_float(raiz)
        if raiz_valor is None:
            continue
        if min(y0, float(limite)) < raiz_valor < max(y0, float(limite)):
            return False, None, None

    try:
        primitiva = sp.integrate(1 / f_y, Y)
        valor_limite = sp.limit(primitiva, Y, limite)
        integral = sp.simplify(valor_limite - primitiva.subs(Y, y0))
    except Exception:
        return False, None, None
    if integral.has(sp.Integral, sp.oo, -sp.oo, sp.zoo, sp.nan, sp.AccumBounds):
        return False, None, None
    tiempo_integral = _a_float(integral)
    if tiempo_integral is None or not math.isfinite(tiempo_integral):
        return False, None, None
    if abs(tiempo_integral) < 1e-12:
        return False, None, None
    tiempo = x0 + tiempo_integral
    if not math.isfinite(tiempo):
        return False, None, None
    direccion = "hacia adelante" if tiempo > x0 else "hacia atrás"
    return True, float(tiempo), direccion


def analizar_existencia(
    rhs: sp.Expr,
    x0: float | None = None,
    y0: float | None = None,
    *,
    x_min: float | None = None,
    x_max: float | None = None,
) -> InfoExistencia:
    """Analiza existencia, unicidad, singularidades y explosión."""

    notas: list[str] = []
    puntos, notas_dominio = _puntos_singulares(rhs)
    notas.extend(notas_dominio)

    f_continua = _continua_en_entorno(rhs, x0, y0)
    if x0 is not None and y0 is not None:
        if _evaluar(rhs, x0, y0) is None:
            f_continua = False
            notas.append("f(x,y) no es finita en el punto inicial.")
        else:
            notas.append("f(x,y) es finita en el punto inicial.")

    try:
        dfdy = sp.simplify(sp.diff(rhs, Y))
    except Exception:
        dfdy = sp.Integer(0)
    dfdy_continua = _continua_en_entorno(dfdy, x0, y0)

    lipschitz: bool | None = None
    no_unicidad = False
    motivo: str | None = None
    if x0 is not None and y0 is not None:
        valor_dfdy = _evaluar(dfdy, x0, y0)
        if valor_dfdy is None:
            lipschitz = False
            no_unicidad = True
            motivo = (
                "∂f/∂y no es finita en el punto inicial; no se cumple la "
                "condición de Lipschitz."
            )
        else:
            lipschitz = True
            if _tiene_potencia_fraccionaria(rhs, y0):
                lipschitz = False
                no_unicidad = True
                motivo = (
                    "f contiene una potencia fraccionaria de (y-y₀) con "
                    "exponente entre 0 y 1; la derivada ∂f/∂y deja de ser "
                    "acotada cerca del punto inicial."
                )
    elif dfdy_continua is not None:
        lipschitz = dfdy_continua

    if no_unicidad:
        notas.append(motivo or "Posible pérdida de unicidad.")
    elif lipschitz:
        notas.append(
            "Se cumplen las hipótesis de Picard-Lindelöf en un entorno del "
            "punto inicial: existe una solución local única."
        )

    explota = False
    tiempo: float | None = None
    direccion: str | None = None
    if x0 is not None and y0 is not None:
        explota, tiempo, direccion = estimar_explosion(rhs, float(x0), float(y0))
    if explota:
        notas.append(
            "La solución no puede extenderse más allá de "
            f"x ≈ {tiempo:.6g} ({direccion}); la norma tiende a infinito."
        )

    if x_min is not None and x_max is not None and tiempo is not None:
        if x_min <= tiempo <= x_max:
            notas.append(
                "El intervalo solicitado contiene el punto de explosión; "
                "la integración numérica puede detenerse antes."
            )

    return InfoExistencia(
        f_continua=f_continua,
        dfdy_continua=dfdy_continua,
        lipschitz=lipschitz,
        puntos_singularidad=puntos,
        no_unicidad=no_unicidad,
        motivo_no_unicidad=motivo,
        explota=explota,
        tiempo_explosion=tiempo,
        direccion_explosion=direccion,
        notas=notas,
    )


def verificar_picard_lindelof(
    rhs: sp.Expr,
    x0: float,
    y0: float,
) -> bool:
    """Atajo booleano: ¿se cumplen las hipótesis de Picard-Lindelöf?"""

    info = analizar_existencia(rhs, x0, y0)
    return bool(info.lipschitz and not info.no_unicidad)


__all__ = [
    "analizar_existencia",
    "estimar_explosion",
    "verificar_picard_lindelof",
]
