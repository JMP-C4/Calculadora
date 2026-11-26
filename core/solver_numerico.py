"""Métodos numéricos de un paso y comparación de integradores.

Incluye implementaciones didácticas propias de Euler, Heun y RK4, además de
los integradores adaptativos de SciPy (RK45, DOP853, BDF y Radau).  El motor
no depende de la interfaz y devuelve siempre :class:`ResultadoNumerico`.
"""

from __future__ import annotations

import math
import time
import warnings
from typing import Callable, Iterable

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

from core.tipos import (
    BenchmarkItem,
    InfoRigidez,
    ResultadoNumerico,
    SolucionNoDisponible,
)
from odecalc.numeric.solver import integrate_scipy_segment, scalar_evaluator
from odecalc.symbols import X, Y, lambdify_modules

METODOS_PROPIOS = ("Euler", "Heun", "RK4")
METODOS_SCIPY = ("RK45", "DOP853", "BDF", "Radau")
METODOS = METODOS_PROPIOS + METODOS_SCIPY


def _preparar_funcion(rhs: sp.Expr) -> Callable[[float, float], float]:
    try:
        evaluar = scalar_evaluator(rhs)
    except ValueError as exc:
        raise SolucionNoDisponible(str(exc)) from exc

    def funcion(x: float, y: float) -> float:
        numero = evaluar(float(x), float(y))
        if not math.isfinite(numero):
            raise ValueError("f(x, y) no es finita.")
        return numero

    return funcion


def _evaluar_exacto(exacto: object, x: np.ndarray) -> np.ndarray | None:
    if exacto is None:
        return None
    try:
        if isinstance(exacto, sp.Expr):
            simbolos = exacto.free_symbols
            if simbolos - {X}:
                return None
            funcion = sp.lambdify(X, exacto, modules=lambdify_modules())
            with np.errstate(all="ignore"):
                valores = funcion(x)
        elif callable(exacto):
            valores = exacto(x)
        else:
            return None
        crudo = np.asarray(valores, dtype=complex)
        if crudo.shape != x.shape:
            crudo = np.broadcast_to(crudo, x.shape)
        return np.where(
            np.isfinite(crudo.real) & np.isfinite(crudo.imag) & (np.abs(crudo.imag) <= 1e-9),
            crudo.real,
            np.nan,
        ).astype(float)
    except Exception:
        return None


def _error_max(y: np.ndarray, exacto: object, x: np.ndarray) -> float | None:
    valores = _evaluar_exacto(exacto, x)
    if valores is None:
        return None
    mascara = np.isfinite(valores) & np.isfinite(y)
    if not np.any(mascara):
        return None
    return float(np.max(np.abs(y[mascara] - valores[mascara])))


def _resultado_fallido(metodo: str, mensaje: str, **extra) -> ResultadoNumerico:
    return ResultadoNumerico(
        metodo=metodo,
        exito=False,
        mensaje=mensaje,
        **extra,
    )


