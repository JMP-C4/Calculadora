"""Componentes reutilizables de la interfaz Streamlit de EDO-Lab."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Iterator

import streamlit as st

from core.parser import parsear_con_parametros
from core.tipos import (
    Certificado,
    EntradaInvalida,
    EstadoVerificacion,
    InfoExistencia,
    Paso,
    ResultadoSolucion,
)


def tema_actual() -> bool:
    """``True`` si el usuario eligió el tema oscuro."""

    return bool(st.session_state.get("tema_oscuro", False))


@contextmanager
def tarjeta(
    titulo: str | None = None,
    *,
    icono: str = "",
    subtitulo: str | None = None,
) -> Iterator[Any]:
    """Bloque con borde suave y padding cómodo."""

    with st.container(border=True):
        if titulo:
            encabezado = f"{icono} {titulo}".strip()
            st.markdown(f"#### {encabezado}")
        if subtitulo:
            st.caption(subtitulo)
        yield


@contextmanager
def bloque_scroll(altura: int = 480) -> Iterator[Any]:
    """Contenedor con altura máxima y barra de scroll propia."""

    with st.container(height=int(altura), border=False):
        yield


def _datos_badge(estado: Any) -> tuple[str, str, str]:
    if isinstance(estado, Certificado):
        estado = estado.estado
    if isinstance(estado, ResultadoSolucion):
        estado = estado.certificado.estado if estado.certificado else None
    if isinstance(estado, str):
        limpio = estado.lower()
        if "simbol" in limpio:
            estado = EstadoVerificacion.SIMBOLICA
        elif "numer" in limpio:
            estado = EstadoVerificacion.NUMERICA
        else:
            estado = EstadoVerificacion.NO_VERIFICADA
    if estado == EstadoVerificacion.SIMBOLICA:
        return "edo-badge-ok", "✅", "Verificada simbólicamente"
    if estado == EstadoVerificacion.NUMERICA:
        return "edo-badge-warn", "⚠️", "Verificación numérica"
    return "edo-badge-error", "❌", "No verificada"


def badge_estado(estado: Any) -> None:
    """Muestra un distintivo accesible con icono y texto."""

    clase, icono, texto = _datos_badge(estado)
    st.markdown(
        f'<span class="edo-badge {clase}">{icono} {texto}</span>',
        unsafe_allow_html=True,
    )


def chip(texto: str, *, tono: str = "info") -> None:
    """Etiqueta compacta para metadatos."""

    clases = {
        "info": "edo-badge-info",
        "ok": "edo-badge-ok",
        "warn": "edo-badge-warn",
        "error": "edo-badge-error",
    }
    st.markdown(
        f'<span class="edo-badge {clases.get(tono, "edo-badge-info")}">'
        f"{texto}</span>",
        unsafe_allow_html=True,
    )


def mensaje_error(mensaje: str, sugerencia: str | None = None) -> None:
    """Error amable, sin trazas técnicas."""

    st.error(f"⚠️ {mensaje}")
    if sugerencia:
        st.info(f"💡 {sugerencia}")


def aviso_parametros(texto: str) -> bool:
    """Explica qué hacer con una EDO parametrizada y devuelve ``True``.

    Las pestañas de resolución, análisis cualitativo y numérico trabajan con
    ecuaciones sin parámetros libres.  En lugar de mostrar un error críptico,
    dirigimos al usuario a las secciones que sí los aceptan.
    """

    try:
        candidata = parsear_con_parametros(texto)
    except EntradaInvalida:
        return False
    if not candidata.parametros:
        return False
    nombres = ", ".join(f"`{nombre}`" for nombre in candidata.parametros)
    st.info(
        f"Esta ecuación contiene parámetros ({nombres}). Configura sus "
        "distribuciones en la pestaña **Incertidumbre** o estudia la familia "
        "en **Cualitativo**. Para resolverla, asigna valores numéricos."
    )
    return True


def teclado_ayuda() -> None:
    """Ayuda de sintaxis y ejemplos dentro de un expander."""

    with st.expander("⌨️ Sintaxis y ejemplos", expanded=False):
        st.markdown(
            """
