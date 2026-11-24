"""Pestaña Informes: vista previa y exportación PDF/LaTeX."""

from __future__ import annotations

import streamlit as st

from core.informes import (
    OpcionesInforme,
    SeccionesInforme,
    generar_latex,
    generar_pdf,
)
from core.tipos import SolucionNoDisponible

from ui.componentes import mensaje_error, mostrar_certificado, mostrar_solucion, sin_resultado, tarjeta, titulo_pagina


def render() -> None:
    titulo_pagina(
        "Informes",
        "Genera un documento con enunciado, procedimiento, gráfica, errores y certificado.",
        icono="📄",
    )
    resultado = st.session_state.get("resultado")
    if resultado is None:
        sin_resultado()
        return

    with tarjeta("Vista previa del contenido", icono="👁️"):
        mostrar_solucion(resultado)
        columnas = st.columns(3)
        columnas[0].metric("Pasos", len(resultado.pasos))
        columnas[1].metric("Advertencias", len(resultado.advertencias))
        columnas[2].metric(
            "Certificado",
            resultado.certificado.etiqueta if resultado.certificado else "sin certificado",
        )
    mostrar_certificado(resultado.certificado)

    with tarjeta("Opciones del informe", icono="⚙️"):
        columnas = st.columns(2)
        titulo = columnas[0].text_input(
            "Título",
            value="Informe EDO-Lab",
            key="informe_titulo",
        )
        autor = columnas[1].text_input(
            "Autor (opcional)",
            value=st.session_state.get("informe_autor", ""),
            key="informe_autor",
        )
        st.markdown("**Secciones**")
        columnas = st.columns(3)
        secciones = SeccionesInforme(
            enunciado=columnas[0].checkbox("Enunciado", value=True, key="inf_enunciado"),
            metodo=columnas[1].checkbox("Método y solución", value=True, key="inf_metodo"),
            pasos=columnas[2].checkbox("Procedimiento", value=True, key="inf_pasos"),
            graficas=columnas[0].checkbox("Gráficas", value=True, key="inf_graficas"),
            errores=columnas[1].checkbox("Tabla de errores", value=True, key="inf_errores"),
            certificado=columnas[2].checkbox("Certificado", value=True, key="inf_certificado"),
            advertencias=columnas[0].checkbox("Advertencias", value=True, key="inf_advertencias"),
        )
        opciones = OpcionesInforme(titulo=titulo, autor=autor, secciones=secciones)

    columnas = st.columns(2)
    generar_pdf_click = columnas[0].button(
        "📕 Generar PDF", key="informe_generar_pdf", type="primary", use_container_width=True
    )
    generar_latex_click = columnas[1].button(
        "📝 Generar LaTeX", key="informe_generar_latex", use_container_width=True
    )
    if generar_pdf_click:
        with st.spinner("Componiendo el PDF…"):
            try:
                informe = generar_pdf(resultado, opciones)
            except SolucionNoDisponible as exc:
                mensaje_error(str(exc), "Instala reportlab y matplotlib.")
                return
            except Exception:
                mensaje_error(
                    "No se pudo generar el PDF.",
                    "Prueba a desactivar la sección de gráficas o revisa el resultado.",
                )
                return
        st.session_state["informe_pdf"] = informe
    if generar_latex_click:
        try:
            latex = generar_latex(resultado, opciones)
        except Exception:
            mensaje_error(
                "No se pudo generar el documento LaTeX.",
                "Prueba a desactivar alguna sección.",
            )
            return
        st.session_state["informe_latex"] = latex

    informe_pdf = st.session_state.get("informe_pdf")
    if informe_pdf is not None:
        st.success(
            f"PDF listo: {informe_pdf.nombre_archivo} "
            f"({informe_pdf.tamano_bytes / 1024:.1f} KB)."
        )
        st.download_button(
            "⬇️ Descargar PDF",
            data=informe_pdf.contenido,
            file_name=informe_pdf.nombre_archivo,
            mime=informe_pdf.mime,
            key="informe_descargar_pdf",
            use_container_width=True,
        )
    latex = st.session_state.get("informe_latex")
    if latex:
        st.success("Documento LaTeX listo.")
        st.download_button(
            "⬇️ Descargar LaTeX",
            data=latex.encode("utf-8"),
            file_name="informe_edolab.tex",
            mime="text/x-tex",
            key="informe_descargar_latex",
            use_container_width=True,
        )
        with st.expander("Ver código LaTeX", expanded=False):
            st.code(latex, language="latex")


__all__ = ["render"]
