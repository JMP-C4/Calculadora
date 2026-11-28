"""Pestaña Numérico: comparación, convergencia, benchmark y rigidez."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import sympy as sp

from odecalc.symbols import X, lambdify_modules

from core.convergencia import benchmark, estudio_convergencia, validar_orden
from core.parser import parsear
from core.solver_numerico import (
    METODOS_PROPIOS,
    comparar_metodos,
    detectar_rigidez,
)
from core.tipos import EntradaInvalida

from ui.componentes import (
    aviso_parametros,
    lienzo,
    mensaje_error,
    mostrar_ecuacion,
    sin_resultado,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import figura_benchmark, figura_convergencia

_METODOS = ("Euler", "Heun", "RK4", "RK45", "DOP853", "BDF", "Radau")


def _exacto_actual() -> sp.Expr | None:
    resultado = st.session_state.get("resultado")
    if resultado is None:
        return None
    if resultado.ecuacion_texto != st.session_state.get("ecuacion_input"):
        return None
    solucion = getattr(resultado, "solucion", None)
    expresion = getattr(solucion, "expr", None)
    if expresion is None or not getattr(solucion, "is_explicit", False):
        return None
    if expresion.free_symbols - {X}:
        return None
    return expresion


def _figura_metodos(resultados, exacto: sp.Expr | None) -> go.Figure:
    figura = go.Figure()
    for indice, resultado in enumerate(resultados):
        if not resultado.exito or resultado.x.size == 0:
            continue
        figura.add_trace(
            go.Scatter(
                x=resultado.x,
                y=resultado.y,
                mode="lines",
                name=f"{resultado.metodo} ({resultado.puntos} pts)",
                line=dict(width=2 if resultado.metodo in METODOS_PROPIOS else 1.6),
            )
        )
    if exacto is not None:
        try:
            funcion = sp.lambdify(X, exacto, modules=lambdify_modules())
            xs = np.linspace(
                float(min(item.x[0] for item in resultados if item.exito)),
                float(max(item.x[-1] for item in resultados if item.exito)),
                500,
            )
            with np.errstate(all="ignore"):
                ys = np.asarray(funcion(xs), dtype=float)
            ys = np.broadcast_to(ys, xs.shape).astype(float)
            mascara = np.isfinite(ys)
            if np.any(mascara):
                figura.add_trace(
                    go.Scatter(
                        x=xs[mascara],
                        y=ys[mascara],
                        mode="lines",
                        name="solución exacta",
                        line=dict(color="#111827", width=2, dash="dash"),
                    )
                )
        except Exception:
            pass
    figura.update_layout(
        template="plotly_dark" if tema_actual() else "plotly_white",
        title="Trayectorias por método",
        xaxis_title="x",
        yaxis_title="y",
        height=430,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return figura


def _tabla_comparacion(resultados) -> None:
    filas = [
        {
            "Método": item.metodo,
            "Puntos": item.puntos,
            "Evaluaciones de f": item.f_evaluaciones,
            "Error máximo": "—" if item.error_max is None else f"{item.error_max:.3e}",
            "Rígido": "sí" if item.rigido else "no",
            "Éxito": "sí" if item.exito else "no",
            "Mensaje": item.mensaje,
        }
        for item in resultados
    ]
    st.dataframe(filas, use_container_width=True, hide_index=True)


def render(*, cabecera: bool = True) -> None:
    if cabecera:
        titulo_pagina(
            "Numérico",
            "Compara métodos, mide el orden empírico, ejecuta un benchmark y detecta rigidez.",
            icono="activity",
        )
    texto = st.session_state.get("ecuacion_input", "")
    if not texto.strip():
        sin_resultado()
        return
    try:
        ecuacion = parsear(texto)
    except EntradaInvalida as exc:
        if aviso_parametros(texto):
            return
        mensaje_error(str(exc))
        return
    x0 = float(st.session_state.get("x0_input", 0.0))
    y0 = float(st.session_state.get("y0_input", 1.0))
    x_min = float(st.session_state.get("x_min_input", 0.0))
    x_max = float(st.session_state.get("x_max_input", 5.0))

    with tarjeta("Problema de valor inicial", icono="pin"):
        mostrar_ecuacion(ecuacion.latex)
        st.caption(
            f"Condición inicial y({x0:g}) = {y0:g}. "
            f"Intervalo de referencia x ∈ [{x_min:g}, {x_max:g}]."
        )
        x_fin = st.number_input(
            "Integrar hasta x =",
            value=float(x_max if x_max > x0 else x0 + 1.0),
            key="num_x_fin",
        )
        if float(x_fin) <= x0:
            st.warning(
                "El extremo debe ser mayor que x₀ para integrar hacia adelante.",
                icon=None,
            )
            return
        h = st.slider(
            "Paso h para métodos de paso fijo",
            min_value=0.005,
            max_value=0.5,
            value=0.1,
            step=0.005,
            key="num_h",
        )
        metodos = st.multiselect(
            "Métodos",
            options=list(_METODOS),
            default=["Euler", "Heun", "RK4", "RK45"],
            key="num_metodos",
        )
        if not metodos:
            st.info("Elige al menos un método.", icon=None)
            return

    exacto = _exacto_actual()
    if exacto is None:
        st.caption(
            "No hay una expresión exacta explícita para este PVI; el error se "
            "medirá contra una referencia DOP853 de alta precisión."
        )

    columnas = st.columns(3)
    comparar = columnas[0].button("Comparar métodos", key="num_comparar", use_container_width=True)
    converger = columnas[1].button("Estudio de convergencia", key="num_converger", use_container_width=True)
    medir = columnas[2].button(
        "Benchmark y rigidez", key="num_benchmark_btn", use_container_width=True
    )

    if comparar:
        with st.spinner("Integrando con cada método…"):
            try:
                resultados = comparar_metodos(
                    ecuacion.rhs,
                    x0,
                    y0,
                    float(x_fin),
                    h=float(h),
                    exacto=exacto,
                    metodos=metodos,
                )
                st.session_state["num_resultados"] = resultados
            except Exception:
                mensaje_error(
                    "No se pudo completar la comparación.",
                    "Prueba un intervalo más corto o menos métodos.",
                )
    if converger:
        fijos = [metodo for metodo in metodos if metodo in METODOS_PROPIOS]
        if not fijos:
            fijos = ["Euler", "Heun", "RK4"]
        with st.spinner("Calculando error frente a h…"):
            try:
                resultado = estudio_convergencia(
                    ecuacion.rhs,
                    x0,
                    y0,
                    float(x_fin),
                    exacto=exacto,
                    metodos=fijos,
                )
                st.session_state["num_convergencia"] = resultado
            except Exception:
                mensaje_error(
                    "No se pudo completar el estudio de convergencia.",
                    "Asegúrate de que la solución no explote dentro del intervalo.",
                )
    if medir:
        with st.spinner("Midiendo tiempos, evaluaciones, errores y rigidez…"):
            try:
                items = benchmark(
                    ecuacion.rhs,
                    x0,
                    y0,
                    float(x_fin),
                    h=float(h),
                    exacto=exacto,
                    metodos=metodos,
                )
                st.session_state["num_benchmark"] = items
                rigidez = detectar_rigidez(ecuacion.rhs, x0, y0, float(x_fin))
                st.session_state["num_rigidez"] = rigidez
            except Exception:
                mensaje_error(
                    "No se pudo completar el benchmark.",
                    "Reduce el número de métodos o el intervalo.",
                )

    resultados = st.session_state.get("num_resultados")
    if resultados:
        st.markdown("#### Comparación de trayectorias")
        lienzo(_figura_metodos(resultados, exacto))
        _tabla_comparacion(resultados)
        errores = [item.error_max for item in resultados if item.error_max is not None]
        if errores:
            st.caption(
                f"Menor error máximo observado: {min(errores):.3e}. "
                "El error se calcula contra la solución exacta o la referencia."
            )

    convergencia = st.session_state.get("num_convergencia")
    if convergencia is not None:
        st.markdown("#### Orden empírico de convergencia")
        lienzo(
            figura_convergencia(
                convergencia.filas,
                convergencia.ordenes,
                tema_oscuro=tema_actual(),
            )
        )
        if convergencia.ordenes:
            columnas = st.columns(min(3, len(convergencia.ordenes)))
            for indice, (metodo, orden) in enumerate(sorted(convergencia.ordenes.items())):
                esperado = {"Euler": 1.0, "Heun": 2.0, "RK4": 4.0}.get(metodo)
                if esperado is not None:
                    valido = validar_orden(orden, esperado)
                    with columnas[indice % len(columnas)]:
                        st.metric(
                            metodo,
                            f"{orden:.3f}",
                            delta="dentro de lo esperado" if valido else "fuera del rango",
                            delta_color="normal" if valido else "inverse",
                        )
                else:
                    with columnas[indice % len(columnas)]:
                        st.metric(metodo, f"{orden:.3f}")
        filas = [
            {
                "Método": fila.metodo,
                "h": fila.h,
                "Error máximo": fila.error_max,
                "Puntos": fila.puntos,
            }
            for fila in convergencia.filas
        ]
        with st.expander("Ver tabla de convergencia", expanded=False):
            st.dataframe(filas, use_container_width=True, hide_index=True)
        for nota in convergencia.notas:
            st.caption(nota)

    items = st.session_state.get("num_benchmark")
    if items:
        st.markdown("#### Benchmark en vivo")
        lienzo(figura_benchmark(items, tema_oscuro=tema_actual()))
        st.dataframe(
            [
                {
                    "Método": item.metodo,
                    "Tiempo (ms)": f"{item.tiempo_ms:.2f}",
                    "Evaluaciones de f": item.f_evaluaciones,
                    "Pasos": item.pasos,
                    "Error máximo": "—" if item.error_max is None else f"{item.error_max:.3e}",
                    "Éxito": "sí" if item.exito else "no",
                }
                for item in items
            ],
            use_container_width=True,
            hide_index=True,
        )

    rigidez = st.session_state.get("num_rigidez")
    if rigidez is not None:
        st.markdown("#### Diagnóstico de rigidez")
        if rigidez.rigida:
            st.warning(
                rigidez.motivo + f" Método recomendado: {rigidez.metodo_recomendado}.",
                icon=None,
            )
        else:
            st.success(rigidez.motivo, icon=None)
        columnas = st.columns(2)
        columnas[0].metric(
            "|∂f/∂y| máximo",
            "—" if rigidez.jacobiano_max is None else f"{rigidez.jacobiano_max:.3e}",
        )
        columnas[1].metric(
            "Evaluaciones RK45",
            "—" if rigidez.nfev_rk45 is None else str(rigidez.nfev_rk45),
        )


__all__ = ["render"]
