"""Pestaña Aprender: ejercicios verificados, corrector y progreso."""

from __future__ import annotations

import streamlit as st

from core.corrector import corregir
from core.ejercicios import (
    TIPOS,
    cargar_perfil,
    generar_ejercicio,
    guardar_perfil,
    recomendar_siguiente,
)
from core.notacion import formatear_texto
from core.tipos import EntradaInvalida, SolucionNoDisponible

from ui.componentes import (
    badge_estado,
    bloque_scroll,
    mensaje_error,
    mostrar_ecuacion,
    mostrar_texto,
    notacion_actual,
    tarjeta,
    titulo_pagina,
)


def _perfil():
    if "perfil_estudiante" not in st.session_state:
        st.session_state["perfil_estudiante"] = cargar_perfil()
    return st.session_state["perfil_estudiante"]


def _seccion_generador(perfil) -> None:
    recomendado = recomendar_siguiente(perfil)
    st.info(
        f"Recomendación del perfil: practica **{recomendado}**. "
        "Se elige el tipo con menor precisión registrada.",
        icon=None,
    )
    with tarjeta("Generar un ejercicio", icono="target"):
        columnas = st.columns(3)
        tipo = columnas[0].selectbox(
            "Tipo de EDO",
            options=list(TIPOS),
            index=list(TIPOS).index(recomendado),
            key="aprender_tipo",
        )
        dificultad = columnas[1].slider(
            "Dificultad",
            min_value=1,
            max_value=5,
            value=1,
            key="aprender_dificultad",
        )
        semilla = columnas[2].number_input(
            "Semilla",
            value=int(st.session_state.get("semilla_global", 42)),
            min_value=0,
            step=1,
            key="aprender_semilla",
        )
        if st.button("Generar ejercicio verificado", key="aprender_generar", type="primary"):
            with st.spinner("Generando y verificando con el motor…"):
                try:
                    ejercicio = generar_ejercicio(
                        tipo,
                        int(dificultad),
                        semilla=int(semilla),
                    )
                except SolucionNoDisponible as exc:
                    mensaje_error(str(exc), "Prueba otro tipo, dificultad o semilla.")
                    return
                except Exception:
                    mensaje_error(
                        "No se pudo generar el ejercicio.",
                        "El motor no encontró una variante verificable; intenta de nuevo.",
                    )
                    return
            st.session_state["ejercicio_actual"] = ejercicio
            st.session_state["mostrar_solucion_ejercicio"] = False

    ejercicio = st.session_state.get("ejercicio_actual")
    if ejercicio is None:
        st.caption("Genera un ejercicio para comenzar.")
        return
    with tarjeta(f"Ejercicio · {ejercicio.resumen}", icono="file"):
        mostrar_texto(ejercicio.enunciado)
        with st.expander("Pista", expanded=False):
            mostrar_texto(ejercicio.pista)
        for advertencia in ejercicio.advertencias:
            st.caption(formatear_texto(advertencia, notacion_actual()))
        columnas = st.columns(3)
        if columnas[0].button("Mostrar solución", key="aprender_mostrar_solucion"):
            st.session_state["mostrar_solucion_ejercicio"] = True
            st.rerun()
        if columnas[1].button("La resolví bien", key="aprender_bien"):
            perfil.registrar(ejercicio.tipo, True, ecuacion=ejercicio.ecuacion)
            guardar_perfil(perfil)
            st.success("Bien: progreso guardado.", icon=None)
            st.session_state["ejercicio_actual"] = None
            st.rerun()
        if columnas[2].button("Me equivoqué", key="aprender_mal"):
            perfil.registrar(ejercicio.tipo, False, ecuacion=ejercicio.ecuacion)
            guardar_perfil(perfil)
            st.info("Registrado. La recomendación se ajustará a este tipo.", icon=None)
            st.session_state["ejercicio_actual"] = None
            st.rerun()
        if st.session_state.get("mostrar_solucion_ejercicio"):
            st.markdown("**Solución certificada**")
            mostrar_ecuacion(ejercicio.solucion_latex)
            if ejercicio.certificado is not None:
                badge_estado(ejercicio.certificado)
                if ejercicio.certificado.dominio_valido:
                    st.caption(
                        "Dominio: "
                        + formatear_texto(
                            ejercicio.certificado.dominio_valido, notacion_actual()
                        )
                    )