def resolver_metodo(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    metodo: str = "RK4",
    h: float = 0.1,
    exacto: object | None = None,
    max_pasos: int = 1_000_000,
) -> ResultadoNumerico:
    """Integra ``y' = rhs`` con un método de paso fijo.

    Parameters
    ----------
    rhs:
        Lado derecho ``f(x, y)`` como expresión SymPy.
    x0, y0:
        Condición inicial.
    x_fin:
        Extremo final (puede ser menor que ``x0`` para integrar hacia atrás).
    metodo:
        ``Euler``, ``Heun`` o ``RK4``.
    h:
        Tamaño de paso (se toma su valor absoluto).
    exacto:
        Expresión o función opcional para calcular el error máximo.
    """

    nombre = metodo.strip()
    if nombre.lower() in {"euler", "euler_explicito"}:
        nombre = "Euler"
    elif nombre.lower() in {"heun", "rk2", "punto_medio"}:
        nombre = "Heun"
    elif nombre.lower() in {"rk4", "runge_kutta", "runge-kutta"}:
        nombre = "RK4"
    if nombre not in METODOS_PROPIOS:
        raise SolucionNoDisponible(
            f"Método propio desconocido: {metodo}. Usa Euler, Heun o RK4."
        )

    try:
        x0 = float(x0)
        y0 = float(y0)
        x_fin = float(x_fin)
        h_abs = abs(float(h))
    except (TypeError, ValueError):
        return _resultado_fallido(nombre, "Los datos numéricos no son válidos.")
    if not all(math.isfinite(v) for v in (x0, y0, x_fin, h_abs)):
        return _resultado_fallido(nombre, "Los datos deben ser finitos.")
    if h_abs <= 0:
        return _resultado_fallido(nombre, "El paso h debe ser positivo.")

    try:
        f = _preparar_funcion(rhs)
    except SolucionNoDisponible as exc:
        return _resultado_fallido(nombre, str(exc))

    distancia = abs(x_fin - x0)
    if distancia == 0:
        return ResultadoNumerico(
            x=np.asarray([x0]),
            y=np.asarray([y0]),
            metodo=nombre,
            exito=True,
            mensaje="El intervalo tiene longitud cero.",
            h=h_abs,
        )

    direccion = 1.0 if x_fin > x0 else -1.0
    n_pasos = max(1, int(math.ceil(distancia / h_abs)))
    h_real = direccion * distancia / n_pasos
    if n_pasos > max_pasos:
        return _resultado_fallido(
            nombre,
            f"Se necesitarían {n_pasos} pasos; aumenta h o reduce el intervalo.",
        )

    xs = np.empty(n_pasos + 1, dtype=float)
    ys = np.empty(n_pasos + 1, dtype=float)
    xs[0], ys[0] = x0, y0
    evaluaciones = 0
    explosion = False

    try:
        for indice in range(n_pasos):
            x_actual, y_actual = xs[indice], ys[indice]
            if nombre == "Euler":
                k1 = f(x_actual, y_actual)
                evaluaciones += 1
                y_siguiente = y_actual + h_real * k1
            elif nombre == "Heun":
                k1 = f(x_actual, y_actual)
                k2 = f(x_actual + h_real, y_actual + h_real * k1)
                evaluaciones += 2
                y_siguiente = y_actual + h_real * (k1 + k2) / 2.0
            else:  # RK4 clásico
                k1 = f(x_actual, y_actual)
                k2 = f(x_actual + h_real / 2.0, y_actual + h_real * k1 / 2.0)
                k3 = f(x_actual + h_real / 2.0, y_actual + h_real * k2 / 2.0)
                k4 = f(x_actual + h_real, y_actual + h_real * k3)
                evaluaciones += 4
                y_siguiente = y_actual + h_real * (k1 + 2 * k2 + 2 * k3 + k4) / 6.0
            if not math.isfinite(float(y_siguiente)):
                explosion = True
                raise ValueError("la solución numérica dejó de ser finita")
            xs[indice + 1] = x_actual + h_real
            ys[indice + 1] = float(y_siguiente)
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        recortado = indice + 1
        xs = xs[:recortado]
        ys = ys[:recortado]
        error = _error_max(ys, exacto, xs)
        return ResultadoNumerico(
            x=xs,
            y=ys,
            metodo=nombre,
            exito=False,
            mensaje=(
                "La integración se detuvo porque la solución dejó de ser "
                f"finita ({exc})."
            ),
            f_evaluaciones=evaluaciones,
            h=abs(h_real),
            error_max=error,
            explosion=explosion,
        )

    error = _error_max(ys, exacto, xs)
    mensaje = f"Integración completada con {n_pasos} pasos de h = {abs(h_real):.6g}."
    return ResultadoNumerico(
        x=xs,
        y=ys,
        metodo=nombre,
        exito=True,
        mensaje=mensaje,
        f_evaluaciones=evaluaciones,
        h=abs(h_real),
        error_max=error,
    )


def euler(rhs: sp.Expr, x0: float, y0: float, x_fin: float, h: float = 0.1, **kw) -> ResultadoNumerico:
    """Método de Euler explícito."""

    return resolver_metodo(rhs, x0, y0, x_fin, metodo="Euler", h=h, **kw)


def heun(rhs: sp.Expr, x0: float, y0: float, x_fin: float, h: float = 0.1, **kw) -> ResultadoNumerico:
    """Método de Heun (RK2)."""

    return resolver_metodo(rhs, x0, y0, x_fin, metodo="Heun", h=h, **kw)


