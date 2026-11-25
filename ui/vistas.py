"""Composición de las cinco vistas principales de EDO-Lab."""

from __future__ import annotations

import streamlit as st

from core.notacion import formatear_texto

from ui.componentes import (
    mostrar_texto,
    notacion_actual,
    sin_resultado,
    tarjeta,
    teclado_ayuda,
    titulo_pagina,
)
from ui.navegacion import establecer_vista
from ui.pagina_aprendizaje import render as render_aprendizaje
from ui.pagina_informes import render as render_informes
from ui.pagina_resolver import (
    render_calculadora,
    render_pasos,
    render_salida,
    render_visualizacion,
)


def _historial() -> None:
    historial = st.session_state.get("historial", [])
    with tarjeta("Cálculos recientes", icono="history"):
        if not historial:
            sin_resultado()
            return
        for indice, entrada in enumerate(historial):
            ecuacion = str(entrada.get("ecuacion", ""))
            x0 = entrada.get("x0")
            y0 = entrada.get("y0")
            condicion = (
                f"y({x0:g}) = {y0:g}"
                if isinstance(x0, (int, float)) and isinstance(y0, (int, float))
                else "sin condición inicial"
            )
            with st.container(border=True):
                st.caption(formatear_texto(ecuacion, notacion_actual()))
                st.caption(
                    f"{condicion} · {entrada.get('tipo', '—')} · "
                    f"camino: {entrada.get('camino', '—')}"
                )
                st.button(
                    "Abrir en la calculadora",
                    key=f"historial_abrir_{indice}",
                    on_click=_cargar_historial,
                    args=(entrada,),
                )
    if st.button("Borrar historial", key="historial_borrar"):
        st.session_state["historial"] = []
        st.rerun()


def _cargar_historial(entrada: dict) -> None:
    st.session_state["_cargar_ecuacion"] = {
        "ecuacion": entrada.get("ecuacion", ""),
        "x0": entrada.get("x0", 0.0),
        "y0": entrada.get("y0", 1.0),
        "x_min": entrada.get("x_min", 0.0),
        "x_max": entrada.get("x_max", 5.0),
    }
    st.session_state["_solicitar_resolver"] = True
    establecer_vista("Calculadora")


def _teoria() -> None:
    bloques = (
        (
            "Ecuaciones de primer orden",
            """
Una EDO de primer orden se escribe $y' = f(x, y)$. La solución es una función
$y(x)$ cuya pendiente en cada punto coincide con $f(x, y)$. Cuando además se
da $y(x₀) = y₀$, se busca la curva concreta que pasa por ese punto.
            """,
        ),
        (
            "Existencia y unicidad",
            r"""
Si $f$ y $\partial f/\partial y$ son continuas alrededor del punto inicial, el
teorema de Picard–Lindelöf garantiza una solución local única. Si
$\partial f/\partial y$ no es continua o $f$ no es Lipschitz, pueden existir
varias soluciones, como ocurre en $y' = y^{1/3}$ con $y(0) = 0$.
            """,
        ),
        (
            "Cómo leer el certificado",
            """
El certificado indica si la solución se verificó simbólicamente (sustitución
exacta en la EDO), numéricamente (residuo pequeño en el intervalo) o si no
pudo verificarse. El residuo máximo y el dominio declarado son parte del
resultado, no un adorno.
            """,
        ),
        (
            "Métodos numéricos",
            """
Euler y Heun son de uno y dos órdenes; RK4 es de cuarto orden. RK45 y DOP853
adaptan el paso y son buenas opciones generales. BDF y Radau son adecuados
para problemas rígidos. La pestaña Numérico compara trayectorias, errores y
tiempos para la misma EDO.
            """,
        ),
        (
            "Lectura cualitativa",
            """
El campo de direcciones muestra la pendiente en cada punto. Las isóclinas
unen puntos con la misma pendiente. En ecuaciones autónomas $y' = f(y)$, los
equilibrios $f(y^*) = 0$ y la línea de fase explican el comportamiento a largo
plazo sin necesidad de una fórmula cerrada.
            """,
        ),
    )
    for titulo, texto in bloques:
        with st.expander(titulo, expanded=False):
            mostrar_texto(texto)
    with st.expander("Sintaxis de la calculadora", expanded=False):
        teclado_ayuda()


def render_historial() -> None:
    """Vista con historial, fundamentos, ejercicios e informes."""

    titulo_pagina(
        "Historial y teoría",
        "Recupera cálculos anteriores, repasa conceptos y exporta informes.",
        icono="book",
    )
    pestanas = st.tabs(["Historial", "Teoría", "Aprender", "Informes"])
    with pestanas[0]:
        _historial()
    with pestanas[1]:
        _teoria()
    with pestanas[2]:
        render_aprendizaje(cabecera=False)
    with pestanas[3]:
        render_informes(cabecera=False)


def despachar(vista: str) -> None:
    """Renderiza la vista indicada por la navegación principal."""

    if vista == "Salida":
        render_salida()
    elif vista == "Visualización":
        render_visualizacion()
    elif vista == "Paso a paso":
        render_pasos()
    elif vista == "Historial y teoría":
        render_historial()
    else:
        render_calculadora()


def pie() -> None:
    st.markdown(
        '<div class="edo-pie">EDO-Lab · motor determinista · '
        "gráficas interactivas con zoom y paneo · "
        "los resultados se recalculan sólo cuando lo pides.</div>",
        unsafe_allow_html=True,
    )


__all__ = ["despachar", "pie", "render_historial"]
