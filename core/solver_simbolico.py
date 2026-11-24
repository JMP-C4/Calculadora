"""Resolución simbólica y aplicación de condiciones iniciales.

Envuelve el motor :mod:`odecalc` para ofrecer una API estable a EDO-Lab.  El
cálculo simbólico se puede ejecutar con un tiempo límite real; si se agota, la
capa híbrida continúa por la vía numérica.
"""

from __future__ import annotations

from typing import Any

import sympy as sp

from odecalc.api import solve as _resolver_motor
from odecalc.models import SolveResult
from odecalc.timeout import TimeoutError as TimeoutMotor

from core.parser import parsear
from core.tipos import (
    EntradaInvalida,
    ResultadoSolucion,
    SolucionNoDisponible,
    TiempoAgotado,
)


def resolver_motor(
    texto: str,
    x0: float | None = None,
    y0: float | None = None,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
    x_min: float = -5.0,
    x_max: float = 5.0,
    calcular_numerico: bool = False,
) -> SolveResult:
    """Ejecuta el motor y devuelve su contrato completo.

    Se valida primero la entrada para poder ofrecer mensajes propios y se
    traduce el tiempo agotado a :class:`core.tipos.TiempoAgotado`.
    """

    parsear(texto)  # validación temprana con mensajes de EDO-Lab
    try:
        return _resolver_motor(
            texto,
            x0=x0,
            y0=y0,
            x_min=x_min,
            x_max=x_max,
            method=metodo,
            compute_numeric=calcular_numerico,
            timeout=timeout,
        )
    except TimeoutMotor as exc:
        raise TiempoAgotado(str(exc)) from exc
    except EntradaInvalida:
        raise
    except Exception as exc:
        raise SolucionNoDisponible(
            "El motor simbólico no pudo completar el cálculo: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def resolver_general(
    texto: str,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
) -> SolveResult:
    """Solución general sin condición inicial."""

    return resolver_motor(texto, timeout=timeout, metodo=metodo)


def resolver_pvi(
    texto: str,
    x0: float,
    y0: float,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
    x_min: float = -5.0,
    x_max: float = 5.0,
) -> SolveResult:
    """Solución particular de un problema de valor inicial."""

    return resolver_motor(
        texto,
        x0=x0,
        y0=y0,
        timeout=timeout,
        metodo=metodo,
        x_min=x_min,
        x_max=x_max,
    )


def resolver_simbolico(
    texto: str,
    x0: float | None = None,
    y0: float | None = None,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
) -> ResultadoSolucion:
    """Resuelve por la vía simbólica y devuelve el contrato de EDO-Lab."""

    motor = resolver_motor(texto, x0=x0, y0=y0, timeout=timeout, metodo=metodo)
    if motor.error is not None:
        raise SolucionNoDisponible(motor.error)
    if motor.general is None:
        raise SolucionNoDisponible(
            "No se encontró una solución simbólica verificable para esta EDO."
        )
    from core.resultado import convertir_motor

    return convertir_motor(motor, texto, camino="analitica", x0=x0, y0=y0)


def constante_pvi(motor: SolveResult) -> Any | None:
    """Devuelve la constante calculada al aplicar el PVI, si es explícita."""

    particular = motor.particular
    if particular is None:
        return None
    if particular.is_implicit:
        return particular.value
    constantes = [
        simbolo
        for simbolo in particular.expr.free_symbols
        if simbolo not in {sp.Symbol("x", real=True), sp.Symbol("y", real=True)}
    ]
    return constantes[0] if constantes else None


__all__ = [
    "resolver_motor",
    "resolver_general",
    "resolver_pvi",
    "resolver_simbolico",
    "constante_pvi",
]