- Escribe la derivada como `y'` o `dy/dx`.
- Potencias con `^` o `**`: `x^2`, `y^2`.
- Funciones: `sin(x)`, `cos(x)`, `tan(x)`, `exp(x)`, `log(x)`, `sqrt(x)`.
- La multiplicación implícita funciona: `2x` se interpreta como `2*x`.
- La constante de integración se calcula al indicar `x₀` e `y₀`.
            """
        )
        st.code(
            "y' = x*y + sin(x)\n"
            "y' = y*(1 - y)\n"
            "y' + 2*y = exp(-x)\n"
            "2*x*y + (x^2+1)*y' = 0",
            language="text",
        )
        st.caption(
            "Sólo se admiten las variables x e y. Los parámetros simbólicos se "
            "pueden explorar en la pestaña Cualitativo."
        )


def mostrar_certificado(certificado: Certificado | None) -> None:
    """Tarjeta con el certificado de verificación."""

    if certificado is None:
        st.warning("Este resultado no incluye certificado de verificación.")
        return
    with tarjeta("Certificado de verificación", icono="🛡️"):
        badge_estado(certificado)
        columnas = st.columns(3)
        columnas[0].metric(
            "Residuo máximo",
            "—" if certificado.residuo_max is None else f"{certificado.residuo_max:.3e}",
        )
        columnas[1].metric("Método", certificado.metodo or "—")
        columnas[2].metric("Estado", certificado.estado.value.split("_")[-1])
        if certificado.dominio_valido:
            st.caption(f"Dominio declarado: {certificado.dominio_valido}")
        for nota in certificado.notas:
            st.caption(f"• {nota}")


def mostrar_pasos(pasos: Iterable[Paso], *, altura: int = 520) -> None:
    """Lista de pasos dentro de un contenedor con scroll propio."""

    pasos = list(pasos)
    if not pasos:
        st.info("No hay pasos disponibles para este resultado.")
        return
    with bloque_scroll(altura):
        for indice, paso in enumerate(pasos, start=1):
            st.markdown(f"**Paso {indice}. {paso.titulo}**")
            if paso.explicacion:
                st.write(paso.explicacion)
            if paso.latex:
                st.latex(paso.latex)
            if indice < len(pasos):
                st.divider()


def mostrar_existencia(info: InfoExistencia | None) -> None:
    """Resumen de existencia, unicidad y explosión."""

    if info is None:
        st.caption("No se ejecutó el análisis de existencia.")
        return
    if info.no_unicidad:
        st.warning(info.motivo_no_unicidad or info.resumen)
    elif info.explota:
        st.warning(info.resumen)
    elif info.lipschitz:
        st.success(info.resumen)
    else:
        st.info(info.resumen)
    if info.puntos_singularidad:
        st.caption(
            "Posibles singularidades: " + "; ".join(info.puntos_singularidad)
        )
    for nota in info.notas:
        st.caption(f"• {nota}")


def mostrar_solucion(resultado: ResultadoSolucion) -> None:
    """Encabezado, solución y advertencias de un resultado."""

    columnas = st.columns([3, 2])
    with columnas[0]:
        st.caption("Ecuación")
        st.latex(resultado.ecuacion_latex)
    with columnas[1]:
        badge_estado(resultado.certificado)
        st.caption(f"Tipo: {resultado.tipo}")
        st.caption(f"Camino: {resultado.camino}")

    if resultado.particular_latex:
        st.markdown("**Solución particular**")
        st.latex(resultado.particular_latex)
    elif resultado.general_latex:
        st.markdown("**Solución general**")
        st.latex(resultado.general_latex)
    elif resultado.solucion_latex:
        st.latex(resultado.solucion_latex)

    if resultado.general_latex and resultado.particular_latex:
        with st.expander("Ver solución general"):
            st.latex(resultado.general_latex)

    for advertencia in resultado.advertencias:
        st.warning(advertencia)


def resumen_numerico(resultado: ResultadoSolucion) -> None:
    """Métricas del respaldo numérico, si existe."""

    numerico = resultado.numerico
    if numerico is None:
        return
    columnas = st.columns(4)
    columnas[0].metric("Método", numerico.metodo or "—")
    columnas[1].metric("Puntos", f"{numerico.puntos}")
    columnas[2].metric("Evaluaciones de f", f"{numerico.f_evaluaciones}")
    columnas[3].metric(
        "Error máximo",
        "—" if numerico.error_max is None else f"{numerico.error_max:.2e}",
    )
    if numerico.rigido:
        st.warning(
            "El problema se detectó como rígido. Se recomienda BDF o Radau "
            "para intervalos largos."
        )
    if numerico.mensaje:
        st.caption(numerico.mensaje)


def titulo_pagina(titulo: str, descripcion: str, *, icono: str = "") -> None:
    """Encabezado homogéneo para cada pestaña."""

    st.markdown(f"## {icono} {titulo}".strip())
    st.caption(descripcion)


def sin_resultado() -> None:
    """Aviso estándar cuando aún no se resolvió una ecuación."""

    st.info(
        "Primero escribe una ecuación en la barra lateral y pulsa **Resolver**. "
        "También puedes cargar un ejemplo o un modelo aplicado."
    )


def metadatos_resultado(resultado: ResultadoSolucion) -> None:
    """Chips con los datos principales del resultado."""

    datos = [resultado.tipo, f"camino: {resultado.camino}"]
    if resultado.x0 is not None and resultado.y0 is not None:
        datos.append(f"y({resultado.x0:g}) = {resultado.y0:g}")
    if resultado.intervalo is not None:
        datos.append(
            f"x ∈ [{resultado.intervalo[0]:g}, {resultado.intervalo[1]:g}]"
        )
    st.markdown(
        " ".join(
            f'<span class="edo-badge edo-badge-info">{dato}</span>' for dato in datos
        ),
        unsafe_allow_html=True,
    )


__all__ = [
    "tema_actual",
    "tarjeta",
    "bloque_scroll",
    "badge_estado",
    "chip",
    "mensaje_error",
    "teclado_ayuda",
    "mostrar_certificado",
    "mostrar_pasos",
    "mostrar_existencia",
    "mostrar_solucion",
    "resumen_numerico",
    "titulo_pagina",
    "sin_resultado",
    "metadatos_resultado",
]
