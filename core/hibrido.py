"""Orquestador híbrido: analítico primero, numérico como respaldo.

Este es el punto de entrada recomendado para la interfaz: nunca deja que un
``dsolve`` lento congele la aplicación y siempre devuelve un resultado con su
certificado o una excepción con un mensaje claro.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp

from odecalc.symbols import X, Y, lambdify_modules

from core.clasificador import clasificar, tipo_principal
from core.existencia import analizar_existencia
from core.parser import parsear
from core.pasos import pasos_numericos
from core.resultado import convertir_motor
from core.solver_numerico import integrar_intervalo
from core.solver_simbolico import resolver_motor
from core.tipos import (
    Certificado,
    Ecuacion,
    EntradaInvalida,
    ResultadoNumerico,
    ResultadoSolucion,
    SolucionNoDisponible,
    TiempoAgotado,
)
from core.verificador import certificar_numerico


def _resultado_numerico(
    texto: str,
    *,
    x0: float,
    y0: float,
    x_min: float,
    x_max: float,
    motivo: str,
    ecuacion: Ecuacion | None = None,
) -> ResultadoSolucion:
    if ecuacion is None:
        ecuacion = parsear(texto)
    numerico = integrar_intervalo(ecuacion.rhs, x0, y0, x_min, x_max)
    if not numerico.exito:
        raise SolucionNoDisponible(
            "No se obtuvo solución simbólica ni numérica. " + numerico.mensaje
        )
    certificado = certificar_numerico(numerico, ecuacion.rhs)
    tipos = clasificar(ecuacion)
    existencia = analizar_existencia(
        ecuacion.rhs, x0, y0, x_min=x_min, x_max=x_max
    )
    advertencias = [motivo]
    dominio = getattr(getattr(ecuacion, "parsed", None), "dominio", "")
    if dominio:
        advertencias.append(f"Dominio declarado en el enunciado: {dominio}.")
    if numerico.mensaje:
        advertencias.append(numerico.mensaje)
    if existencia.no_unicidad:
        advertencias.append(
            existencia.motivo_no_unicidad
            or "La solución puede no ser única en el punto inicial."
        )
    if existencia.explota and existencia.tiempo_explosion is not None:
        advertencias.append(
            f"Posible explosión en x ≈ {existencia.tiempo_explosion:.6g}."
        )
    return ResultadoSolucion(
        ecuacion_texto=texto,
        ecuacion_latex=ecuacion.latex,
        tipo="Integración numérica",
        tipos=[tipo.etiqueta for tipo in tipos],
        camino="numerica",
        solucion=numerico,
        solucion_latex=rf"y(x) \approx \text{{solución numérica ({numerico.metodo})}}",
        certificado=certificado,
        advertencias=list(dict.fromkeys(advertencias)),
        pasos=pasos_numericos(numerico),
        x0=x0,
        y0=y0,
        intervalo=(x_min, x_max),
        numerico=numerico,
        existencia=existencia,
        resultado_motor=None,
    )


def _adjuntar_numerico(
    resultado: ResultadoSolucion,
    x_min: float,
    x_max: float,
    *,
    ecuacion: Ecuacion | None = None,
) -> None:
    if resultado.numerico is not None or resultado.x0 is None or resultado.y0 is None:
        return
    if ecuacion is None:
        ecuacion = parsear(resultado.ecuacion_texto)
    numerico = integrar_intervalo(
        ecuacion.rhs, resultado.x0, resultado.y0, x_min, x_max
    )
    if numerico.exito:
        resultado.numerico = numerico
        if resultado.particular_latex == "":
            resultado.advertencias.append(
                "No se pudo aplicar la condición inicial a la solución general; "
                "se muestra la familia y la curva numérica del PVI."
            )


def resolver(
    texto: str,
    x0: float | None = None,
    y0: float | None = None,
    x_min: float = -5.0,
    x_max: float = 5.0,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
    incluir_numerico: bool = True,
) -> ResultadoSolucion:
    """Resuelve una EDO con el camino analítico y, si hace falta, el numérico."""

    if x_min >= x_max:
        raise EntradaInvalida(
            "El intervalo no es válido: x_min debe ser estrictamente menor "
            "que x_max."
        )
    if (x0 is None) != (y0 is None):
        raise EntradaInvalida(
            "Para un PVI debes indicar x₀ e y₀; para la solución general deja "
            "ambos vacíos."
        )
    ecuacion = parsear(texto)

    motivo = ""
    motor = None
    try:
        motor = resolver_motor(
            texto,
            x0=x0,
            y0=y0,
            timeout=timeout,
            metodo=metodo,
            x_min=x_min,
            x_max=x_max,
            calcular_numerico=False,
        )
    except TiempoAgotado as exc:
        motivo = str(exc)
    except SolucionNoDisponible as exc:
        motivo = str(exc)

    if motor is not None and motor.general is not None:
        resultado = convertir_motor(
            motor,
            texto,
            camino="analitica",
            x0=x0,
            y0=y0,
            intervalo=(x_min, x_max),
            ecuacion=ecuacion,
        )
        if incluir_numerico and x0 is not None and y0 is not None:
            _adjuntar_numerico(resultado, x_min, x_max, ecuacion=ecuacion)
        if resultado.particular_latex == "" and x0 is not None:
            resultado.advertencias.append(
                "La solución general no permitió imponer la condición inicial "
                "en una rama real; revisa el dominio o prueba otro punto."
            )
        dominio = getattr(getattr(ecuacion, "parsed", None), "dominio", "")
        if dominio:
            resultado.advertencias.insert(
                0, f"Dominio declarado en el enunciado: {dominio}."
            )
        return resultado

    if motor is not None and motor.error:
        motivo = motor.error
    if x0 is None or y0 is None:
        if motivo:
            raise SolucionNoDisponible(
                "No se encontró una solución simbólica verificable. " + motivo
            )
        raise SolucionNoDisponible(
            "No se encontró una solución simbólica verificable. Indica x₀ e y₀ "
            "para intentar la vía numérica."
        )
    if not incluir_numerico:
        raise SolucionNoDisponible(
            motivo or "No hay solución simbólica y la vía numérica está desactivada."
        )
    return _resultado_numerico(
        texto,
        x0=float(x0),
        y0=float(y0),
        x_min=float(x_min),
        x_max=float(x_max),
        motivo=motivo or "Se usó el respaldo numérico porque no hubo forma cerrada verificable.",
        ecuacion=ecuacion,
    )


def _evaluar_curva_expresion(
    expresion: sp.Expr,
    x_min: float,
    x_max: float,
    n_points: int,
) -> tuple[np.ndarray, np.ndarray] | None:
    try:
        funcion = sp.lambdify(X, expresion, modules=lambdify_modules())
        xs = np.linspace(float(x_min), float(x_max), max(int(n_points), 2))
        with np.errstate(all="ignore"):
            raw = np.asarray(funcion(xs), dtype=complex)
        if raw.shape != xs.shape:
            raw = np.broadcast_to(raw, xs.shape)
        mascara = np.isfinite(raw.real) & np.isfinite(raw.imag) & (np.abs(raw.imag) <= 1e-9)
        return xs[mascara], raw.real[mascara].astype(float)
    except Exception:
        return None


def curva_solucion(
    resultado: ResultadoSolucion,
    *,
    x_min: float | None = None,
    x_max: float | None = None,
    n_points: int = 500,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Devuelve puntos ``(x, y)`` para dibujar la solución."""

    def_min, def_max = (
        resultado.intervalo if resultado.intervalo is not None else (-5.0, 5.0)
    )
    req_min = float(def_min if x_min is None else x_min)
    req_max = float(def_max if x_max is None else x_max)
    rango_personalizado = (
        (x_min is not None and not math.isclose(req_min, float(def_min), rel_tol=0.0, abs_tol=1e-9))
        or (x_max is not None and not math.isclose(req_max, float(def_max), rel_tol=0.0, abs_tol=1e-9))
    )

    if not rango_personalizado and resultado.numerico is not None and resultado.numerico.exito:
        return (
            np.asarray(resultado.numerico.x, dtype=float),
            np.asarray(resultado.numerico.y, dtype=float),
        )

    solucion = resultado.solucion
    expresion = getattr(solucion, "expr", None)
    tiene_simbolica = (
        expresion is not None
        and getattr(solucion, "is_explicit", False)
        and not (expresion.free_symbols - {X, Y})
    )
    if tiene_simbolica:
        curva = _evaluar_curva_expresion(expresion, req_min, req_max, n_points)
        if curva is not None:
            return curva

    if resultado.numerico is not None and resultado.numerico.exito:
        nx = np.asarray(resultado.numerico.x, dtype=float)
        ny = np.asarray(resultado.numerico.y, dtype=float)
        if (
            rango_personalizado
            and nx.size > 0
            and not resultado.numerico.explosion
            and resultado.x0 is not None
            and resultado.y0 is not None
            and req_min <= resultado.x0 <= req_max
            and (req_min < float(nx[0]) - 1e-6 or req_max > float(nx[-1]) + 1e-6)
        ):
            try:
                ecuacion = parsear(resultado.ecuacion_texto)
                recalculado = integrar_intervalo(
                    ecuacion.rhs,
                    float(resultado.x0),
                    float(resultado.y0),
                    req_min,
                    req_max,
                    n_points=n_points,
                )
                if recalculado.exito:
                    return np.asarray(recalculado.x, dtype=float), np.asarray(recalculado.y, dtype=float)
            except Exception:
                pass
        mascara = (nx >= req_min) & (nx <= req_max)
        return nx[mascara], ny[mascara]

    return None


