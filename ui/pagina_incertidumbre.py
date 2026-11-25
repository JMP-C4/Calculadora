"""Pestaña Incertidumbre: Monte Carlo y sensibilidad global con Sobol."""

from __future__ import annotations

import numpy as np
import streamlit as st

from odecalc.symbols import X, Y

from core.incertidumbre import (
    Distribucion,
    distribuciones_por_defecto,
    monte_carlo,
    sobol_indices,
)
from core.parser import parsear_con_parametros
from core.tipos import EntradaInvalida, SolucionNoDisponible

from ui.componentes import (
    lienzo,
    mensaje_error,
    mostrar_ecuacion,
    sin_resultado,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import figura_monte_carlo, figura_sobol


def _parametros(rhs) -> list[str]:
    return [str(simbolo) for simbolo in sorted(rhs.free_symbols - {X, Y}, key=lambda s: s.name)]


def _control_distribucion(
    nombre: str,
    defecto: Distribucion,
    *,
    clave: str,
) -> Distribucion:
    with st.expander(f"Parámetro «{nombre}»", expanded=False):
        tipo = st.selectbox(
            "Distribución",
            options=["normal", "uniforme", "fija"],
            index=["normal", "uniforme", "fija"].index(defecto.tipo),
            key=f"{clave}_tipo",
            format_func=lambda valor: {
                "normal": "Normal",
                "uniforme": "Uniforme",
                "fija": "Fija",
            }[valor],
        )
        columnas = st.columns(2)
        media = columnas[0].number_input(
            "Media / valor",
            value=float(defecto.media),
            key=f"{clave}_media",
        )
        if tipo == "uniforme":
            bajo = columnas[1].number_input(
                "Mínimo",
                value=float(defecto.minimo if defecto.minimo is not None else defecto.media - defecto.desviacion),
                key=f"{clave}_min",
            )
            alto = columnas[1].number_input(
                "Máximo",
                value=float(defecto.maximo if defecto.maximo is not None else defecto.media + defecto.desviacion),
                key=f"{clave}_max",
            )
            return Distribucion(
                nombre=nombre,
                tipo=tipo,
                media=float(media),
                minimo=float(bajo),
                maximo=float(alto),
            )
        desviacion = columnas[1].number_input(
            "Desviación estándar",
            value=float(abs(defecto.desviacion)),
            min_value=0.0,
            key=f"{clave}_std",
        )
        return Distribucion(
            nombre=nombre,
            tipo=tipo if tipo in {"normal", "fija"} else "normal",
            media=float(media),
            desviacion=float(desviacion),
        )


def render(*, cabecera: bool = True) -> None:
    if cabecera:
        titulo_pagina(
            "Incertidumbre",
            "Propaga la incertidumbre de parámetros y condiciones iniciales; mide sensibilidad global.",
            icono="shield",
        )
    texto = st.session_state.get("ecuacion_input", "")
    if not texto.strip():
        sin_resultado()
        return
    try:
        ecuacion = parsear_con_parametros(texto)
    except EntradaInvalida as exc:
        mensaje_error(
            str(exc),
            "Para Monte Carlo y Sobol escribe una EDO con parámetros, por "
            "ejemplo `y' = r*y`.",
        )
        return
    nombres = _parametros(ecuacion.rhs)
    x0 = float(st.session_state.get("x0_input", 0.0))
    y0 = float(st.session_state.get("y0_input", 1.0))
    x_min = float(st.session_state.get("x_min_input", 0.0))
    x_max = float(st.session_state.get("x_max_input", 5.0))
    if x_min >= x_max:
        mensaje_error("El intervalo no es válido.")
        return

    with tarjeta("Ecuación y fuentes de incertidumbre", icono="pin"):
        mostrar_ecuacion(ecuacion.latex)
        if nombres:
            st.caption(
                "Parámetros detectados: " + ", ".join(nombres) + ". "
                "Configura su distribución antes de simular."
            )
        else:
            st.info(
                "La ecuación no tiene parámetros simbólicos; puedes estudiar "
                "la incertidumbre de la condición inicial y₀.",
                icon=None,
            )
        st.caption(
            f"PVI base: y({x0:g}) = {y0:g}, x ∈ [{x_min:g}, {x_max:g}]."
        )

    with tarjeta("Distribuciones", icono="sliders"):
        defectos = distribuciones_por_defecto(ecuacion.rhs)
        distribuciones = {
            nombre: _control_distribucion(nombre, defectos[nombre], clave=f"inci_{nombre}")
            for nombre in nombres
        }
        usar_y0 = st.checkbox(
            "Añadir incertidumbre a la condición inicial y₀",
            value=False,
            key="inci_usar_y0",
        )
        distribucion_y0 = None
        if usar_y0:
            columnas = st.columns(2)
            tipo_y0 = columnas[0].selectbox(
                "Distribución de y₀",
                ["normal", "uniforme"],
                key="inci_y0_tipo",
                format_func=lambda valor: "Normal" if valor == "normal" else "Uniforme",
            )
            desviacion_y0 = columnas[1].number_input(
                "Desviación de y₀",
                value=float(max(abs(y0) * 0.05, 0.01)),
                min_value=0.0,
                key="inci_y0_std",
            )
            distribucion_y0 = Distribucion(
                nombre="y0",
                tipo=tipo_y0,
                media=float(y0),
                desviacion=float(desviacion_y0),
                minimo=float(y0 - desviacion_y0) if tipo_y0 == "uniforme" else None,
                maximo=float(y0 + desviacion_y0) if tipo_y0 == "uniforme" else None,
            )

    with tarjeta("Simulación Monte Carlo", icono="activity"):
        columnas = st.columns(3)
        n_muestras = columnas[0].slider(
            "Muestras", min_value=50, max_value=1500, value=300, step=50, key="inci_muestras"
        )
        semilla = columnas[1].number_input(
            "Semilla",
            value=int(st.session_state.get("semilla_global", 42)),
            min_value=0,
            step=1,
            key="inci_semilla",
        )
        nivel = columnas[2].slider(
            "Nivel de banda", min_value=0.5, max_value=0.99, value=0.90, step=0.01, key="inci_nivel"
        )
        if st.button("Ejecutar Monte Carlo", key="inci_ejecutar", type="primary"):
            x_eval = np.linspace(x_min, x_max, 80)
            with st.spinner("Integrando las trayectorias muestreadas…"):
                try:
                    resultado = monte_carlo(
                        ecuacion.rhs,
                        x0,
                        y0,
                        x_eval,
                        parametros=distribuciones,
                        distribucion_y0=distribucion_y0,
                        n_muestras=int(n_muestras),
                        semilla=int(semilla),
                        nivel=float(nivel),
                    )
                except (EntradaInvalida, SolucionNoDisponible) as exc:
                    mensaje_error(str(exc), "Ajusta las distribuciones o el intervalo.")
                    return
                except Exception:
                    mensaje_error(
                        "La simulación Monte Carlo no pudo completarse.",
                        "Reduce el número de muestras o el intervalo de integración.",
                    )
                    return
            st.session_state["inci_mc"] = resultado

    resultado_mc = st.session_state.get("inci_mc")
    if resultado_mc is not None:
        columnas = st.columns(4)
        columnas[0].metric("Trayectorias exitosas", f"{resultado_mc.n_exitos}/{resultado_mc.n_total}")
        columnas[1].metric("Éxito", f"{resultado_mc.porcentaje_exito:.1f}%")
        columnas[2].metric("Semilla", resultado_mc.semilla)
        columnas[3].metric("Banda", f"{int(resultado_mc.nivel * 100)}%")
        lienzo(figura_monte_carlo(resultado_mc, tema_oscuro=tema_actual()))
        for nota in resultado_mc.notas:
            st.caption(nota)
        st.caption(
            "La misma semilla reproduce exactamente las mismas bandas: "
            "los cálculos son deterministas."
        )

    st.markdown("#### Sensibilidad global (Sobol)")
    if not nombres:
        st.info(
            "Sobol necesita al menos un parámetro simbólico en la ecuación.",
            icon=None,
        )
        return
    with tarjeta("Índices de Sobol", icono="layers"):
        st.caption(
            "S1 mide el efecto directo de cada parámetro; ST incluye sus "
            "interacciones. Se evalúa y(x_final) con muestreo de Saltelli."
        )
        columnas = st.columns(2)
        x_final = columnas[0].number_input(
            "Evaluar en x =",
            value=float(x_max),
            key="sobol_x_final",
        )
        n_sobol = columnas[1].slider(
            "Tamaño base N",
            min_value=16,
            max_value=256,
            value=64,
            step=16,
            key="sobol_n",
            help="El número de evaluaciones es aproximadamente N·(2d+2).",
        )
        limites: dict[str, tuple[float, float]] = {}
        for nombre in nombres:
            defecto = defectos[nombre]
            with st.expander(f"Límites de «{nombre}»", expanded=False):
                columnas_param = st.columns(2)
                bajo = columnas_param[0].number_input(
                    "Mínimo",
                    value=float(defecto.media - 3 * abs(defecto.desviacion)),
                    key=f"sobol_{nombre}_min",
                )
                alto = columnas_param[1].number_input(
                    "Máximo",
                    value=float(defecto.media + 3 * abs(defecto.desviacion)),
                    key=f"sobol_{nombre}_max",
                )
                limites[nombre] = (float(bajo), float(alto))
        if st.button("Calcular índices de Sobol", key="sobol_ejecutar"):
            if any(bajo >= alto for bajo, alto in limites.values()):
                st.warning(
                    "Cada límite inferior debe ser menor que su máximo.",
                    icon=None,
                )
                return
            with st.spinner("Muestreando y evaluando el modelo…"):
                try:
                    indices = sobol_indices(
                        ecuacion.rhs,
                        x0,
                        y0,
                        float(x_final),
                        limites=limites,
                        n_muestras=int(n_sobol),
                        semilla=int(st.session_state.get("semilla_global", 42)),
                    )
                except (EntradaInvalida, SolucionNoDisponible) as exc:
                    mensaje_error(str(exc), "Amplía o reduce los límites de los parámetros.")
                    return
                except Exception:
                    mensaje_error(
                        "No se pudieron calcular los índices de Sobol.",
                        "Prueba con menos parámetros, un N menor o revisa los límites.",
                    )
                    return
            st.session_state["sobol_resultado"] = indices

    indices = st.session_state.get("sobol_resultado")
    if indices is not None:
        lienzo(figura_sobol(indices, tema_oscuro=tema_actual()))
        st.dataframe(
            [
                {
                    "Parámetro": nombre,
                    "S1": f"{s1:.4f}",
                    "Conf. S1": f"{c1:.4f}",
                    "ST": f"{st_total:.4f}",
                    "Conf. ST": f"{ct:.4f}",
                }
                for nombre, s1, c1, st_total, ct in zip(
                    indices.nombres,
                    indices.S1,
                    indices.S1_conf,
                    indices.ST,
                    indices.ST_conf,
                )
            ],
            use_container_width=True,
            hide_index=True,
        )
        for nota in indices.notas:
            st.caption(nota)


__all__ = ["render"]