def rk4(rhs: sp.Expr, x0: float, y0: float, x_fin: float, h: float = 0.1, **kw) -> ResultadoNumerico:
    """Método de Runge-Kutta clásico de cuarto orden."""

    return resolver_metodo(rhs, x0, y0, x_fin, metodo="RK4", h=h, **kw)


def _integrar_scipy(
    f: Callable[[float, float], float],
    x0: float,
    y0: float,
    x_fin: float,
    metodo: str,
    rtol: float,
    atol: float,
    n_points: int,
) -> tuple[object, int]:
    nfev = 0

    def funcion(t: float, estado: np.ndarray) -> list[float]:
        nonlocal nfev
        nfev += 1
        return [f(t, float(estado[0]))]

    puntos = max(int(n_points), 2)
    t_eval = np.linspace(x0, x_fin, puntos)
    solucion = solve_ivp(
        funcion,
        (x0, x_fin),
        [y0],
        method=metodo,
        t_eval=t_eval,
        rtol=rtol,
        atol=atol,
    )
    return solucion, nfev


def resolver_scipy(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    metodo: str = "RK45",
    rtol: float = 1e-8,
    atol: float = 1e-10,
    n_points: int = 500,
    exacto: object | None = None,
    _evaluador: Callable[[float, float], float] | None = None,
) -> ResultadoNumerico:
    """Integra con SciPy y cambia a un método implícito si detecta rigidez."""

    nombre = metodo.strip()
    if nombre.lower() == "dop853":
        nombre = "DOP853"
    elif nombre.lower() in {"radau", "bdf", "rk45"}:
        nombre = nombre.upper()
    if nombre not in METODOS_SCIPY:
        raise SolucionNoDisponible(
            f"Método de SciPy desconocido: {metodo}. Usa {', '.join(METODOS_SCIPY)}."
        )
    if x0 == x_fin:
        return ResultadoNumerico(
            x=np.asarray([x0]),
            y=np.asarray([y0]),
            metodo=nombre,
            exito=True,
            mensaje="El intervalo tiene longitud cero.",
        )

    if _evaluador is None:
        try:
            evaluador = scalar_evaluator(rhs)
        except ValueError as exc:
            return _resultado_fallido(nombre, str(exc))
    else:
        evaluador = _evaluador

    intentos: tuple[str, ...] = (
        (nombre, "BDF", "Radau") if nombre in {"RK45", "DOP853"} else (nombre,)
    )
    resultado_seg = integrate_scipy_segment(
        evaluador,
        float(x0),
        float(x_fin),
        float(y0),
        n_points=n_points,
        rtol=rtol,
        atol=atol,
        methods=intentos,
    )
    if resultado_seg.success:
        error = _error_max(resultado_seg.y, exacto, resultado_seg.t)
        detalle = ""
        if resultado_seg.stiff:
            detalle += " Se cambió automáticamente a un integrador implícito por rigidez."
        if resultado_seg.blow_up:
            detalle += " Se detectó una posible explosión o frontera de dominio."
        return ResultadoNumerico(
            x=resultado_seg.t,
            y=resultado_seg.y,
            metodo=resultado_seg.method,
            exito=True,
            mensaje=(
                f"Integración exitosa con {resultado_seg.method} "
                f"({resultado_seg.t.size} puntos)." + detalle
            ),
            f_evaluaciones=resultado_seg.nfev,
            error_max=error,
            rigido=resultado_seg.stiff,
            explosion=resultado_seg.blow_up,
        )

    return _resultado_fallido(
        resultado_seg.method or nombre,
        f"La integración numérica falló ({resultado_seg.message}).",
        f_evaluaciones=resultado_seg.nfev,
        rigido=resultado_seg.stiff,
        explosion=resultado_seg.blow_up,
    )


def comparar_metodos(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    h: float = 0.1,
    exacto: object | None = None,
    metodos: Iterable[str] = ("Euler", "Heun", "RK4", "RK45", "BDF", "Radau"),
) -> list[ResultadoNumerico]:
    """Ejecuta varios métodos sobre el mismo problema y devuelve sus resultados."""

    resultados: list[ResultadoNumerico] = []
    for metodo in metodos:
        if metodo in METODOS_PROPIOS:
            resultados.append(
                resolver_metodo(rhs, x0, y0, x_fin, metodo=metodo, h=h, exacto=exacto)
            )
        else:
            resultados.append(
                resolver_scipy(rhs, x0, y0, x_fin, metodo=metodo, exacto=exacto)
            )
    return resultados


