"""Pestaña Cualitativo: equilibrios, fase, isóclinas y bifurcaciones."""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.cualitativo import (
    bifurcacion,
    comportamiento_asintotico,
    datos_isoclinas,
    equilibrios,
    es_autonoma,
    resumen_cualitativo,
)
from core.parser import parsear, parsear_parametrizada
from core.tipos import EntradaInvalida

from ui.componentes import (
    aviso_parametros,
    bloque_scroll,
    mensaje_error,
    mostrar_existencia,
    sin_resultado,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import figura_bifurcacion, figura_fase, figura_isoclinas


def _tabla_equilibrios(puntos) -> None:
    if not puntos:
        st.info("No se encontraron equilibrios reales en el rango elegido.")
        return
    filas = [
        {
            "y*": f"{punto.valor:.6g}",
            "Estabilidad": punto.estabilidad,
            "f'(y*)": "—" if punto.f_prima is None else f"{punto.f_prima:.6g}",
            "Notas": " ".join(punto.notas) if punto.notas else "—",
        }
        for punto in puntos
    ]
    st.dataframe(filas, use_container_width=True, hide_index=True)


def _seccion_equilibrios(rhs) -> None:
    st.markdown("#### ⚖️ Equilibrios y estabilidad")
    columnas = st.columns(2)
    y_min = columnas[0].number_input(
        "y mínimo para buscar equilibrios", value=-5.0, key="cual_y_min"
    )
    y_max = columnas[1].number_input(
        "y máximo para buscar equilibrios", value=10.0, key="cual_y_max"
    )
    if y_min >= y_max:
        st.warning("El rango de y no es válido: el mínimo debe ser menor que el máximo.")
        return
    puntos = equilibrios(rhs, y_min=float(y_min), y_max=float(y_max))
    st.caption(resumen_cualitativo(rhs))
    _tabla_equilibrios(puntos)
    figura = figura_fase(
        rhs,
        puntos,
        y_min=float(y_min),
        y_max=float(y_max),
        tema_oscuro=tema_actual(),
    )
    st.plotly_chart(figura, use_container_width=True)
    st.caption(
        "🟢 estable: las trayectorias se acercan. 🔴 inestable: se alejan. "
        "🟡 semiestable o indeterminado."
    )


def _seccion_isoclinas(rhs, x_min: float, x_max: float) -> None:
    st.markdown("#### 🗺️ Isóclinas")
    valores = st.multiselect(
        "Valores de k para las isóclinas f(x, y) = k",
        options=[-2.0, -1.0, -0.5, 0.0, 0.5, 1.0, 2.0],
        default=[-1.0, 0.0, 1.0],
        key="cual_isoclinas",
    )
    if not valores:
        st.info("Elige al menos un valor para dibujar isóclinas.")
        return
    if x_min >= x_max:
        st.warning("El intervalo de x no es válido.")
        return
    with st.spinner("Calculando isóclinas…"):
        try:
            datos = datos_isoclinas(
                rhs,
                valores=tuple(float(valor) for valor in valores),
                x_min=float(x_min),
                x_max=float(x_max),
                y_min=-6.0,
                y_max=6.0,
            )
        except Exception:
            mensaje_error(
                "No se pudieron calcular las isóclinas.",
                "Prueba con otros valores de k o revisa la ecuación.",
            )
            return
    st.plotly_chart(
        figura_isoclinas(datos, tema_oscuro=tema_actual()),
        use_container_width=True,
    )
    st.caption(datos.nota)


def _seccion_bifurcacion() -> None:
    st.markdown("#### 🌀 Bifurcación con un parámetro")
    st.caption(
        "Estudia una familia y' = f(y; μ). El motor calcula los equilibrios y su "
        "estabilidad para cada valor del parámetro."
    )
    with st.form("form_bifurcacion"):
        familia = st.text_input(
            "Familia parametrizada",
            value=st.session_state.get("familia_bifurcacion", "y' = mu*y - y^2"),
            help="Usa mu como parámetro. Ejemplos: y' = mu*y - y^2, y' = mu - y^2",
        )
        columnas = st.columns(3)
        mu_min = columnas[0].number_input("μ mínimo", value=-2.0)
        mu_max = columnas[1].number_input("μ máximo", value=2.0)
        pasos = columnas[2].number_input("Número de valores", value=41, min_value=5, max_value=201)
        enviado = st.form_submit_button("Calcular bifurcación")
    if enviado:
        st.session_state["familia_bifurcacion"] = familia
        if mu_min >= mu_max:
            st.warning("El rango de μ no es válido.")
            return
        try:
            parametrizada = parsear_parametrizada(familia, "mu")
            valores = np.linspace(float(mu_min), float(mu_max), int(pasos))
            with st.spinner("Barriendo el parámetro μ…"):
                puntos = bifurcacion(parametrizada.rhs, parametrizada.parametro, valores)
        except EntradaInvalida as exc:
            mensaje_error(str(exc), "Usa una familia con el parámetro `mu`.")
            return
        except Exception:
            mensaje_error(
                "No se pudo completar el barrido de bifurcación.",
                "Prueba un rango más pequeño o una familia más simple.",
            )
            return
        if not puntos:
            st.info("No se encontraron equilibrios reales en ese rango.")
            return
        figura = figura_bifurcacion(puntos, tema_oscuro=tema_actual())
        st.plotly_chart(figura, use_container_width=True)
        filas = [
            {
                "μ": f"{punto.parametro:.4g}",
                "y*": f"{punto.equilibrio:.4g}",
                "Estabilidad": punto.estabilidad,
            }
            for punto in puntos
        ]
        with bloque_scroll(260):
            st.dataframe(filas, use_container_width=True, hide_index=True)


def render() -> None:
    titulo_pagina(
        "Cualitativo",
        "Equilibrios, estabilidad, línea de fase, isóclinas y bifurcaciones.",
        icono="🧭",
    )
    resultado = st.session_state.get("resultado")
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

    with tarjeta("Ecuación de trabajo", icono="📌"):
        st.latex(ecuacion.latex)
        if es_autonoma(ecuacion.rhs):
            st.success("La EDO es autónoma: y' = f(y).")
        else:
            st.info(
                "La EDO depende explícitamente de x; los equilibrios y la línea "
                "de fase se definen para ecuaciones autónomas. Puedes explorar "
                "las isóclinas y el campo de direcciones."
            )

    if resultado is not None and resultado.ecuacion_texto == texto:
        with st.expander("🔎 Existencia y unicidad del PVI actual", expanded=False):
            mostrar_existencia(resultado.existencia)
        with st.expander("♾️ Comportamiento asintótico", expanded=False):
            comportamiento = comportamiento_asintotico(resultado)
            st.write(comportamiento.texto)

    if es_autonoma(ecuacion.rhs):
        _seccion_equilibrios(ecuacion.rhs)

    intervalo = st.session_state.get("intervalo_actual")
    if intervalo is not None:
        x_min, x_max = intervalo
    else:
        x_min = float(st.session_state.get("x_min_input", -5.0))
        x_max = float(st.session_state.get("x_max_input", 5.0))
    with st.expander("🗺️ Isóclinas y curvas de nivel", expanded=False):
        _seccion_isoclinas(ecuacion.rhs, float(x_min), float(x_max))

    _seccion_bifurcacion()


__all__ = ["render"]
