"""Pestaña Datos: carga de CSV/Excel, ajuste, AIC/BIC y predicción."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.ajuste import (
    MODELOS,
    ajustar,
    cargar_datos,
    cargar_ejemplo,
    listar_modelos,
    predecir,
    seleccionar_mejor_modelo,
)
from core.tipos import DatosInvalidos

from ui.componentes import (
    bloque_scroll,
    lienzo,
    mensaje_error,
    mostrar_ecuacion,
    mostrar_texto,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import figura_ajuste, figura_sensibilidad

_EJEMPLOS = {
    "logistico": "Población logística (K ≈ 100, r ≈ 0.8)",
    "enfriamiento": "Enfriamiento de Newton (Tenv = 20 °C)",
    "crecimiento": "Crecimiento exponencial (k ≈ 0.35)",
    "decaimiento": "Decaimiento radiactivo (λ ≈ 0.15)",
}


def _guardar_datos(datos, origen: str) -> None:
    st.session_state["datos_ajuste"] = datos
    st.session_state["datos_origen"] = origen
    st.session_state["ajustes_datos"] = None
    st.session_state["mejor_ajuste"] = None
    st.session_state["prediccion_datos"] = None


def _cargar_fuente(archivo) -> None:
    firma = f"{archivo.name}:{archivo.size}"
    if st.session_state.get("datos_origen") == firma:
        return
    try:
        datos = cargar_datos(archivo.getvalue(), nombre=archivo.name)
    except DatosInvalidos as exc:
        mensaje_error(
            str(exc),
            "El archivo debe tener una columna de tiempo y otra de valor, "
            "con al menos cuatro filas numéricas.",
        )
        return
    except Exception:
        mensaje_error(
            "No se pudo leer el archivo.",
            "Comprueba que sea un CSV o Excel válido y que no esté dañado.",
        )
        return
    _guardar_datos(datos, firma)
    st.success("Datos cargados correctamente.", icon=None)


def _tabla_modelos(resultados) -> None:
    filas = []
    for resultado in resultados:
        fila = {
            "Modelo": resultado.nombre,
            "AIC": f"{resultado.aic:.3f}",
            "BIC": f"{resultado.bic:.3f}",
            "RMSE": f"{resultado.rmse:.4g}",
            "R²": f"{resultado.r2:.4f}",
            "Éxito": "sí" if resultado.exito else "no",
        }
        for nombre, parametro in resultado.parametros.items():
            fila[nombre] = f"{parametro.valor:.6g}"
        filas.append(fila)
    st.dataframe(filas, use_container_width=True, hide_index=True)


def _tabla_parametros(resultado) -> None:
    filas = []
    for nombre, parametro in resultado.parametros.items():
        filas.append(
            {
                "Parámetro": nombre,
                "Valor": f"{parametro.valor:.6g}",
                "Error estándar": "—" if parametro.error_estandar is None else f"{parametro.error_estandar:.4g}",
                "IC 95% inferior": "—" if parametro.ic_inf is None else f"{parametro.ic_inf:.6g}",
                "IC 95% superior": "—" if parametro.ic_sup is None else f"{parametro.ic_sup:.6g}",
            }
        )
    st.dataframe(filas, use_container_width=True, hide_index=True)


def _residuales(resultado) -> go.Figure:
    figura = go.Figure()
    if resultado.datos is not None and resultado.residuales.size:
        figura.add_trace(
            go.Scatter(
                x=resultado.datos.x,
                y=resultado.residuales,
                mode="markers+lines",
                name="residual",
                marker=dict(color="#dc2626", size=6),
                line=dict(color="#dc2626", width=1),
            )
        )
        figura.add_trace(
            go.Scatter(
                x=[float(resultado.datos.x[0]), float(resultado.datos.x[-1])],
                y=[0, 0],
                mode="lines",
                line=dict(color="#94a3b8", dash="dash"),
                hoverinfo="skip",
                showlegend=False,
            )
        )
    figura.update_layout(
        template="plotly_dark" if tema_actual() else "plotly_white",
        title="Residuales del mejor modelo",
        xaxis_title=resultado.datos.nombres[0] if resultado.datos else "x",
        yaxis_title="y observado − y ajustado",
        height=300,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return figura


def render(*, cabecera: bool = True) -> None:
    if cabecera:
        titulo_pagina(
            "Datos",
            "Carga observaciones, ajusta modelos de EDO y predice con bandas de confianza.",
            icono="chart",
        )
    columnas = st.columns([1.1, 1])
    with columnas[0]:
        with tarjeta("Cargar datos", icono="folder"):
            ejemplo = st.selectbox(
                "Ejemplo incluido",
                options=list(_EJEMPLOS),
                format_func=lambda clave: _EJEMPLOS[clave],
                key="datos_ejemplo_selector",
            )
            if st.button("Cargar ejemplo", key="datos_cargar_ejemplo"):
                try:
                    datos = cargar_ejemplo(ejemplo)
                    _guardar_datos(datos, f"ejemplo:{ejemplo}")
                    st.success(f"Ejemplo «{ejemplo}» cargado.", icon=None)
                except Exception:
                    mensaje_error(
                        "No se pudo cargar el ejemplo.",
                        "Revisa que exista data/ejemplos y que el archivo sea válido.",
                    )
            archivo = st.file_uploader(
                "O sube un CSV o Excel",
                type=["csv", "xlsx", "xls"],
                key="datos_archivo",
            )
            if archivo is not None:
                _cargar_fuente(archivo)
    with columnas[1]:
        with tarjeta("Formato esperado", icono="book"):
            st.markdown(
                """