def integrar_intervalo(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_min: float,
    x_max: float,
    *,
    metodo: str = "RK45",
    n_points: int = 500,
    exacto: object | None = None,
) -> ResultadoNumerico:
    """Integra hacia atrás y hacia delante desde ``x0`` dentro de un intervalo."""

    try:
        x0, y0, x_min, x_max = float(x0), float(y0), float(x_min), float(x_max)
    except (TypeError, ValueError):
        return _resultado_fallido("auto", "El intervalo y el PVI deben ser numéricos.")
    if not all(math.isfinite(v) for v in (x0, y0, x_min, x_max)):
        return _resultado_fallido("auto", "El intervalo y el PVI deben ser finitos.")
    if x_min >= x_max:
        return _resultado_fallido(
            "auto", "El intervalo no es válido: x_min debe ser menor que x_max."
        )
    if not (x_min <= x0 <= x_max):
        return _resultado_fallido(
            "auto", "La condición inicial x₀ debe pertenecer al intervalo."
        )

    try:
        evaluador = scalar_evaluator(rhs)
        valor_inicial = evaluador(x0, y0)
    except Exception as exc:
        return _resultado_fallido("auto", str(exc))
    if not math.isfinite(valor_inicial):
        return _resultado_fallido(
            "auto",
            "La derivada no es finita en la condición inicial "
            f"(x₀={x0:g}, y₀={y0:g}); se omite la integración numérica.",
        )

    segmentos: list[ResultadoNumerico] = []
    if x0 > x_min:
        segmentos.append(
            resolver_scipy(
                rhs,
                x0,
                y0,
                x_min,
                metodo=metodo,
                n_points=n_points,
                exacto=exacto,
                _evaluador=evaluador,
            )
        )
    if x0 < x_max:
        segmentos.append(
            resolver_scipy(
                rhs,
                x0,
                y0,
                x_max,
                metodo=metodo,
                n_points=n_points,
                exacto=exacto,
                _evaluador=evaluador,
            )
        )
    exitosos = [segmento for segmento in segmentos if segmento.exito]
    explosion = any(segmento.explosion for segmento in segmentos)
    if not exitosos:
        detalle = "; ".join(segmento.mensaje for segmento in segmentos)
        return _resultado_fallido(
            segmentos[0].metodo if segmentos else "auto",
            f"La integración numérica falló en ambos sentidos ({detalle}).",
            explosion=explosion,
        )

    x = np.concatenate([segmento.x for segmento in exitosos])
    y = np.concatenate([segmento.y for segmento in exitosos])
    orden = np.argsort(x, kind="stable")
    x, y = x[orden], y[orden]
    x_unicos, indices = np.unique(x, return_index=True)
    x, y = x_unicos, y[indices]
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        return _resultado_fallido(
            "auto", "La solución numérica contiene valores no finitos.", explosion=True
        )
    metodos = sorted({segmento.metodo for segmento in exitosos})
    mensaje = (
        f"Integración numérica exitosa en {x.size} puntos con "
        f"{'/'.join(metodos)}."
    )
    if explosion:
        mensaje += " Se detectó una posible explosión o frontera de dominio."
    if len(exitosos) != len(segmentos):
        mensaje += " Sólo uno de los dos sentidos pudo integrarse."
    return ResultadoNumerico(
        x=x,
        y=y,
        metodo="/".join(metodos),
        exito=True,
        mensaje=mensaje,
        f_evaluaciones=sum(segmento.f_evaluaciones for segmento in exitosos),
        error_max=_error_max(y, exacto, x),
        rigido=any(segmento.rigido for segmento in exitosos),
        explosion=explosion,
    )


