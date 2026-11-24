"""Análisis cualitativo de EDOs autónomas y familias parametrizadas."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import sympy as sp

from odecalc.symbols import X, Y

from core.tipos import (
    Equilibrio,
    PuntoBifurcacion,
    ResultadoSolucion,
)


@dataclass
class Isoclina:
    """Curvas ``f(x,y) = k`` de una isoclina."""

    valor: float
    curvas: list[tuple[np.ndarray, np.ndarray]] = field(default_factory=list)
    nota: str = ""


@dataclass
class DatosIsoclinas:
    """Malla y curvas para dibujar isoclinas."""

    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    valores: tuple[float, ...]
    curvas: list[Isoclina] = field(default_factory=list)
    nota: str = ""


@dataclass
class ComportamientoAsintotico:
    """Límite o tendencia cuando ``x → ∞``."""

    limite: float | None
    texto: str
    tipo: str = "indeterminado"


def es_autonoma(rhs: sp.Expr) -> bool:
    """``True`` si el lado derecho no depende de x."""

    return not rhs.has(X)


def _raices_reales(expr: sp.Expr) -> list[float]:
    raices: list[float] = []
    try:
        candidatas = sp.solve(sp.Eq(expr, 0), Y)
    except Exception:
        candidatas = []
    if not candidatas:
        try:
            polinomio = sp.Poly(expr, Y)
            candidatas = list(sp.nroots(polinomio))
        except Exception:
            candidatas = []
    for candidata in candidatas:
        try:
            valor = complex(sp.N(candidata))
        except Exception:
            continue
        if abs(valor.imag) > 1e-8 or not math.isfinite(valor.real):
            continue
        if not any(abs(valor.real - existente) < 1e-8 for existente in raices):
            raices.append(float(valor.real))
    raices.sort()
    return raices


def _estabilidad_en(rhs: sp.Expr, equilibrio: float) -> tuple[str, float | None, list[str]]:
    notas: list[str] = []
    try:
        derivada = sp.simplify(sp.diff(rhs, Y).subs(Y, equilibrio))
        valor = complex(sp.N(derivada))
    except Exception:
        derivada = sp.nan
        valor = complex(float("nan"))
    f_prima = float(valor.real) if abs(valor.imag) < 1e-8 and math.isfinite(valor.real) else None

    if f_prima is not None and f_prima < -1e-12:
        return "estable (atractor)", f_prima, notas
    if f_prima is not None and f_prima > 1e-12:
        return "inestable (repulsor)", f_prima, notas

    # f'(y*) = 0: se estudia el signo de f a ambos lados.
    epsilon = max(1e-3, 1e-3 * max(1.0, abs(equilibrio)))
    try:
        izquierda = float(sp.N(rhs.subs(Y, equilibrio - epsilon)))
        derecha = float(sp.N(rhs.subs(Y, equilibrio + epsilon)))
    except Exception:
        return "indeterminada", f_prima, ["No se pudo evaluar el signo de f."]
    if izquierda > 0 > derecha:
        return "estable (atractor)", f_prima, notas
    if izquierda < 0 < derecha:
        return "inestable (repulsor)", f_prima, notas
    if izquierda > 0 and derecha > 0:
        notas.append("f(y) > 0 a ambos lados: las trayectorias se alejan por la izquierda.")
        return "semiestable", f_prima, notas
    if izquierda < 0 and derecha < 0:
        notas.append("f(y) < 0 a ambos lados: las trayectorias se acercan por la izquierda.")
        return "semiestable", f_prima, notas
    return "indeterminada", f_prima, notas


def equilibrios(
    rhs: sp.Expr,
    *,
    y_min: float | None = None,
    y_max: float | None = None,
) -> list[Equilibrio]:
    """Equilibrios reales de ``y' = f(y)`` con su estabilidad."""

    if not es_autonoma(rhs):
        return []
    valores = _raices_reales(rhs)
    if y_min is not None:
        valores = [valor for valor in valores if valor >= y_min]
    if y_max is not None:
        valores = [valor for valor in valores if valor <= y_max]
    resultado: list[Equilibrio] = []
    for valor in valores:
        estabilidad, f_prima, notas = _estabilidad_en(rhs, valor)
        resultado.append(
            Equilibrio(
                valor=valor,
                estabilidad=estabilidad,
                f_prima=f_prima,
                notas=notas,
            )
        )
    return resultado


def linea_fase(
    rhs: sp.Expr,
    *,
    y_min: float = -3.0,
    y_max: float = 5.0,
    n: int = 400,
) -> dict[str, np.ndarray]:
    """Datos para dibujar la línea de fase 1D."""

    if not es_autonoma(rhs):
        raise ValueError("La línea de fase sólo está definida para EDOs autónomas.")
    f = sp.lambdify(Y, rhs, modules=["numpy"])
    ys = np.linspace(float(y_min), float(y_max), max(int(n), 2))
    with np.errstate(all="ignore"):
        valores = np.asarray(f(ys), dtype=float)
    if valores.shape != ys.shape:
        valores = np.broadcast_to(valores, ys.shape).astype(float)
    return {"y": ys, "f": valores}


