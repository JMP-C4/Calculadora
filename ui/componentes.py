"""Componentes reutilizables de la interfaz Streamlit de EDO-Lab."""

from __future__ import annotations

from contextlib import contextmanager
from html import escape
from typing import Any, Iterable, Iterator

import streamlit as st

from core.notacion import (
    CLAVE_NOTACION,
    NATURAL,
    NOTACIONES,
    formatear,
    formatear_texto,
    normalizar,
)
from core.parser import parsear_con_parametros
from core.tipos import (
    Certificado,
    EntradaInvalida,
    EstadoVerificacion,
    InfoExistencia,
    Paso,
    ResultadoSolucion,
)
from ui.iconos import svg

_CONFIG_GRAFICA: dict[str, Any] = {
    "responsive": True,
    "scrollZoom": True,
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "sendDataToCloud"],
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


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
    """Bloque con borde suave, padding cómodo y encabezado vectorial."""

    with st.container(border=True):
        if titulo:
            marca = svg(icono, size=18) if icono else ""
            st.markdown(
                f'<div class="edo-titulo">{marca}<h3>{escape(str(titulo))}</h3></div>',
                unsafe_allow_html=True,
            )
        if subtitulo:
            st.caption(subtitulo)
        yield


@contextmanager
def bloque_scroll(altura: int = 480) -> Iterator[Any]:
    """Contenedor con altura máxima y barra de scroll propia."""

    st.markdown(
        '<span class="edo-marcador-scroll" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    with st.container(height=int(altura), border=False):
        yield


def lienzo(figura: Any, *, key: str | None = None, **kwargs: Any) -> Any:
    """Dibuja una figura Plotly con zoom, paneo y altura adaptada al viewport."""

    figura.update_layout(autosize=True, height=None, uirevision="edo-lab")
    st.markdown(
        '<span class="edo-marcador-lienzo" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    claves = {"key": key} if key else {}
    try:
        return st.plotly_chart(
            figura, width="stretch", config=_CONFIG_GRAFICA, **claves, **kwargs
        )
    except TypeError:  # Streamlit < 1.50
        try:
            return st.plotly_chart(
                figura,
                use_container_width=True,
                config=_CONFIG_GRAFICA,
                **claves,
                **kwargs,
            )
        except TypeError:  # Streamlit sin selección de puntos
            compat = {
                clave: valor
                for clave, valor in kwargs.items()
                if clave not in {"on_select", "selection_mode"}
            }
            return st.plotly_chart(
                figura, use_container_width=True, config=_CONFIG_GRAFICA, **claves, **compat
            )


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
        return "edo-badge-ok", "check", "Verificada simbólicamente"
    if estado == EstadoVerificacion.NUMERICA:
        return "edo-badge-warn", "alert", "Verificación numérica"
    return "edo-badge-error", "x", "No verificada"


def badge_estado(estado: Any) -> None:
    """Muestra un distintivo accesible con icono vectorial y texto."""

    clase, icono, texto = _datos_badge(estado)
    st.markdown(
        f'<span class="edo-badge {clase}">{svg(icono, size=14, etiqueta=texto)}'
        f"<span>{texto}</span></span>",
        unsafe_allow_html=True,
    )


def chip(texto: str, *, tono: str = "info", icono: str = "") -> None:
    """Etiqueta compacta para metadatos."""

    clases = {
        "info": "edo-badge-info",
        "ok": "edo-badge-ok",
        "warn": "edo-badge-warn",
        "error": "edo-badge-error",
    }
    marca = svg(icono, size=13) if icono else ""
    st.markdown(
        f'<span class="edo-badge {clases.get(tono, "edo-badge-info")}">'
        f"{marca}<span>{escape(str(texto))}</span></span>",
        unsafe_allow_html=True,
    )


def sugerencia_error(exc: Exception | str) -> str:
    """ Traduce errores del motor en una pista accionable."""

    texto = str(exc).lower()
    if "paréntesis" in texto:
        return "Revisa que todos los paréntesis estén balanceados."
    if "multiplicación" in texto or "falta un" in texto:
        return "Parece que falta un `*`: por ejemplo, escribe `2*x` en lugar de `2x`."
    if "sólo se admiten" in texto or "parámetro" in texto:
        return "Usa x, y y funciones habituales; los parámetros se exploran en Visualización."
    if "intervalo" in texto:
        return "Comprueba que x_mín < x₀ < x_máx."
    if "tiempo" in texto:
        return "El cálculo tardó demasiado; prueba un intervalo más corto o el método numérico."
    return "Revisa la ecuación y la condición inicial, o carga uno de los ejemplos."


def mensaje_error(mensaje: str, sugerencia: str | None = None) -> None:
    """Error amable, sin trazas técnicas ni iconos emoji."""

    st.error(mensaje, icon=None)
    if sugerencia:
        st.info(sugerencia, icon=None)


def aviso_parametros(texto: str) -> bool:
    """Explica qué hacer con una EDO parametrizada y devuelve ``True``."""

    try:
        candidata = parsear_con_parametros(texto)
    except EntradaInvalida:
        return False
    if not candidata.parametros:
        return False
    nombres = ", ".join(f"`{nombre}`" for nombre in candidata.parametros)
    st.info(
        f"Esta ecuación contiene parámetros ({nombres}). Configura sus "
        "distribuciones en la pestaña **Incertidumbre** de **Visualización** "
        "o estudia la familia en el lienzo. Para resolverla, asigna valores "
        "numéricos.",
        icon=None,
    )
    return True


def teclado_ayuda() -> None:
    """Ayuda de sintaxis y ejemplos dentro de un acordeón."""

    with st.expander("Sintaxis y ejemplos", expanded=False):
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
            "pueden explorar en la vista de visualización."
        )


def mostrar_certificado(
    certificado: Certificado | None, *, notacion: str | None = None
) -> None:
    """Tarjeta con el certificado de verificación."""

    if certificado is None:
        st.warning("Este resultado no incluye certificado de verificación.", icon=None)
        return
    notacion = notacion if notacion is not None else notacion_actual()
    with tarjeta("Certificado de verificación", icono="shield"):
        badge_estado(certificado)
        columnas = st.columns(3)
        columnas[0].metric(
            "Residuo máximo",
            "—" if certificado.residuo_max is None else f"{certificado.residuo_max:.3e}",
        )
        columnas[1].metric("Método", certificado.metodo or "—")
        columnas[2].metric("Estado", certificado.estado.value.split("_")[-1])
        if certificado.dominio_valido:
            st.caption(
                "Dominio declarado: "
                + formatear_texto(certificado.dominio_valido, notacion)
            )
        for nota in certificado.notas:
            st.caption("· " + formatear_texto(nota, notacion))


def mostrar_pasos(
    pasos: Iterable[Paso], *, altura: int = 520, notacion: str | None = None
) -> None:
    """Lista de pasos con explicación y fórmulas en la notación elegida."""

    notacion = notacion if notacion is not None else notacion_actual()
    pasos = list(pasos)
    if not pasos:
        st.info("No hay pasos disponibles para este resultado.", icon=None)
        return
    with bloque_scroll(altura):
        for indice, paso in enumerate(pasos, start=1):
            st.markdown(f"**Paso {indice}. {paso.titulo}**")
            if paso.explicacion:
                mostrar_texto(paso.explicacion, notacion)
            if paso.latex:
                mostrar_formula(paso.latex, None, notacion)
            if indice < len(pasos):
                st.divider()


def mostrar_existencia(
    info: InfoExistencia | None, *, notacion: str | None = None
) -> None:
    """Resumen de existencia, unicidad y explosión."""

    if info is None:
        st.caption("No se ejecutó el análisis de existencia.")
        return
    notacion = notacion if notacion is not None else notacion_actual()
    resumen = formatear_texto(info.resumen, notacion)
    if info.no_unicidad:
        motivo = formatear_texto(info.motivo_no_unicidad or info.resumen, notacion)
        st.warning(motivo, icon=None)
    elif info.explota:
        st.warning(resumen, icon=None)
    elif info.lipschitz:
        st.success(resumen, icon=None)
    else:
        st.info(resumen, icon=None)
    if info.puntos_singularidad:
        puntos = "; ".join(
            formatear_texto(punto, notacion) for punto in info.puntos_singularidad
        )
        st.caption("Posibles singularidades: " + puntos)
    for nota in info.notas:
        st.caption("· " + formatear_texto(nota, notacion))


def notacion_actual() -> str:
    """Notación vigente en la sesión, sin crear widgets."""

    return normalizar(st.session_state.get(CLAVE_NOTACION))


def selector_notacion() -> str:
    """Selector de notación, persistido en la sesión de Streamlit."""

    if CLAVE_NOTACION not in st.session_state:
        st.session_state[CLAVE_NOTACION] = NATURAL

    if hasattr(st, "segmented_control"):
        seleccion = st.segmented_control(
            "Notación",
            options=NOTACIONES,
            key=CLAVE_NOTACION,
            label_visibility="collapsed",
            help=(
                "Natural / Leibniz: Pretty Print (2D Math) con derivadas "
                "dy/dx e y′ en resultado, método, pasos, advertencias y explicación."
            ),
        )
    else:  # pragma: no cover - versiones antiguas de Streamlit
        seleccion = st.radio(
            "Notación",
            options=NOTACIONES,
            key=CLAVE_NOTACION,
            horizontal=True,
            label_visibility="collapsed",
            help="Pretty Print (2D Math) con derivadas dy/dx e y′.",
        )
    return normalizar(seleccion)


def mostrar_formula(latex: str, solucion: object | None, notacion: str) -> None:
    """Muestra una fórmula completa en la notación elegida."""

    texto, es_latex = formatear(latex, solucion, notacion)
    if not texto:
        return
    if es_latex:
        st.latex(texto)
    else:
        st.code(texto, language=None, wrap_lines=True)


def mostrar_ecuacion(latex: str, *, notacion: str | None = None) -> None:
    """Muestra una ecuación en la notación vigente, sin código crudo."""

    mostrar_formula(latex, None, notacion if notacion is not None else notacion_actual())


def mostrar_texto(texto: object, notacion: str | None = None) -> None:
    """Muestra prosa con fragmentos matemáticos en la notación elegida."""

    preparado = formatear_texto(
        texto, notacion if notacion is not None else notacion_actual()
    )
    if preparado:
        st.markdown(preparado)


def mostrar_metodos(metodos: Iterable[object], *, notacion: str | None = None) -> None:
    """Lista de clasificaciones y evidencia con la notación elegida."""

    notacion = notacion if notacion is not None else notacion_actual()
    elementos = list(metodos)
    if not elementos:
        st.info("No hay métodos aplicables para esta ecuación.", icon=None)
        return
    with bloque_scroll(280):
        for metodo in elementos:
            # Acepta ``Match`` del motor, ``TipoDetectado`` de core y etiquetas.
            nombre = str(
                getattr(metodo, "name", None)
                or getattr(metodo, "etiqueta", None)
                or metodo
                or "Método"
            )
            clave = str(
                getattr(metodo, "method", None) or getattr(metodo, "id", None) or "—"
            )
            prioridad = getattr(metodo, "priority", None)
            if prioridad is None:
                prioridad = getattr(metodo, "prioridad", None)
            etiqueta = f"**{nombre}** · `{clave}`"
            if prioridad is not None:
                etiqueta += f" · prioridad {prioridad}"
            st.markdown(etiqueta)
            evidencia = (
                getattr(metodo, "evidence", None)
                or getattr(metodo, "evidencia", None)
                or getattr(metodo, "descripcion", "")
            )
            if evidencia:
                mostrar_texto(evidencia, notacion)
            st.divider()


def mostrar_advertencias(
    advertencias: Iterable[object], *, notacion: str | None = None
) -> None:
    """Avisos del motor con la misma notación que el resto de la salida."""

    notacion = notacion if notacion is not None else notacion_actual()
    avisos = [str(aviso) for aviso in advertencias if str(aviso).strip()]
    if not avisos:
        st.success("Sin advertencias para este resultado.", icon=None)
        return
    for aviso in avisos:
        st.warning(formatear_texto(aviso, notacion), icon=None)


def mostrar_solucion(
    resultado: ResultadoSolucion, *, mostrar_selector: bool = True
) -> None:
    """Encabezado, solución y advertencias de un resultado."""

    notacion = selector_notacion() if mostrar_selector else notacion_actual()
    columnas = st.columns([3, 2])
    with columnas[0]:
        st.caption("Ecuación")
        mostrar_ecuacion(resultado.ecuacion_latex, notacion=notacion)
    with columnas[1]:
        badge_estado(resultado.certificado)
        st.caption(f"Tipo: {resultado.tipo}")
        st.caption(f"Camino: {resultado.camino}")

    solucion = resultado.solucion
    if resultado.particular_latex:
        st.markdown("**Solución particular**")
        mostrar_formula(resultado.particular_latex, solucion, notacion)
    elif resultado.general_latex:
        st.markdown("**Solución general**")
        mostrar_formula(resultado.general_latex, solucion, notacion)
    elif resultado.solucion_latex:
        mostrar_formula(resultado.solucion_latex, solucion, notacion)

    if resultado.general_latex and resultado.particular_latex:
        with st.expander("Ver solución general", expanded=False):
            mostrar_formula(resultado.general_latex, None, notacion)

    mostrar_advertencias(resultado.advertencias, notacion=notacion)


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
            "para intervalos largos.",
            icon=None,
        )
    if numerico.mensaje:
        st.caption(formatear_texto(numerico.mensaje, notacion_actual()))