def curvas_familia(
    resultado: ResultadoSolucion,
    *,
    constantes: tuple[float, ...] = (-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0),
    n_points: int = 400,
) -> list[tuple[np.ndarray, np.ndarray, str]]:
    """Puntos de la familia general al variar la constante de integración."""

    motor = getattr(resultado, "resultado_motor", None)
    general = getattr(motor, "general", None)
    if general is None or not getattr(general, "is_explicit", False):
        return []
    expresion = getattr(general, "expr", None)
    if expresion is None:
        return []
    constante = getattr(general, "constant", None)
    if constante is None:
        candidatas = expresion.free_symbols - {X, Y}
        constante = next(iter(candidatas), None)
    if constante is not None and expresion.free_symbols - {X, Y, constante}:
        return []
    if resultado.intervalo is None:
        x_min, x_max = -5.0, 5.0
    else:
        x_min, x_max = resultado.intervalo
    xs = np.linspace(float(x_min), float(x_max), max(int(n_points), 2))
    curvas: list[tuple[np.ndarray, np.ndarray, str]] = []
    for valor in constantes:
        try:
            expr = expresion if constante is None else expresion.subs(constante, float(valor))
            funcion = sp.lambdify(X, expr, modules=lambdify_modules())
            with np.errstate(all="ignore"):
                ys = np.asarray(funcion(xs), dtype=float)
            if ys.shape != xs.shape:
                ys = np.broadcast_to(ys, xs.shape).astype(float)
            mascara = np.isfinite(ys)
            if np.any(mascara):
                curvas.append((xs[mascara], ys[mascara], f"C = {valor:g}"))
        except Exception:
            continue
    return curvas