def datos_isoclinas(
    rhs: sp.Expr,
    *,
    valores: tuple[float, ...] = (-1.0, 0.0, 1.0),
    x_min: float = -5.0,
    x_max: float = 5.0,
    y_min: float = -5.0,
    y_max: float = 5.0,
    n: int = 160,
) -> DatosIsoclinas:
    """Malla de ``f(x,y)`` y curvas ``f(x,y)=k`` cuando pueden despejarse."""

    xs = np.linspace(float(x_min), float(x_max), max(int(n), 2))
    ys = np.linspace(float(y_min), float(y_max), max(int(n), 2))
    xx, yy = np.meshgrid(xs, ys)
    try:
        f = sp.lambdify((X, Y), rhs, modules=["numpy"])
        with np.errstate(all="ignore"):
            zz = np.asarray(f(xx, yy), dtype=float)
    except Exception:
        zz = np.full_like(xx, np.nan)

    curvas: list[Isoclina] = []
    for valor in valores:
        isoclina = Isoclina(valor=float(valor))
        try:
            ramas = sp.solve(sp.Eq(rhs, valor), Y)
        except Exception:
            ramas = []
        for rama in ramas:
            if not isinstance(rama, sp.Expr) or rama.has(Y):
                continue
            if rama.free_symbols - {X}:
                continue
            try:
                funcion = sp.lambdify(X, rama, modules=["numpy"])
                with np.errstate(all="ignore"):
                    valores_y = np.asarray(funcion(xs), dtype=float)
                if valores_y.shape != xs.shape:
                    valores_y = np.broadcast_to(valores_y, xs.shape).astype(float)
                mascara = np.isfinite(valores_y)
                if np.any(mascara):
                    isoclina.curvas.append((xs[mascara], valores_y[mascara]))
            except Exception:
                continue
        if not isoclina.curvas:
            isoclina.nota = "No se pudo despejar y; usa las curvas de nivel."
        curvas.append(isoclina)

    return DatosIsoclinas(
        x=xs,
        y=ys,
        z=zz,
        valores=tuple(float(v) for v in valores),
        curvas=curvas,
        nota="Las isoclinas son las curvas de nivel f(x,y) = k.",
    )


def bifurcacion(
    rhs_param: sp.Expr,
    parametro: sp.Symbol,
    valores: np.ndarray | list[float],
) -> list[PuntoBifurcacion]:
    """Equilibrios y estabilidad para una familia ``y' = f(y; μ)``."""

    puntos: list[PuntoBifurcacion] = []
    for valor_mu in np.asarray(valores, dtype=float):
        try:
            rhs = sp.simplify(rhs_param.subs(parametro, float(valor_mu)))
            if rhs.has(parametro):
                continue
            for equilibrio in equilibrios(rhs):
                puntos.append(
                    PuntoBifurcacion(
                        parametro=float(valor_mu),
                        equilibrio=equilibrio.valor,
                        estabilidad=equilibrio.estabilidad,
                    )
                )
        except Exception:
            continue
    return puntos


def comportamiento_asintotico(resultado: ResultadoSolucion) -> ComportamientoAsintotico:
    """Calcula el límite ``x → ∞`` de la solución particular, con respaldo numérico."""

    solucion = resultado.solucion
    expresion = getattr(solucion, "expr", None)
    if expresion is not None and getattr(solucion, "is_explicit", False):
        if not (expresion.free_symbols - {X, Y}):
            try:
                limite = sp.limit(expresion, X, sp.oo)
                if limite in (sp.oo,):
                    return ComportamientoAsintotico(None, "Crece sin cota (→ +∞).", "divergente")
                if limite in (-sp.oo,):
                    return ComportamientoAsintotico(None, "Decrece sin cota (→ −∞).", "divergente")
                if limite.is_finite:
                    valor = float(sp.N(limite))
                    return ComportamientoAsintotico(valor, f"Tiende a {valor:.6g}.", "convergente")
                if limite in (sp.nan, sp.zoo) or limite.has(sp.AccumBounds):
                    pass
                else:
                    return ComportamientoAsintotico(None, f"Límite no concluyente: {sp.sstr(limite)}.", "indeterminado")
            except Exception:
                pass

    if resultado.numerico is not None and resultado.numerico.exito:
        y = np.asarray(resultado.numerico.y, dtype=float)
        if y.size >= 5:
            ultimos = y[-5:]
            if np.all(np.isfinite(ultimos)):
                pendiente = float(np.polyfit(np.arange(5), ultimos, 1)[0])
                if abs(pendiente) < 1e-3 * max(1.0, abs(float(np.mean(ultimos)))):
                    valor = float(np.mean(ultimos))
                    return ComportamientoAsintotico(
                        valor,
                        f"La curva numérica se estabiliza alrededor de {valor:.6g}.",
                        "convergente (numérico)",
                    )
                signo = "crece" if pendiente > 0 else "decrece"
                return ComportamientoAsintotico(
                    None,
                    f"La curva numérica {signo} al final del intervalo; no se observa límite finito.",
                    "divergente (numérico)",
                )
    return ComportamientoAsintotico(
        None,
        "No hay información suficiente para determinar el comportamiento asintótico.",
        "indeterminado",
    )


def resumen_cualitativo(rhs: sp.Expr) -> str:
    """Resumen breve para encabezados de la UI."""

    if not es_autonoma(rhs):
        return "EDO no autónoma: no hay equilibrios en el sentido y' = f(y)."
    puntos = equilibrios(rhs)
    if not puntos:
        return "EDO autónoma sin equilibrios reales."
    partes = [f"y = {p.valor:.6g} ({p.estabilidad})" for p in puntos]
    return "Equilibrios: " + "; ".join(partes) + "."


__all__ = [
    "Isoclina",
    "DatosIsoclinas",
    "ComportamientoAsintotico",
    "es_autonoma",
    "equilibrios",
    "linea_fase",
    "datos_isoclinas",
    "bifurcacion",
    "comportamiento_asintotico",
    "resumen_cualitativo",
]
