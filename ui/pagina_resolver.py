"""Pestaña Resolver: resultado certificado, gráfica, pasos y modelos."""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.cualitativo import comportamiento_asintotico, es_autonoma
from core.hibrido import curva_desde_punto, curva_solucion, evaluar_solucion
from core.ia_opcional import estado_ia, explicar_resultado
from core.modelos import MODELOS, instanciar_modelo
from core.parser import parsear
from core.tipos import EntradaInvalida

from ui.componentes import (
    badge_estado,
    bloque_scroll,
    mensaje_error,
    metadatos_resultado,
    mostrar_certificado,
    mostrar_existencia,
    mostrar_pasos,
    mostrar_solucion,
    resumen_numerico,
    sin_resultado,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import (
    figura_campo_direcciones,
    figura_solucion,
)


def _curva_clic_en_campo(figura, tema_oscuro: bool) -> None:
    curva = st.session_state.get("curva_clic")
    if curva is None:
        return
    punto = st.session_state.get("punto_clic")
    etiqueta = "curva desde el clic"
    if punto is not None:
        etiqueta += f" ({punto[0]:.3g}, {punto[1]:.3g})"
    figura.add_trace(
        {
            "type": "scatter",
            "x": curva.x,
            "y": curva.y,
            "mode": "lines",
            "name": etiqueta,
            "line": {"color": "#dc2626", "width": 2.4},
        }
    )


def _seccion_campo(resultado) -> None:
    tema_oscuro = tema_actual()
    try:
        ecuaciones = parsear(resultado.ecuacion_texto)
    except EntradaInvalida:
        return
    if resultado.intervalo is None:
        return
    x_min, x_max = resultado.intervalo
    y_actual = resultado.numerico.y if resultado.numerico is not None else np.asarray([])
    if y_actual.size:
        finitos = y_actual[np.isfinite(y_actual)]
        centro = float(np.median(finitos)) if finitos.size else 0.0
        amplitud = max(3.0, float(np.ptp(finitos)) if finitos.size else 6.0)
    else:
        centro = float(resultado.y0 or 0.0)
        amplitud = 5.0
    margen = 0.6 * amplitud
    y_min = centro - margen
    y_max = centro + margen
    if y_min == y_max:
        y_min, y_max = -5.0, 5.0

    activar_clic = st.checkbox(
        "🖱️ Trazar curva haciendo clic en el campo",
        key="activar_clic_campo",
        help="Haz clic sobre un punto del campo para integrar la curva que pasa por él.",
    )
    figura = figura_campo_direcciones(
        ecuaciones.rhs,
        float(x_min),
        float(x_max),
        y_min,
        y_max,
        n=23,
        seleccionable=activar_clic,
        tema_oscuro=tema_oscuro,
        altura=430,
    )
    curva_actual = curva_solucion(resultado, n_points=600)
    if curva_actual is not None and activar_clic:
        xs, ys = curva_actual
        figura.add_trace(
            {
                "type": "scatter",
                "x": xs,
                "y": ys,
                "mode": "lines",
                "name": "solución del PVI",
                "line": {"color": "#2563eb", "width": 2.4},
            }
        )
    _curva_clic_en_campo(figura, tema_oscuro)

    if activar_clic:
        evento = st.plotly_chart(
            figura,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            key="grafico_campo_clic",
        )
        puntos = []
        if evento is not None:
            seleccion = evento.get("selection", {}) if isinstance(evento, dict) else {}
            puntos = seleccion.get("points", []) if isinstance(seleccion, dict) else []
        if puntos:
            primero = puntos[0]
            try:
                x_punto = float(primero["x"])
                y_punto = float(primero["y"])
            except (KeyError, TypeError, ValueError):
                x_punto = y_punto = None
            if x_punto is not None and y_punto is not None:
                anterior = st.session_state.get("punto_clic")
                if anterior is None or abs(anterior[0] - x_punto) > 1e-9 or abs(anterior[1] - y_punto) > 1e-9:
                    try:
                        curva = curva_desde_punto(
                            resultado.ecuacion_texto,
                            x_punto,
                            y_punto,
                            x_min=float(x_min),
                            x_max=float(x_max),
                        )
                    except Exception:
                        curva = None
                    if curva is not None and curva.exito:
                        st.session_state["curva_clic"] = curva
                        st.session_state["punto_clic"] = (x_punto, y_punto)
                        st.rerun()
                    else:
                        st.warning(
                            "No se pudo integrar desde ese punto; prueba con "
                            "otro punto del campo."
                        )
        if st.session_state.get("curva_clic") is not None:
            st.caption(
                "La curva roja se integró desde el último punto seleccionado."
            )
            if st.button("Limpiar traza del campo", key="limpiar_clic"):
                st.session_state["curva_clic"] = None
                st.session_state["punto_clic"] = None
                st.rerun()
    else:
        st.plotly_chart(figura, use_container_width=True)


def _seccion_explicacion(resultado) -> None:
    with st.expander("💬 Explicación en lenguaje sencillo", expanded=False):
        estado = estado_ia()
        usar_ia = False
        if estado.activa:
            usar_ia = st.checkbox(
                "Usar IA opcional para redactar (nunca calcula)",
                value=False,
                key="usar_ia_explicacion",
            )
        else:
            st.caption(
                "La capa de IA está desactivada; se usa el explicador local. "
                + estado.motivo
            )
        if st.button("Generar explicación", key="generar_explicacion"):
            try:
                st.session_state["explicacion_resultado"] = explicar_resultado(
                    resultado, usar_ia=usar_ia
                )
            except Exception:
                mensaje_error(
                    "No se pudo generar la explicación.",
                    "Se mostrará una explicación local si vuelves a intentarlo.",
                )
        explicacion = st.session_state.get("explicacion_resultado")
        if explicacion:
            st.write(explicacion)


def _seccion_evaluacion(resultado) -> None:
    with st.expander("📍 Evaluar la solución en un punto", expanded=False):
        if resultado.intervalo is None:
            st.caption("No hay intervalo definido.")
            return
        x_min, x_max = resultado.intervalo
        x_eval = st.number_input(
            "Valor de x",
            value=float((x_min + x_max) / 2.0),
            key="x_evaluacion_solucion",
        )
        if st.button("Evaluar", key="boton_evaluar_solucion"):
            valor = evaluar_solucion(resultado, float(x_eval))
            if valor is None:
                st.warning(
                    "No se pudo evaluar la expresión; usa la curva numérica."
                )
            else:
                st.success(f"y({float(x_eval):g}) ≈ {valor:.10g}")


def _seccion_modelos() -> None:
    with st.expander("🧩 Modelos aplicados", expanded=False):
        st.caption(
            "Carga un modelo con sus parámetros y condiciones iniciales. "
            "Después podrás resolverlo y analizarlo como cualquier EDO."
        )
        id_modelo = st.selectbox(
            "Modelo",
            options=list(MODELOS),
            format_func=lambda clave: MODELOS[clave].nombre,
            key="modelo_aplicado_selector",
        )
        modelo = MODELOS[id_modelo]
        st.write(modelo.descripcion)
        st.caption(modelo.contexto)
        parametros: dict[str, float] = {}
        columnas = st.columns(min(3, max(1, len(modelo.parametros))))
        for indice, parametro in enumerate(modelo.parametros):
            with columnas[indice % len(columnas)]:
                valor = st.number_input(
                    f"{parametro.etiqueta} ({parametro.unidad})" if parametro.unidad else parametro.etiqueta,
                    value=float(parametro.valor_defecto),
                    min_value=parametro.minimo,
                    max_value=parametro.maximo,
                    key=f"modelo_{id_modelo}_{parametro.nombre}",
                    help=parametro.descripcion,
                )
                parametros[parametro.nombre] = float(valor)
        columnas_iniciales = st.columns(4)
        x0 = columnas_iniciales[0].number_input(
            "x₀", value=float(modelo.x0), key=f"modelo_{id_modelo}_x0"
        )
        y0 = columnas_iniciales[1].number_input(
            "y₀", value=float(modelo.y0), key=f"modelo_{id_modelo}_y0"
        )
        x_min = columnas_iniciales[2].number_input(
            "x mínimo", value=float(modelo.x_min), key=f"modelo_{id_modelo}_xmin"
        )
        x_max = columnas_iniciales[3].number_input(
            "x máximo", value=float(modelo.x_max), key=f"modelo_{id_modelo}_xmax"
        )
        try:
            instancia = instanciar_modelo(
                id_modelo,
                parametros=parametros,
                x0=float(x0),
                y0=float(y0),
                x_min=float(x_min),
                x_max=float(x_max),
            )
        except EntradaInvalida as exc:
            st.warning(str(exc))
            return
        st.markdown("**Ecuación instanciada**")
        st.code(instancia.ecuacion_texto, language="text")
        if instancia.solucion_conocida:
            st.caption(f"Solución de referencia: {instancia.solucion_conocida}")
        if st.button("Cargar modelo en la barra lateral", key="cargar_modelo"):
            st.session_state["_cargar_ecuacion"] = {
                "ecuacion": instancia.ecuacion_texto,
                "x0": instancia.x0,
                "y0": instancia.y0,
                "x_min": instancia.x_min,
                "x_max": instancia.x_max,
            }
            st.session_state["_solicitar_resolver"] = True
            st.rerun()


def render() -> None:
    titulo_pagina(
        "Resolver",
        "Solución verificada, certificado, pasos y exploración del campo de direcciones.",
        icono="🧮",
    )
    error = st.session_state.get("error_resolver")
    if error:
        mensaje_error(error)
    resultado = st.session_state.get("resultado")
    if resultado is None:
        sin_resultado()
        _seccion_modelos()
        return

    with tarjeta("Resultado", icono="📌"):
        mostrar_solucion(resultado)
        metadatos_resultado(resultado)

    columna_grafica, columna_pasos = st.columns([1.35, 1], gap="large")
    with columna_grafica:
        pestaña_solucion, pestaña_campo = st.tabs(["📈 Solución", "🧭 Campo"])
        with pestaña_solucion:
            figura = figura_solucion(resultado, tema_oscuro=tema_actual())
            st.plotly_chart(figura, use_container_width=True)
        with pestaña_campo:
            _seccion_campo(resultado)
    with columna_pasos:
        st.markdown("#### 🪜 Paso a paso")
        mostrar_pasos(resultado.pasos, altura=520)

    mostrar_certificado(resultado.certificado)

    columnas = st.columns(2)
    with columnas[0]:
        with st.expander("🔎 Existencia, unicidad y explosión", expanded=False):
            mostrar_existencia(resultado.existencia)
    with columnas[1]:
        with st.expander("🧮 Detalles numéricos", expanded=False):
            if resultado.numerico is None:
                st.caption("No se ejecutó integración numérica.")
            else:
                resumen_numerico(resultado)
                if resultado.numerico.exito:
                    datos = {
                        "x": resultado.numerico.x,
                        "y": resultado.numerico.y,
                    }
                    with bloque_scroll(240):
                        st.dataframe(datos, use_container_width=True)

    if es_autonoma(parsear(resultado.ecuacion_texto).rhs):
        comportamiento = comportamiento_asintotico(resultado)
        with st.expander("♾️ Comportamiento cuando x → ∞", expanded=False):
            st.write(comportamiento.texto)
            if comportamiento.limite is not None:
                st.caption(f"Límite estimado: {comportamiento.limite:.6g}")

    _seccion_evaluacion(resultado)
    _seccion_explicacion(resultado)
    _seccion_modelos()


__all__ = ["render"]