def titulo_pagina(titulo: str, descripcion: str, *, icono: str = "") -> None:
    """Encabezado homogéneo para cada vista."""

    marca = svg(icono, size=22) if icono else ""
    st.markdown(
        f'<div class="edo-titulo">{marca}<h2>{escape(str(titulo))}</h2></div>',
        unsafe_allow_html=True,
    )
    st.caption(descripcion)


def sin_resultado() -> None:
    """Aviso estándar cuando aún no se resolvió una ecuación."""

    st.info(
        "Escribe una ecuación en el panel de control y pulsa **Resolver**. "
        "También puedes cargar un ejemplo o un modelo aplicado.",
        icon=None,
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
    for dato in datos:
        chip(dato)


__all__ = [
    "tema_actual",
    "tarjeta",
    "bloque_scroll",
    "lienzo",
    "badge_estado",
    "chip",
    "mensaje_error",
    "sugerencia_error",
    "teclado_ayuda",
    "mostrar_certificado",
    "mostrar_formula",
    "mostrar_ecuacion",
    "mostrar_texto",
    "mostrar_metodos",
    "mostrar_advertencias",
    "mostrar_pasos",
    "mostrar_existencia",
    "mostrar_solucion",
    "notacion_actual",
    "resumen_numerico",
    "selector_notacion",
    "titulo_pagina",
    "sin_resultado",
    "metadatos_resultado",
]
