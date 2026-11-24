"""Estudios de convergencia, orden empírico y benchmark de métodos numéricos."""

from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import sympy as sp

from odecalc.symbols import X

from core.solver_numerico import (
    METODOS_PROPIOS,
    benchmark_metodos,
    resolver_metodo,
    resolver_scipy,
)
from core.tipos import (
    BenchmarkItem,
    FilaConvergencia,
    ResultadoConvergencia,
    SolucionNoDisponible,
)


def _referencia_final(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
) -> float:
    referencia = resolver_scipy(
        rhs,
        x0,
        y0,
        x_fin,
        metodo="DOP853",
        rtol=1e-12,
        atol=1e-14,
        n_points=50,
    )
    if not referencia.exito or referencia.y.size == 0:
        raise SolucionNoDisponible(
            "No se pudo construir una referencia numérica de alta precisión."
        )
    return float(referencia.y[-1])


def _error(
    resultado,
    exacto: object | None,
    referencia_final: float | None,
) -> float | None:
    if not resultado.exito or resultado.y.size == 0:
        return None
    if exacto is not None:
        if resultado.error_max is not None:
            return float(resultado.error_max)
        return None
    if referencia_final is None:
        return None
    return float(abs(float(resultado.y[-1]) - referencia_final))


def estudio_convergencia(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    exacto: object | None = None,
    metodos: Iterable[str] = ("Euler", "Heun", "RK4"),
    hs: Iterable[float] | None = None,
    min_puntos: int = 3,
) -> ResultadoConvergencia:
    """Calcula error vs h y ajusta el orden empírico por regresión log-log."""

    hs = tuple(hs) if hs is not None else (0.2, 0.1, 0.05, 0.025, 0.0125, 0.00625)
    metodos = tuple(metodos)
    for metodo in metodos:
        if metodo not in METODOS_PROPIOS:
            raise SolucionNoDisponible(
                "El estudio de orden empírico usa métodos de paso fijo: "
                + ", ".join(METODOS_PROPIOS)
                + "."
            )
    referencia = (
        None if exacto is not None else _referencia_final(rhs, x0, y0, x_fin)
    )

    filas: list[FilaConvergencia] = []
    errores: dict[str, list[tuple[float, float]]] = {metodo: [] for metodo in metodos}
    notas: list[str] = []
    for metodo in metodos:
        for h in hs:
            resultado = resolver_metodo(
                rhs,
                x0,
                y0,
                x_fin,
                metodo=metodo,
                h=float(h),
                exacto=exacto,
            )
            error = _error(resultado, exacto, referencia)
            if error is None or not math.isfinite(error):
                notas.append(
                    f"{metodo} con h={h:g}: no se pudo evaluar el error "
                    f"({resultado.mensaje})."
                )
                continue
            filas.append(
                FilaConvergencia(
                    metodo=metodo,
                    h=float(resultado.h if resultado.h is not None else h),
                    error_max=error,
                    puntos=int(resultado.x.size),
                )
            )
            if error > 0:
                errores[metodo].append((float(h), error))

    ordenes: dict[str, float] = {}
    for metodo, pares in errores.items():
        if len(pares) < min_puntos:
            continue
        hs_validos = np.asarray([par[0] for par in pares], dtype=float)
        es_validos = np.asarray([par[1] for par in pares], dtype=float)
        try:
            pendiente, _ = np.polyfit(np.log(hs_validos), np.log(es_validos), 1)
            ordenes[metodo] = float(pendiente)
        except Exception:
            continue

    if exacto is None:
        notas.append(
            "El error se midió contra una referencia DOP853 con tolerancias "
            "muy estrictas."
        )
    return ResultadoConvergencia(
        filas=filas,
        ordenes=ordenes,
        referencia="solución exacta" if exacto is not None else "DOP853 (alta precisión)",
        notas=notas,
    )


def benchmark(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_fin: float,
    *,
    h: float = 0.05,
    exacto: object | None = None,
    metodos: Iterable[str] = ("Euler", "Heun", "RK4", "RK45", "BDF", "Radau"),
) -> list[BenchmarkItem]:
    """Benchmark en vivo de varios métodos."""

    return benchmark_metodos(
        rhs, x0, y0, x_fin, h=h, exacto=exacto, metodos=metodos
    )


def validar_orden(orden: float, esperado: float, tolerancia: float = 0.2) -> bool:
    """Comprueba si el orden empírico cae en la banda esperada."""

    return abs(orden - esperado) <= tolerancia


__all__ = [
    "estudio_convergencia",
    "benchmark",
    "validar_orden",
]
