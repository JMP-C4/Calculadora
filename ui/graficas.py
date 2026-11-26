"""Gráficas Plotly compartidas por las pestañas de EDO-Lab."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import plotly.graph_objects as go
import sympy as sp
from plotly.subplots import make_subplots

from odecalc.plotting import singular_curves, tangency_points
from odecalc.symbols import X, Y

_COLORES = (
    "#2563eb",
    "#dc2626",
    "#059669",
    "#d97706",
    "#7c3aed",
    "#0891b2",
)

#: Modos compartidos por el selector de la cabecera y el lienzo.
GRAFICAS = (
    "Solución y(x)",
    "Campo de direcciones",
    "Isoclinas",
    "Familia de curvas",
    "Línea de fase",
    "Puntos de equilibrio",
    "Superficie 3D z = f(x,y)",
)
CLAVE_GRAFICA = "edo_grafica_activa"


def _plantilla(tema_oscuro: bool = False) -> str:
    return "plotly_dark" if tema_oscuro else "plotly_white"


def _acabado(
    figura: go.Figure,
    *,
    titulo: str = "",
    x_titulo: str = "x",
    y_titulo: str = "y",
    altura: int = 420,
    tema_oscuro: bool = False,
) -> go.Figure:
    figura.update_layout(
        template=_plantilla(tema_oscuro),
        title=titulo,
        xaxis_title=x_titulo,
        yaxis_title=y_titulo,
        height=altura,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return figura


def _rhs_funcion(rhs: sp.Expr):
    return sp.lambdify((X, Y), rhs, modules=["numpy"])


def _rango_x(resultado) -> tuple[float, float]:
    """Intervalo horizontal del resultado, con respaldo seguro."""

    intervalo = getattr(resultado, "intervalo", None)
    if intervalo is not None and len(intervalo) == 2:
        try:
            x_min, x_max = float(intervalo[0]), float(intervalo[1])
            if x_min < x_max:
                return x_min, x_max
        except (TypeError, ValueError):
            pass
    return -5.0, 5.0


def _anadir_singular(
    figura: go.Figure, resultado, *, x_min: float, x_max: float
) -> bool:
    """Superpone la envolvente singular y el punto de tangencia de la particular."""

    motor = getattr(resultado, "resultado_motor", None) or resultado
    curvas = singular_curves(motor, x_min=x_min, x_max=x_max)
    for curva in curvas:
        figura.add_trace(
            go.Scatter(
                x=curva["x"],
                y=curva["y"],
                mode="lines",
                name=curva["label"],
                line=dict(color="#7c3aed", width=3.2, dash="dash"),
                legendgroup="envolvente",
            )
        )
    for punto in tangency_points(motor, x_min=x_min, x_max=x_max):
        figura.add_trace(
            go.Scatter(
                x=[punto["x"]],
                y=[punto["y"]],
                mode="markers+text",
                text=[punto["label"]],
                textposition="top center",
                name="Tangencia",
                marker=dict(color="#b45309", size=12, symbol="diamond"),
            )
        )
    return bool(curvas)


def figura_solucion(
    resultado,
    *,
    curvas_extra: Iterable[tuple[np.ndarray, np.ndarray, str]] | None = None,
    tema_oscuro: bool = False,
    altura: int = 430,
) -> go.Figure:
    """Curva de la solución certificada y curvas adicionales."""

    from core.hibrido import curva_solucion

    figura = go.Figure()
    curva = curva_solucion(resultado, n_points=700)
    if curva is not None:
        xs, ys = curva
        figura.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name="Solución",
                line=dict(color=_COLORES[0], width=2.6),
            )
        )
    if resultado.x0 is not None and resultado.y0 is not None:
        figura.add_trace(
            go.Scatter(
                x=[resultado.x0],
                y=[resultado.y0],
                mode="markers",
                name="Condición inicial",
                marker=dict(color=_COLORES[1], size=10, symbol="circle"),
            )
        )
    x_min, x_max = _rango_x(resultado)
    _anadir_singular(figura, resultado, x_min=x_min, x_max=x_max)
    for indice, (xs, ys, etiqueta) in enumerate(curvas_extra or (), start=2):
        figura.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=etiqueta,
                line=dict(color=_COLORES[indice % len(_COLORES)], width=1.8, dash="dot"),
            )
        )
    return _acabado(figura, titulo="Curva solución", tema_oscuro=tema_oscuro, altura=altura)


def figura_campo_direcciones(
    rhs: sp.Expr,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    *,
    n: int = 21,
    seleccionable: bool = False,
    tema_oscuro: bool = False,
    altura: int = 430,
    titulo: str = "Campo de direcciones",
) -> go.Figure:
    """Campo de pendientes con puntos invisibles para el clic."""

    figura = go.Figure()
    if x_min >= x_max or y_min >= y_max:
        return _acabado(figura, titulo=titulo, tema_oscuro=tema_oscuro, altura=altura)
    xs = np.linspace(float(x_min), float(x_max), max(int(n), 5))
    ys = np.linspace(float(y_min), float(y_max), max(int(n), 5))
    xx, yy = np.meshgrid(xs, ys)
    try:
        funcion = _rhs_funcion(rhs)
        with np.errstate(all="ignore"):
            pendientes = np.asarray(funcion(xx, yy), dtype=float)
        pendientes = np.broadcast_to(pendientes, xx.shape).astype(float)
    except Exception:
        pendientes = np.full_like(xx, np.nan)
    mascara = np.isfinite(pendientes)
    if not np.any(mascara):
        return _acabado(figura, titulo=titulo, tema_oscuro=tema_oscuro, altura=altura)

    paso_x = 0.78 * (float(x_max) - float(x_min)) / max(len(xs) - 1, 1)
    paso_y = 0.78 * (float(y_max) - float(y_min)) / max(len(ys) - 1, 1)
    norm = np.sqrt(1.0 + pendientes**2)
    ux = paso_x / norm
    uy = pendientes * ux
    escala = np.minimum(1.0, paso_y / np.maximum(np.abs(uy), 1e-12))
    ux = ux * escala
    uy = uy * escala

    x0 = xx[mascara]
    y0 = yy[mascara]
    vx = ux[mascara]
    vy = uy[mascara]
    x1, y1 = x0 + vx, y0 + vy

    sx: list[float | None] = []
    sy: list[float | None] = []
    for ax, ay, bx, by in zip(x0, y0, x1, y1):
        sx.extend([float(ax), float(bx), None])
        sy.extend([float(ay), float(by), None])
    figura.add_trace(
        go.Scatter(
            x=sx,
            y=sy,
            mode="lines",
            line=dict(color="rgba(100,116,139,.6)" if not tema_oscuro else "rgba(203,213,225,.55)", width=1),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    # Cabeza de flecha: dos segmentos cortos hacia atrás.
    hx: list[float | None] = []
    hy: list[float | None] = []
    for ax, ay, bx, by in zip(x0, y0, x1, y1):
        dx, dy = bx - ax, by - ay
        hx.extend([float(bx), float(bx - 0.35 * dx + 0.18 * dy), None])
        hy.extend([float(by), float(by - 0.35 * dy - 0.18 * dx), None])
        hx.extend([float(bx), float(bx - 0.35 * dx - 0.18 * dy), None])
        hy.extend([float(by), float(by - 0.35 * dy + 0.18 * dx), None])
    figura.add_trace(
        go.Scatter(
            x=hx,
            y=hy,
            mode="lines",
            line=dict(color="rgba(100,116,139,.75)" if not tema_oscuro else "rgba(203,213,225,.7)", width=1),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    if seleccionable:
        figura.add_trace(
            go.Scatter(
                x=xx.ravel(),
                y=yy.ravel(),
                mode="markers",
                marker=dict(size=9, color="#2563eb", opacity=0.012),
                name="Puntos para clic",
                showlegend=False,
                hovertemplate="x = %{x:.3f}<br>y = %{y:.3f}<extra></extra>",
            )
        )
    figura.update_xaxes(range=[x_min, x_max])
    figura.update_yaxes(range=[y_min, y_max])
    return _acabado(figura, titulo=titulo, tema_oscuro=tema_oscuro, altura=altura)


def figura_fase(
    rhs: sp.Expr,
    equilibrios: Iterable[Any],
    *,
    y_min: float = -3.0,
    y_max: float = 5.0,
    tema_oscuro: bool = False,
    altura: int = 360,
) -> go.Figure:
    """Gráfica f(y) con equilibrios marcados."""

    figura = go.Figure()
    ys = np.linspace(float(y_min), float(y_max), 500)
    try:
        funcion = sp.lambdify(Y, rhs, modules=["numpy"])
        with np.errstate(all="ignore"):
            valores = np.asarray(funcion(ys), dtype=float)
        valores = np.broadcast_to(valores, ys.shape).astype(float)
        figura.add_trace(
            go.Scatter(
                x=ys,
                y=valores,
                mode="lines",
                name="f(y)",
                line=dict(color=_COLORES[0], width=2.4),
            )
        )
        figura.add_trace(
            go.Scatter(
                x=[y_min, y_max],
                y=[0, 0],
                mode="lines",
                name="f(y) = 0",
                line=dict(color="#94a3b8", width=1, dash="dash"),
                hoverinfo="skip",
            )
        )
    except Exception:
        pass
    for equilibrio in equilibrios:
        estable = equilibrio.estabilidad.startswith("estable")
        inestable = equilibrio.estabilidad.startswith("inestable")
        color = "#059669" if estable else ("#dc2626" if inestable else "#d97706")
        figura.add_trace(
            go.Scatter(
                x=[equilibrio.valor],
                y=[0],
                mode="markers+text",
                text=[f"y*={equilibrio.valor:.4g}"],
                textposition="top center",
                name=equilibrio.estabilidad,
                marker=dict(color=color, size=12, symbol="diamond"),
            )
        )
    return _acabado(
        figura,
        titulo="Línea de fase: f(y) frente a y",
        x_titulo="y",
        y_titulo="f(y)",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_isoclinas(datos, *, tema_oscuro: bool = False, altura: int = 420) -> go.Figure:
    """Curvas de nivel y ramas explícitas de las isóclinas."""

    figura = go.Figure()
    try:
        figura.add_trace(
            go.Contour(
                x=datos.x,
                y=datos.y,
                z=datos.z,
                colorscale="RdBu",
                opacity=0.35,
                showscale=False,
                hoverinfo="skip",
            )
        )
    except Exception:
        pass
    for indice, isoclina in enumerate(datos.curvas):
        for rama, (xs, ys) in enumerate(isoclina.curvas):
            figura.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    name=f"f = {isoclina.valor:g}",
                    legendgroup=f"iso-{indice}",
                    showlegend=rama == 0,
                    line=dict(
                        color=_COLORES[indice % len(_COLORES)],
                        width=2,
                    ),
                )
            )
    figura.update_xaxes(range=[float(datos.x[0]), float(datos.x[-1])])
    figura.update_yaxes(range=[float(datos.y[0]), float(datos.y[-1])])
    return _acabado(
        figura,
        titulo="Isóclinas: f(x, y) = k",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_bifurcacion(puntos: Iterable[Any], *, tema_oscuro: bool = False, altura: int = 420) -> go.Figure:
    """Diagrama de bifurcación con estabilidad por color."""

    figura = go.Figure()
    grupos = {
        "estable": ("#059669", "Estable"),
        "inestable": ("#dc2626", "Inestable"),
        "semiestable": ("#d97706", "Semiestable"),
        "indeterminada": ("#64748b", "Indeterminada"),
    }
    por_grupo: dict[str, list[Any]] = {clave: [] for clave in grupos}
    for punto in puntos:
        clave = next(
            (nombre for nombre in grupos if punto.estabilidad.startswith(nombre)),
            "indeterminada",
        )
        por_grupo[clave].append(punto)
    for clave, (color, etiqueta) in grupos.items():
        lista = sorted(por_grupo[clave], key=lambda item: item.parametro)
        if not lista:
            continue
        figura.add_trace(
            go.Scatter(
                x=[item.parametro for item in lista],
                y=[item.equilibrio for item in lista],
                mode="lines+markers",
                name=etiqueta,
                line=dict(color=color, width=1.6),
                marker=dict(color=color, size=7),
            )
        )
    return _acabado(
        figura,
        titulo="Diagrama de bifurcación",
        x_titulo="parámetro μ",
        y_titulo="equilibrio y*",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_convergencia(filas: Iterable[Any], ordenes: dict[str, float], *, tema_oscuro: bool = False, altura: int = 420) -> go.Figure:
    """Error máximo frente a h en escala log-log."""

    figura = go.Figure()
    por_metodo: dict[str, list[Any]] = {}
    for fila in filas:
        por_metodo.setdefault(fila.metodo, []).append(fila)
    for indice, (metodo, lista) in enumerate(sorted(por_metodo.items())):
        lista = sorted(lista, key=lambda item: item.h)
        hs = np.asarray([item.h for item in lista], dtype=float)
        errores = np.asarray([item.error_max for item in lista], dtype=float)
        orden = ordenes.get(metodo)
        etiqueta = metodo if orden is None else f"{metodo} (orden ≈ {orden:.2f})"
        figura.add_trace(
            go.Scatter(
                x=hs,
                y=errores,
                mode="markers+lines",
                name=etiqueta,
                line=dict(color=_COLORES[indice % len(_COLORES)], width=1.8),
                marker=dict(size=8),
            )
        )
        validos = (hs > 0) & (errores > 0)
        if np.sum(validos) >= 2:
            pendiente, intercepto = np.polyfit(
                np.log(hs[validos]), np.log(errores[validos]), 1
            )
            ajuste = np.exp(intercepto) * hs[validos] ** pendiente
            figura.add_trace(
                go.Scatter(
                    x=hs[validos],
                    y=ajuste,
                    mode="lines",
                    name=f"ajuste {metodo}",
                    line=dict(
                        color=_COLORES[indice % len(_COLORES)],
                        width=1,
                        dash="dot",
                    ),
                    showlegend=False,
                )
            )
    figura.update_xaxes(type="log", title="paso h")
    figura.update_yaxes(type="log", title="error máximo")
    return _acabado(
        figura,
        titulo="Convergencia: error frente a h",
        x_titulo="paso h",
        y_titulo="error máximo",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_benchmark(items: Iterable[Any], *, tema_oscuro: bool = False, altura: int = 420) -> go.Figure:
    """Tiempo y error por método en un gráfico de doble eje."""

    items = list(items)
    figura = make_subplots(specs=[[{"secondary_y": True}]])
    nombres = [item.metodo for item in items]
    figura.add_trace(
        go.Bar(
            x=nombres,
            y=[item.tiempo_ms for item in items],
            name="tiempo (ms)",
            marker_color=_COLORES[0],
            opacity=0.8,
        ),
        secondary_y=False,
    )
    figura.add_trace(
        go.Scatter(
            x=nombres,
            y=[
                item.error_max if item.error_max is not None else np.nan
                for item in items
            ],
            mode="markers+lines",
            name="error máximo",
            marker=dict(color=_COLORES[1], size=9),
            line=dict(color=_COLORES[1], width=1.5),
        ),
        secondary_y=True,
    )
    figura.update_yaxes(title_text="tiempo (ms)", secondary_y=False)
    figura.update_yaxes(title_text="error máximo", secondary_y=True, type="log")
    figura.update_layout(
        template=_plantilla(tema_oscuro),
        title="Benchmark de métodos",
        height=altura,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return figura


def _curva_modelo(modelo: Any, parametros: dict[str, float], y0: float, xs: np.ndarray) -> np.ndarray | None:
    from scipy.integrate import solve_ivp

    try:
        def f(t: float, estado: np.ndarray) -> list[float]:
            return [modelo.evaluar(t, float(estado[0]), parametros)]

        solucion = solve_ivp(
            f,
            (float(xs[0]), float(xs[-1])),
            [float(y0)],
            t_eval=xs,
            method="RK45",
            rtol=1e-7,
            atol=1e-9,
        )
    except Exception:
        return None
    if not solucion.success or solucion.y.shape[1] != xs.size:
        return None
    valores = np.asarray(solucion.y[0], dtype=float)
    return valores if np.all(np.isfinite(valores)) else None


def figura_ajuste(
    datos,
    resultados: Iterable[Any],
    *,
    prediccion: Any | None = None,
    tema_oscuro: bool = False,
    altura: int = 440,
) -> go.Figure:
    """Datos observados, curvas ajustadas y banda de predicción."""

    from core.ajuste import MODELOS

    figura = go.Figure()
    figura.add_trace(
        go.Scatter(
            x=datos.x,
            y=datos.y,
            mode="markers",
            name="datos",
            marker=dict(color="#111827" if not tema_oscuro else "#e2e8f0", size=7),
        )
    )
    fin = float(prediccion.x[-1]) if prediccion is not None else float(datos.x[-1])
    xs = np.linspace(float(datos.x[0]), fin, 240)
    for indice, resultado in enumerate(resultados):
        if not resultado.exito:
            continue
        modelo = MODELOS.get(resultado.modelo)
        if modelo is None:
            continue
        valores = _curva_modelo(modelo, resultado.parametros_simples, resultado.y0, xs)
        if valores is None:
            continue
        figura.add_trace(
            go.Scatter(
                x=xs,
                y=valores,
                mode="lines",
                name=resultado.nombre,
                line=dict(color=_COLORES[indice % len(_COLORES)], width=2),
            )
        )
    if prediccion is not None:
        figura.add_trace(
            go.Scatter(
                x=prediccion.x,
                y=prediccion.ic_sup,
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figura.add_trace(
            go.Scatter(
                x=prediccion.x,
                y=prediccion.ic_inf,
                mode="lines",
                fill="tonexty",
                fillcolor="rgba(37,99,235,.18)",
                line=dict(width=0),
                name=f"banda {int(prediccion.nivel * 100)}%",
                hoverinfo="skip",
            )
        )
        figura.add_trace(
            go.Scatter(
                x=prediccion.x,
                y=prediccion.y,
                mode="lines",
                name="predicción",
                line=dict(color=_COLORES[0], width=2.2, dash="dash"),
            )
        )
    return _acabado(
        figura,
        titulo="Ajuste de modelos a los datos",
        x_titulo=datos.nombres[0],
        y_titulo=datos.nombres[1],
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_monte_carlo(resultado, *, tema_oscuro: bool = False, altura: int = 430) -> go.Figure:
    """Bandas de predicción y trayectorias muestreadas."""

    figura = go.Figure()
    muestras = np.asarray(resultado.muestras, dtype=float)
    if muestras.ndim == 2:
        for indice in range(min(18, muestras.shape[0])):
            figura.add_trace(
                go.Scatter(
                    x=resultado.x,
                    y=muestras[indice],
                    mode="lines",
                    line=dict(color="rgba(148,163,184,.35)", width=1),
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
    figura.add_trace(
        go.Scatter(
            x=resultado.x,
            y=resultado.banda_sup,
            mode="lines",
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    figura.add_trace(
        go.Scatter(
            x=resultado.x,
            y=resultado.banda_inf,
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(37,99,235,.20)",
            line=dict(width=0),
            name=f"banda {int(resultado.nivel * 100)}%",
            hoverinfo="skip",
        )
    )
    figura.add_trace(
        go.Scatter(
            x=resultado.x,
            y=resultado.media,
            mode="lines",
            name="media",
            line=dict(color=_COLORES[0], width=2.6),
        )
    )
    return _acabado(
        figura,
        titulo="Monte Carlo: bandas de predicción",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_sobol(resultado, *, tema_oscuro: bool = False, altura: int = 400) -> go.Figure:
    """Barras agrupadas de índices de Sobol de primer orden y total."""

    figura = go.Figure()
    figura.add_trace(
        go.Bar(
            x=resultado.nombres,
            y=resultado.S1,
            name="primer orden (S1)",
            marker_color=_COLORES[0],
            error_y=dict(type="data", array=resultado.S1_conf, visible=True),
        )
    )
    figura.add_trace(
        go.Bar(
            x=resultado.nombres,
            y=resultado.ST,
            name="total (ST)",
            marker_color=_COLORES[4],
            error_y=dict(type="data", array=resultado.ST_conf, visible=True),
        )
    )
    figura.update_layout(barmode="group")
    return _acabado(
        figura,
        titulo="Sensibilidad global (Sobol)",
        x_titulo="parámetro",
        y_titulo="índice",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_sensibilidad(sensibilidad: dict[str, float], *, tema_oscuro: bool = False, altura: int = 360) -> go.Figure:
    """Barras horizontales de sensibilidad local."""

    figura = go.Figure(
        go.Bar(
            x=list(sensibilidad.values()),
            y=list(sensibilidad.keys()),
            orientation="h",
            marker_color=_COLORES[2],
        )
    )
    return _acabado(
        figura,
        titulo="Sensibilidad local de y(x_final)",
        x_titulo="elasticidad relativa",
        y_titulo="parámetro",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_familia(
    curvas: Iterable[tuple[np.ndarray, np.ndarray, str]],
    *,
    resultado=None,
    tema_oscuro: bool = False,
    altura: int = 430,
) -> go.Figure:
    """Familia de soluciones al variar la constante de integración."""

    figura = go.Figure()
    for indice, (xs, ys, etiqueta) in enumerate(curvas):
        figura.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                name=etiqueta,
                line=dict(
                    color=_COLORES[indice % len(_COLORES)],
                    width=2.0,
                ),
            )
        )
    if resultado is not None:
        x_min, x_max = _rango_x(resultado)
        _anadir_singular(figura, resultado, x_min=x_min, x_max=x_max)
    return _acabado(
        figura,
        titulo="Familia de curvas solución",
        tema_oscuro=tema_oscuro,
        altura=altura,
    )


def figura_superficie(
    datos,
    *,
    tema_oscuro: bool = False,
    altura: int = 460,
) -> go.Figure:
    """Superficie ``z = f(x, y)`` a partir de la malla de isóclinas."""

    figura = go.Figure(
        go.Surface(
            x=datos.x,
            y=datos.y,
            z=datos.z,
            colorscale="RdBu",
            opacity=0.92,
            showscale=False,
        )
    )
    figura.update_layout(
        template=_plantilla(tema_oscuro),
        title="Superficie z = f(x, y)",
        height=altura,
        margin=dict(l=0, r=0, t=50, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis_title="x",
            yaxis_title="y",
            zaxis_title="z = f(x, y)",
        ),
    )
    return figura


__all__ = [
    "CLAVE_GRAFICA",
    "GRAFICAS",
    "figura_solucion",
    "figura_campo_direcciones",
    "figura_fase",
    "figura_isoclinas",
    "figura_familia",
    "figura_superficie",
    "figura_bifurcacion",
    "figura_convergencia",
    "figura_benchmark",
    "figura_ajuste",
    "figura_monte_carlo",
    "figura_sobol",
    "figura_sensibilidad",
]
