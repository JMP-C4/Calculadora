"""Certificados de verificación para soluciones simbólicas y numéricas.

Toda solución que muestra EDO-Lab pasa por aquí.  El certificado indica si la
comprobación fue simbólica (residuo idénticamente nulo), numérica (residuo
evaluado en muchos puntos) o si no pudo verificarse.
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp

from odecalc.models import Solution as SolucionMotor
from odecalc.models import SolveResult as ResultadoMotor
from odecalc.symbols import X, Y
from odecalc.verify import verify_solution
from odecalc.verify.verifier import simplify_residual

from core.tipos import (
    Certificado,
    EstadoVerificacion,
    ResultadoNumerico,
    SolucionNoDisponible,
)


def _evaluar_residuo(residual: sp.Expr, *, semilla: int = 42) -> float | None:
    """Máximo absoluto del residuo en una muestra determinista."""

    if residual is None:
        return None
    try:
        simplificado = simplify_residual(residual)
        if simplificado == 0:
            return 0.0
    except Exception:
        simplificado = residual
    if simplificado.has(sp.Integral):
        return None
    simbolos = simplificado.free_symbols
    if simbolos - {X, Y}:
        return None
    try:
        funcion = sp.lambdify((X, Y), simplificado, modules=["numpy"])
    except Exception:
        return None
    generador = np.random.default_rng(semilla)
    xs = generador.uniform(-3.0, 3.0, 200)
    ys = generador.uniform(-3.0, 3.0, 200)
    with np.errstate(all="ignore"):
        valores = np.asarray(funcion(xs, ys), dtype=float)
    finitos = valores[np.isfinite(valores)]
    if finitos.size == 0:
        return None
    return float(np.max(np.abs(finitos)))


def certificar_motor(resultado: ResultadoMotor) -> Certificado:
    """Construye el certificado de un :class:`odecalc.models.SolveResult`."""

    verificacion = resultado.particular_verification or resultado.verification
    dominio = (
        resultado.validity.interval
        or resultado.validity.domain
        or "Dominio no determinado."
    )
    metodo = resultado.chosen_method or "motor"
    notas: list[str] = []

    if verificacion is None:
        if resultado.numeric is not None and resultado.numeric.success:
            return Certificado(
                estado=EstadoVerificacion.NUMERICA,
                residuo_max=resultado.numeric.error_estimate,
                dominio_valido=dominio,
                notas=[
                    "No hubo verificación simbólica; se presenta la integración "
                    "numérica con su estimación de error."
                ],
                metodo=metodo,
            )
        return Certificado(
            estado=EstadoVerificacion.NO_VERIFICADA,
            residuo_max=None,
            dominio_valido=dominio,
            notas=["El motor no devolvió una verificación utilizable."],
            metodo=metodo,
        )

    notas.extend(
        nota
        for nota in (resultado.validity.notes or [])
        if isinstance(nota, str)
    )
    if verificacion.message:
        notas.append(verificacion.message)

    if verificacion.status == "ok":
        residuo = _evaluar_residuo(verificacion.residual)
        if verificacion.numeric_checked:
            estado = EstadoVerificacion.NUMERICA
            notas.append(
                f"Se evaluó el residuo en {verificacion.points_checked} puntos "
                "debido a que la simplificación simbólica no fue concluyente."
            )
            if residuo is None:
                residuo = 0.0
        else:
            estado = EstadoVerificacion.SIMBOLICA
            residuo = 0.0 if residuo is None else residuo
        return Certificado(
            estado=estado,
            residuo_max=residuo,
            dominio_valido=dominio,
            notas=notas,
            metodo=metodo,
        )

    return Certificado(
        estado=EstadoVerificacion.NO_VERIFICADA,
        residuo_max=_evaluar_residuo(verificacion.residual),
        dominio_valido=dominio,
        notas=notas or ["La solución no superó la verificación."],
        metodo=metodo,
    )


def certificar_numerico(
    resultado: ResultadoNumerico,
    rhs: sp.Expr,
) -> Certificado:
    """Certifica una solución numérica mediante su defecto de discretización.

    El residuo se estima con diferencias centrales sobre la malla y no debe
    confundirse con un residuo simbólico exactamente nulo.
    """

    dominio = (
        f"x ∈ [{resultado.x[0]:.6g}, {resultado.x[-1]:.6g}]"
        if resultado.x.size
        else "Intervalo no disponible."
    )
    if not resultado.exito or resultado.x.size < 3:
        return Certificado(
            estado=EstadoVerificacion.NO_VERIFICADA,
            residuo_max=None,
            dominio_valido=dominio,
            notas=[resultado.mensaje or "La integración numérica no fue exitosa."],
            metodo=resultado.metodo,
        )

    try:
        f = sp.lambdify((X, Y), rhs, modules=["numpy"])
        x = np.asarray(resultado.x, dtype=float)
        y = np.asarray(resultado.y, dtype=float)
        derivada = np.gradient(y, x)
        with np.errstate(all="ignore"):
            esperado = np.asarray(f(x, y), dtype=float)
        diferencias = np.abs(derivada - esperado)
        finitas = diferencias[np.isfinite(diferencias)]
        defecto = float(np.max(finitas)) if finitas.size else None
    except Exception:
        defecto = None

    notas = [
        "Certificado numérico: el residuo es el defecto de la solución discreta "
        "estimado con diferencias centrales.",
        resultado.mensaje,
    ]
    if resultado.rigido:
        notas.append("El integrador detectó rigidez y usó un método implícito.")
    if resultado.explosion:
        notas.append("La integración se detuvo por posible explosión o valores no finitos.")
    estado = (
        EstadoVerificacion.NUMERICA
        if defecto is not None and math.isfinite(defecto)
        else EstadoVerificacion.NO_VERIFICADA
    )
    return Certificado(
        estado=estado,
        residuo_max=defecto,
        dominio_valido=dominio,
        notas=notas,
        metodo=resultado.metodo,
    )


def verificar_expresion(
    expresion: sp.Expr,
    rhs: sp.Expr,
    *,
    x0: float | None = None,
    y0: float | None = None,
    nombre: str = "candidata",
) -> Certificado:
    """Verifica una expresión ``y(x)`` candidata contra ``y' = rhs``."""

    if not isinstance(expresion, sp.Expr):
        raise SolucionNoDisponible("La candidata no es una expresión SymPy.")
    solucion = SolucionMotor(
        form="explicit",
        expr=expresion,
        latex=sp.latex(sp.Eq(Y, expresion)),
    )
    verificacion = verify_solution(solucion, rhs=rhs, x0=x0)
    notas = [verificacion.message] if verificacion.message else []
    if x0 is not None and y0 is not None:
        try:
            valor = float(sp.N(expresion.subs(X, x0)))
        except Exception:
            valor = float("nan")
        if math.isfinite(valor):
            error = abs(valor - float(y0))
            notas.append(f"Error en la condición inicial: {error:.3e}.")
            if error > 1e-6:
                notas.append("La candidata no satisface la condición inicial.")
        else:
            notas.append("No se pudo evaluar la condición inicial.")

    if verificacion.status == "ok":
        estado = (
            EstadoVerificacion.NUMERICA
            if verificacion.numeric_checked
            else EstadoVerificacion.SIMBOLICA
        )
        return Certificado(
            estado=estado,
            residuo_max=0.0 if not verificacion.numeric_checked else _evaluar_residuo(verificacion.residual),
            dominio_valido="Dominio local de la expresión candidata.",
            notas=notas,
            metodo=nombre,
        )
    return Certificado(
        estado=EstadoVerificacion.NO_VERIFICADA,
        residuo_max=_evaluar_residuo(verificacion.residual),
        dominio_valido="No determinado.",
        notas=notas or ["La candidata no satisface la EDO."],
        metodo=nombre,
    )


__all__ = [
    "certificar_motor",
    "certificar_numerico",
    "verificar_expresion",
]
