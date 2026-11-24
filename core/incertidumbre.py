"""Incertidumbre: Monte Carlo y análisis de sensibilidad global con Sobol."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp

from odecalc.symbols import X, Y

from core.solver_numerico import integrar_intervalo
from core.tipos import EntradaInvalida, SolucionNoDisponible


@dataclass
class Distribucion:
    """Distribución de un parámetro o condición inicial."""

    nombre: str
    tipo: str = "normal"  # "normal" | "uniforme" | "fija"
    media: float = 0.0
    desviacion: float = 0.0
    minimo: float | None = None
    maximo: float | None = None

    def muestrear(self, generador: np.random.Generator, n: int) -> np.ndarray:
        if self.tipo == "fija":
            return np.full(n, float(self.media))
        if self.tipo == "uniforme":
            bajo = self.minimo if self.minimo is not None else self.media - self.desviacion
            alto = self.maximo if self.maximo is not None else self.media + self.desviacion
            if bajo >= alto:
                return np.full(n, float(self.media))
            return generador.uniform(float(bajo), float(alto), n)
        if self.tipo != "normal":
            raise EntradaInvalida(f"Distribución desconocida: {self.tipo}.")
        muestras = generador.normal(float(self.media), max(float(self.desviacion), 0.0), n)
        if self.minimo is not None:
            muestras = np.maximum(muestras, self.minimo)
        if self.maximo is not None:
            muestras = np.minimum(muestras, self.maximo)
        return muestras


@dataclass
class ResultadoMonteCarlo:
    """Bandas de predicción obtenidas por Monte Carlo."""

    x: np.ndarray
    media: np.ndarray
    banda_inf: np.ndarray
    banda_sup: np.ndarray
    muestras: np.ndarray
    n_exitos: int
    n_total: int
    nivel: float
    parametros: dict[str, np.ndarray] = field(default_factory=dict)
    semilla: int = 42
    notas: list[str] = field(default_factory=list)

    @property
    def porcentaje_exito(self) -> float:
        return 100.0 * self.n_exitos / self.n_total if self.n_total else 0.0


@dataclass
class ResultadoSobol:
    """Índices de Sobol de primer orden y totales."""

    nombres: list[str]
    S1: np.ndarray
    ST: np.ndarray
    S1_conf: np.ndarray
    ST_conf: np.ndarray
    N: int
    semilla: int = 42
    salida_media: float | None = None
    notas: list[str] = field(default_factory=list)


def _trayectoria(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_eval: np.ndarray,
) -> np.ndarray | None:
    x_min = float(min(x0, np.min(x_eval)))
    x_max = float(max(x0, np.max(x_eval)))
    resultado = integrar_intervalo(rhs, x0, y0, x_min, x_max, n_points=200)
    if not resultado.exito or resultado.x.size < 2:
        return None
    valores = np.interp(x_eval, resultado.x, resultado.y, left=np.nan, right=np.nan)
    return valores if np.all(np.isfinite(valores)) else None


def monte_carlo(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_eval: np.ndarray | list[float],
    *,
    parametros: dict[str, Distribucion] | None = None,
    distribucion_x0: Distribucion | None = None,
    distribucion_y0: Distribucion | None = None,
    n_muestras: int = 800,
    semilla: int = 42,
    nivel: float = 0.90,
) -> ResultadoMonteCarlo:
    """Propaga incertidumbre sobre parámetros y condiciones iniciales."""

    x = np.asarray(sorted(float(v) for v in x_eval), dtype=float)
    if x.size < 2:
        raise EntradaInvalida("Se necesitan al menos dos puntos para la banda.")
    if not (0 < nivel < 1):
        raise EntradaInvalida("El nivel de la banda debe estar entre 0 y 1.")
    n_muestras = max(int(n_muestras), 10)
    generador = np.random.default_rng(int(semilla))
    parametros = parametros or {}
    simbolos = sorted(rhs.free_symbols - {X, Y}, key=lambda s: s.name)
    faltantes = [str(s) for s in simbolos if str(s) not in parametros]
    if faltantes:
        raise EntradaInvalida(
            "Faltan distribuciones para los parámetros: " + ", ".join(faltantes)
        )

    muestras_parametros = {
        nombre: distribucion.muestrear(generador, n_muestras)
        for nombre, distribucion in parametros.items()
    }
    x0_muestras = (
        distribucion_x0.muestrear(generador, n_muestras)
        if distribucion_x0 is not None
        else np.full(n_muestras, float(x0))
    )
    y0_muestras = (
        distribucion_y0.muestrear(generador, n_muestras)
        if distribucion_y0 is not None
        else np.full(n_muestras, float(y0))
    )

    trayectorias: list[np.ndarray] = []
    exitosas: list[int] = []
    for indice in range(n_muestras):
        sustituciones = {
            simbolo: float(muestras_parametros[str(simbolo)][indice])
            for simbolo in simbolos
        }
        rhs_sustituido = sp.simplify(rhs.subs(sustituciones))
        if rhs_sustituido.free_symbols - {X, Y}:
            continue
        valores = _trayectoria(
            rhs_sustituido,
            float(x0_muestras[indice]),
            float(y0_muestras[indice]),
            x,
        )
        if valores is not None:
            trayectorias.append(valores)
            exitosas.append(indice)

    if len(trayectorias) < 5:
        raise SolucionNoDisponible(
            "Muy pocas trayectorias de Monte Carlo fueron exitosas; revisa las "
            "distribuciones o el intervalo."
        )
    matriz = np.vstack(trayectorias)
    alfa = (1.0 - nivel) / 2.0
    banda_inf = np.quantile(matriz, alfa, axis=0)
    banda_sup = np.quantile(matriz, 1.0 - alfa, axis=0)
    media = np.mean(matriz, axis=0)
    return ResultadoMonteCarlo(
        x=x,
        media=media,
        banda_inf=banda_inf,
        banda_sup=banda_sup,
        muestras=matriz,
        n_exitos=len(trayectorias),
        n_total=n_muestras,
        nivel=nivel,
        parametros={
            nombre: valores[np.asarray(exitosas)] for nombre, valores in muestras_parametros.items()
        },
        semilla=int(semilla),
        notas=[
            f"Bandas {100 * alfa:.1f}%–{100 * (1 - alfa):.1f}% con {len(trayectorias)} "
            f"de {n_muestras} trayectorias exitosas."
        ],
    )


def sobol_indices(
    rhs: sp.Expr,
    x0: float,
    y0: float,
    x_final: float,
    *,
    limites: dict[str, tuple[float, float]],
    n_muestras: int = 64,
    semilla: int = 42,
) -> ResultadoSobol:
    """Calcula índices de Sobol de primer orden y totales con SALib."""

    try:
        from SALib.analyze import sobol as analizar_sobol
        from SALib.sample import sobol as muestrear_sobol
    except Exception as exc:  # pragma: no cover - depende del entorno
        raise SolucionNoDisponible(
            "SALib no está instalado. Instala `SALib` para usar el análisis de Sobol."
        ) from exc

    simbolos = sorted(rhs.free_symbols - {X, Y}, key=lambda s: s.name)
    nombres = [str(s) for s in simbolos]
    if not nombres:
        raise EntradaInvalida("La EDO no tiene parámetros para analizar con Sobol.")
    faltantes = [nombre for nombre in nombres if nombre not in limites]
    if faltantes:
        raise EntradaInvalida(
            "Faltan límites para los parámetros: " + ", ".join(faltantes)
        )
    problem = {
        "num_vars": len(nombres),
        "names": nombres,
        "bounds": [list(limites[nombre]) for nombre in nombres],
    }
    N = max(int(n_muestras), 16)
    try:
        muestras = muestrear_sobol.sample(
            problem, N, calc_second_order=False, seed=int(semilla)
        )
    except TypeError:  # pragma: no cover - versiones antiguas de SALib
        np.random.seed(int(semilla))
        muestras = muestrear_sobol.sample(problem, N, calc_second_order=False)

    salidas = np.full(muestras.shape[0], np.nan, dtype=float)
    for indice, fila in enumerate(muestras):
        sustituciones = {
            simbolo: float(fila[pos]) for pos, simbolo in enumerate(simbolos)
        }
        rhs_sustituido = sp.simplify(rhs.subs(sustituciones))
        valores = _trayectoria(rhs_sustituido, float(x0), float(y0), np.asarray([x_final]))
        if valores is not None:
            salidas[indice] = float(valores[0])
    validas = np.isfinite(salidas)
    if np.sum(validas) < 16:
        raise SolucionNoDisponible(
            "Muy pocas evaluaciones de Sobol fueron exitosas; ajusta los límites "
            "o el intervalo."
        )
    if not np.all(validas):
        salidas[~validas] = float(np.mean(salidas[validas]))

    try:
        indices = analizar_sobol.analyze(
            problem,
            salidas,
            calc_second_order=False,
            seed=int(semilla),
            print_to_console=False,
        )
    except TypeError:  # pragma: no cover - versiones antiguas
        indices = analizar_sobol.analyze(
            problem, salidas, calc_second_order=False, print_to_console=False
        )
    return ResultadoSobol(
        nombres=nombres,
        S1=np.asarray(indices["S1"], dtype=float),
        ST=np.asarray(indices["ST"], dtype=float),
        S1_conf=np.asarray(indices["S1_conf"], dtype=float),
        ST_conf=np.asarray(indices["ST_conf"], dtype=float),
        N=N,
        semilla=int(semilla),
        salida_media=float(np.mean(salidas)),
        notas=[
            f"Se evaluó y({x_final:g}) con {muestras.shape[0]} muestras "
            f"(N = {N}, semilla = {semilla})."
        ],
    )


def distribuciones_por_defecto(rhs: sp.Expr) -> dict[str, Distribucion]:
    """Distribuciones razonables para los parámetros habituales de los modelos."""

    valores = {
        "r": (0.8, 0.15),
        "k": (0.1, 0.02),
        "K": (100.0, 10.0),
        "Tenv": (20.0, 2.0),
        "lambda": (0.1, 0.02),
        "R": (10.0, 1.0),
        "L": (1.0, 0.1),
        "V": (12.0, 0.5),
    }
    resultado: dict[str, Distribucion] = {}
    for simbolo in rhs.free_symbols - {X, Y}:
        nombre = str(simbolo)
        media, desviacion = valores.get(nombre, (1.0, 0.1))
        resultado[nombre] = Distribucion(
            nombre=nombre,
            tipo="normal",
            media=media,
            desviacion=desviacion,
        )
    return resultado


__all__ = [
    "Distribucion",
    "ResultadoMonteCarlo",
    "ResultadoSobol",
    "monte_carlo",
    "sobol_indices",
    "distribuciones_por_defecto",
]