def benchmark_metodos(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    h: float = 0.05,
    exacto: object | None = None,
    metodos: Iterable[str] = ("Euler", "Heun", "RK4", "RK45", "BDF", "Radau"),
) -> list[BenchmarkItem]:
    """Mide tiempo, evaluaciones de f, pasos y error máximo por método."""

    items: list[BenchmarkItem] = []
    for metodo in metodos:
        inicio = time.perf_counter()
        if metodo in METODOS_PROPIOS:
            resultado = resolver_metodo(
                rhs, x0, y0, x_fin, metodo=metodo, h=h, exacto=exacto
            )
        else:
            resultado = resolver_scipy(
                rhs, x0, y0, x_fin, metodo=metodo, exacto=exacto
            )
        transcurrido = (time.perf_counter() - inicio) * 1000.0
        items.append(
            BenchmarkItem(
                metodo=metodo,
                tiempo_ms=transcurrido,
                f_evaluaciones=resultado.f_evaluaciones,
                error_max=resultado.error_max,
                pasos=int(resultado.x.size),
                exito=resultado.exito,
                notas=resultado.mensaje,
            )
        )
    return items


def detectar_rigidez(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
) -> InfoRigidez:
    """Estima rigidez con el jacobiano y el coste de RK45."""

    jacobiano_max: float | None = None
    try:
        dfdy = sp.simplify(sp.diff(rhs, Y))
        if not dfdy.has(Y):
            funcion = sp.lambdify(X, dfdy, modules=lambdify_modules())
            x_muestras = np.linspace(float(x0), float(x_fin), 50)
            with np.errstate(all="ignore"):
                valores = np.asarray(funcion(x_muestras), dtype=float)
            finitos = valores[np.isfinite(valores)]
            if finitos.size:
                jacobiano_max = float(np.max(np.abs(finitos)))
        else:
            funcion = sp.lambdify((X, Y), dfdy, modules=lambdify_modules())
            x_muestras = np.linspace(float(x0), float(x_fin), 40)
            y_muestras = float(y0) + np.linspace(-1.0, 1.0, 21) * max(1.0, abs(float(y0)))
            xx, yy = np.meshgrid(x_muestras, y_muestras)
            with np.errstate(all="ignore"):
                valores = np.asarray(funcion(xx, yy), dtype=float)
            finitos = valores[np.isfinite(valores)]
            if finitos.size:
                jacobiano_max = float(np.max(np.abs(finitos)))
    except Exception:
        jacobiano_max = None

    nfev: int | None = None
    try:
        evaluador = scalar_evaluator(rhs)
        resultado_rk = integrate_scipy_segment(
            evaluador,
            float(x0),
            float(x_fin),
            float(y0),
            methods=("RK45",),
            rtol=1e-6,
            atol=1e-9,
            n_points=200,
        )
        nfev = resultado_rk.nfev
        if (
            not resultado_rk.success
            and not resultado_rk.blow_up
            and "step size" in resultado_rk.message.lower()
        ):
            return InfoRigidez(
                rigida=True,
                motivo=(
                    "RK45 redujo el paso hasta el límite de precisión; el "
                    "problema es probablemente rígido."
                ),
                metodo_recomendado="BDF",
                jacobiano_max=jacobiano_max,
                nfev_rk45=nfev,
            )
    except Exception:
        nfev = None

    distancia = abs(float(x_fin) - float(x0))
    escala = (jacobiano_max or 0.0) * max(distancia, 1.0)
    if escala > 50.0 or (nfev is not None and nfev > 5000):
        motivo = (
            f"El jacobiano |∂f/∂y| alcanza {jacobiano_max:.3g} y el producto "
            f"|∂f/∂y|·Δx ≈ {escala:.3g}; conviene un método implícito."
            if jacobiano_max is not None
            else "RK45 necesitó muchísimas evaluaciones; conviene un método implícito."
        )
        return InfoRigidez(
            rigida=True,
            motivo=motivo,
            metodo_recomendado="BDF/Radau",
            jacobiano_max=jacobiano_max,
            nfev_rk45=nfev,
        )
    return InfoRigidez(
        rigida=False,
        motivo="No se detectaron signos claros de rigidez en el intervalo.",
        metodo_recomendado="RK45/DOP853",
        jacobiano_max=jacobiano_max,
        nfev_rk45=nfev,
    )


__all__ = [
    "METODOS",
    "METODOS_PROPIOS",
    "METODOS_SCIPY",
    "resolver_metodo",
    "resolver_scipy",
    "euler",
    "heun",
    "rk4",
    "comparar_metodos",
    "integrar_intervalo",
    "benchmark_metodos",
    "detectar_rigidez",
]