def _seccion_corrector(perfil) -> None:
    with tarjeta("Corrector de procedimiento", icono="search"):
        st.caption(
            "Escribe una línea por paso. El corrector comprueba equivalencia "
            "entre pasos y consistencia con la EDO; señala el primer error y da "
            "una pista, sin entregar la respuesta completa."
        )
        ecuacion = st.text_input(
            "EDO original (opcional)",
            value=st.session_state.get("ecuacion_input", "y' = y"),
            key="corrector_ecuacion",
        )
        desarrollo = st.text_area(
            "Tu desarrollo",
            value=st.session_state.get("corrector_texto", ""),
            height=220,
            placeholder=(
                "Ejemplo:\n"
                "y' = y\n"
                "dy/y = dx\n"
                "ln|y| = x + C\n"
                "y = C*exp(x)"
            ),
            key="corrector_texto",
        )
        columnas = st.columns(3)
        usar_pvi = columnas[0].checkbox(
            "Comprobar el PVI", value=False, key="corrector_usar_pvi"
        )
        x0 = columnas[1].number_input("x₀", value=0.0, key="corrector_x0")
        y0 = columnas[2].number_input("y₀", value=1.0, key="corrector_y0")
        if st.button("Revisar procedimiento", key="corrector_revisar"):
            try:
                resultado = corregir(
                    desarrollo,
                    ecuacion.strip() or None,
                    x0=float(x0) if usar_pvi else None,
                    y0=float(y0) if usar_pvi else None,
                )
            except EntradaInvalida as exc:
                mensaje_error(str(exc))
                return
            except Exception:
                mensaje_error(
                    "No se pudo revisar el desarrollo.",
                    "Comprueba la sintaxis de cada línea y usa y' para la derivada.",
                )
                return
            st.session_state["corrector_resultado"] = resultado
            perfil.registrar("corrector", resultado.correcto)
            guardar_perfil(perfil)

    resultado = st.session_state.get("corrector_resultado")
    if resultado is None:
        return
    if resultado.correcto:
        st.success(formatear_texto(resultado.mensaje, notacion_actual()), icon=None)
        st.caption(f"Líneas verificadas: {resultado.lineas_verificadas}.")
    else:
        error = resultado.primer_error
        st.error(formatear_texto(resultado.mensaje, notacion_actual()), icon=None)
        if error is not None:
            st.markdown(f"**Línea {error.linea}:** `{error.texto}`")
            st.info(
                "Pista: " + formatear_texto(error.pista, notacion_actual()), icon=None
            )
            st.caption(f"Tipo de error: {error.tipo}")
    with st.expander("Detalles de la revisión", expanded=False):
        with bloque_scroll(240):
            for detalle in resultado.detalles:
                mostrar_texto(f"· {detalle}")
            if not resultado.detalles:
                st.caption("Sin detalles adicionales.")


def _seccion_progreso(perfil) -> None:
    st.markdown("#### Progreso por tipo")
    columnas = st.columns(4)
    columnas[0].metric("Intentos totales", perfil.total)
    columnas[1].metric(
        "Tipos con datos",
        sum(1 for valor in perfil.resumen().values() if valor["precision"] is not None),
    )
    mejor = max(
        (
            (tipo, valor["precision"])
            for tipo, valor in perfil.resumen().items()
            if valor["precision"] is not None
        ),
        key=lambda par: par[1],
        default=None,
    )
    columnas[2].metric(
        "Mejor precisión",
        "—" if mejor is None else f"{mejor[1] * 100:.0f}% ({mejor[0]})",
    )
    columnas[3].metric("Recomendación", recomendar_siguiente(perfil))

    filas = []
    for tipo, valores in perfil.resumen().items():
        precision = valores["precision"]
        filas.append(
            {
                "Tipo": tipo,
                "Aciertos": valores["aciertos"],
                "Errores": valores["errores"],
                "Precisión": "—" if precision is None else f"{precision * 100:.0f}%",
            }
        )
    st.dataframe(filas, use_container_width=True, hide_index=True)

    with st.expander("Historial reciente", expanded=False):
        with bloque_scroll(260):
            if perfil.historial:
                for entrada in reversed(perfil.historial[-30:]):
                    estado = "Correcto" if entrada.get("correcto") else "Incorrecto"
                    etiqueta = entrada.get("tipo", "—")
                    extra = entrada.get("ecuacion", "")
                    mostrar_texto(f"**{estado}** · **{etiqueta}** {extra}")
            else:
                st.caption("Todavía no hay intentos registrados.")

    with st.expander("Reiniciar perfil", expanded=False):
        confirmar = st.checkbox(
            "Confirmo que quiero borrar el progreso guardado",
            key="aprender_confirmar_reset",
        )
        if st.button("Reiniciar progreso", key="aprender_reset", disabled=not confirmar):
            from core.ejercicios import PerfilEstudiante

            perfil = PerfilEstudiante()
            guardar_perfil(perfil)
            st.session_state["perfil_estudiante"] = perfil
            st.success("Perfil reiniciado.", icon=None)
            st.rerun()


def render(*, cabecera: bool = True) -> None:
    if cabecera:
        titulo_pagina(
            "Aprender",
            "Ejercicios certificados, corrección del procedimiento y progreso adaptativo.",
            icono="book",
        )
    perfil = _perfil()
    pestañas = st.tabs(["Ejercicios", "Corrector", "Progreso"])
    with pestañas[0]:
        _seccion_generador(perfil)
    with pestañas[1]:
        _seccion_corrector(perfil)
    with pestañas[2]:
        _seccion_progreso(perfil)


__all__ = ["render"]