def curva_desde_punto(
    texto: str,
    x_punto: float,
    y_punto: float,
    *,
    x_min: float = -5.0,
    x_max: float = 5.0,
    metodo: str = "RK45",
) -> ResultadoNumerico:
    """Traza la curva que pasa por un punto elegido en el campo de direcciones."""

    ecuacion = parsear(texto)
    if not (x_min <= x_punto <= x_max):
        raise EntradaInvalida("El punto elegido debe estar dentro del intervalo.")
    return integrar_intervalo(
        ecuacion.rhs,
        float(x_punto),
        float(y_punto),
        float(x_min),
        float(x_max),
        metodo=metodo,
    )


def evaluar_solucion(resultado: ResultadoSolucion, x: float) -> float | None:
    """Evalúa la solución particular en un punto, si es posible."""

    solucion = resultado.solucion
    expresion = getattr(solucion, "expr", None)
    if expresion is None or not getattr(solucion, "is_explicit", False):
        return None
    if expresion.free_symbols - {X, Y}:
        return None
    try:
        valor = complex(sp.N(expresion.subs(X, x)))
    except Exception:
        return None
    if abs(valor.imag) > 1e-8 or not math.isfinite(valor.real):
        return None
    return float(valor.real)


__all__ = [
    "resolver",
    "curva_solucion",
    "curvas_familia",
    "curva_desde_punto",
    "evaluar_solucion",
]