- Una columna de tiempo (`tiempo`, `t`, `x`, `fecha`…).
- Una columna de valor (`valor`, `poblacion`, `temperatura`, `y`…).
- Al menos 4 filas numéricas; los `NaN` se descartan.
- También se aceptan Excel (`.xlsx`) con el mismo esquema.
                """
            )
            datos = st.session_state.get("datos_ajuste")
            if datos is not None:
                st.caption(f"Fuente actual: {st.session_state.get('datos_origen', '—')}")
                st.caption(datos.resumen)

    datos = st.session_state.get("datos_ajuste")
    if datos is None:
        st.info("Carga un ejemplo o un archivo para comenzar el ajuste.", icon=None)
        return

    st.markdown("#### Vista previa")
    with bloque_scroll(260):
        st.dataframe(
            {
                datos.nombres[0]: datos.x,
                datos.nombres[1]: datos.y,
            },
            use_container_width=True,
        )

    with tarjeta("Modelos candidatos", icono="layers"):
        modelos = listar_modelos()
        seleccionados = st.multiselect(
            "Modelos a ajustar",
            options=[modelo.id for modelo in modelos],
            default=[modelo.id for modelo in modelos],
            format_func=lambda clave: MODELOS[clave].nombre,
            key="datos_modelos",
        )
        with st.expander("Descripción de los modelos", expanded=False):
            for modelo in modelos:
                mostrar_texto(f"**{modelo.nombre}** — {modelo.descripcion}")
                mostrar_ecuacion(modelo.ecuacion_latex)
        if st.button("Ajustar modelos", key="datos_ajustar", type="primary"):
            if not seleccionados:
                st.warning("Elige al menos un modelo.", icon=None)
            else:
                with st.spinner("Integrando la EDO para cada modelo…"):
                    try:
                        resultados = ajustar(datos, modelos=seleccionados)
                    except Exception:
                        mensaje_error(
                            "No se pudo completar el ajuste.",
                            "Prueba con menos modelos o revisa los datos.",
                        )
                        return
                st.session_state["ajustes_datos"] = resultados
                st.session_state["mejor_ajuste"] = seleccionar_mejor_modelo(resultados)
                st.session_state["prediccion_datos"] = None

    resultados = st.session_state.get("ajustes_datos")
    if not resultados:
        return
    mejor = st.session_state.get("mejor_ajuste")

    if mejor is not None:
        st.success(
            f"Mejor modelo por AIC: **{mejor.nombre}**. {mejor.resumen} "
            "Un AIC menor indica mejor equilibrio entre ajuste y complejidad.",
            icon=None,
        )
    else:
        st.warning("Ningún modelo logró un ajuste exitoso con estos datos.", icon=None)

    st.markdown("#### Comparación AIC/BIC")
    _tabla_modelos(resultados)
    st.caption(
        "Regla práctica: diferencias de AIC menores que 2 son poco concluyentes; "
        "mayores que 10 indican evidencia clara a favor del menor AIC."
    )

    if mejor is not None:
        columnas = st.columns(2)
        with columnas[0]:
            st.markdown("#### Parámetros estimados")
            _tabla_parametros(mejor)
        with columnas[1]:
            st.markdown("#### Sensibilidad local")
            if mejor.sensibilidad:
                lienzo(figura_sensibilidad(mejor.sensibilidad, tema_oscuro=tema_actual()))
            else:
                st.caption("No se pudo calcular la sensibilidad.")

        lienzo(
            figura_ajuste(
                datos,
                resultados,
                prediccion=st.session_state.get("prediccion_datos"),
                tema_oscuro=tema_actual(),
            )
        )

        with st.expander("Residuales del mejor modelo", expanded=False):
            lienzo(_residuales(mejor))

        with tarjeta("Predicción a futuro", icono="chart"):
            columnas = st.columns(3)
            horizonte = columnas[0].number_input(
                "Horizonte a predecir",
                value=float(max(datos.x[-1] - datos.x[0], 1.0)),
                min_value=0.001,
                key="datos_horizonte",
            )
            nivel = columnas[1].slider(
                "Nivel de la banda",
                min_value=0.5,
                max_value=0.99,
                value=0.95,
                step=0.01,
                key="datos_nivel",
            )
            n_puntos = columnas[2].number_input(
                "Puntos de predicción",
                value=60,
                min_value=10,
                max_value=300,
                key="datos_n_pred",
            )
            if st.button("Predecir", key="datos_predecir"):
                x_nuevo = np.linspace(
                    float(datos.x[-1]),
                    float(datos.x[-1]) + float(horizonte),
                    int(n_puntos),
                )
                with st.spinner("Propagando la incertidumbre de los parámetros…"):
                    try:
                        prediccion = predecir(
                            mejor,
                            x_nuevo,
                            nivel=float(nivel),
                            semilla=int(st.session_state.get("semilla_global", 42)),
                        )
                    except Exception:
                        mensaje_error(
                            "No se pudo calcular la predicción.",
                            "Prueba un horizonte más corto o un nivel de banda menor.",
                        )
                        return
                if prediccion is None:
                    st.warning(
                        "La predicción no está disponible para este modelo.",
                        icon=None,
                    )
                else:
                    st.session_state["prediccion_datos"] = prediccion
                    st.rerun()
            prediccion = st.session_state.get("prediccion_datos")
            if prediccion is not None:
                st.caption(
                    f"Banda del {int(prediccion.nivel * 100)}% calculada por Monte Carlo "
                    "sobre la covarianza de los parámetros."
                )
                lienzo(
                    figura_ajuste(
                        datos,
                        [mejor],
                        prediccion=prediccion,
                        tema_oscuro=tema_actual(),
                    )
                )


__all__ = ["render"]
