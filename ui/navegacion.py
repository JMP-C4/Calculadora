"""Navegación principal de EDO-Lab con estado compartible por URL.

La vista activa se guarda en ``st.query_params["vista"]`` de modo que un
estudiante pueda enlazar directamente a la salida, al lienzo, a los pasos o al
historial.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

VISTAS: tuple[str, ...] = (
    "Calculadora",
    "Salida",
    "Visualización",
    "Paso a paso",
    "Historial y teoría",
)

_SLUGS: dict[str, str] = {
    "Calculadora": "calculadora",
    "Salida": "salida",
    "Visualización": "visualizacion",
    "Paso a paso": "paso-a-paso",
    "Historial y teoría": "historial",
}
_POR_SLUG: dict[str, str] = {slug: vista for vista, slug in _SLUGS.items()}
_CLAVE = "vista_activa"
_CLAVE_NAV = "edo_vista_nav"
_CLAVE_SINCRONIZADA = "_edo_vista_sincronizada"
_CLAVE_PENDIENTE = "_edo_vista_pendiente"


def normalizar(valor: Any) -> str | None:
    """Convierte un nombre o slug en una vista conocida."""

    if valor is None:
        return None
    if isinstance(valor, (list, tuple)):
        valor = valor[0] if valor else None
    if valor is None:
        return None
    texto = str(valor).strip()
    if texto in VISTAS:
        return texto
    return _POR_SLUG.get(texto.lower())


def vista_actual() -> str:
    """Vista seleccionada, priorizando el parámetro de la URL."""

    valor = normalizar(st.query_params.get("vista"))
    if valor is not None:
        return valor
    valor = normalizar(st.session_state.get(_CLAVE))
    return valor or VISTAS[0]


def establecer_vista(vista: Any, *, diferir: bool = True) -> str:
    """Fija la vista activa y actualiza la URL sin recursión."""

    destino = normalizar(vista) or VISTAS[0]
    st.session_state[_CLAVE] = destino
    st.session_state[f"_{_CLAVE}_sincronizada"] = destino
    # ``establecer_vista`` también se llama después de instanciar el widget
    # (al resolver o al abrir una gráfica). Se difiere la sincronización a la
    # siguiente ejecución, donde ``barra()`` puede escribir la clave del widget
    # antes de volver a crearlo sin descartar un cambio del usuario.
    if diferir:
        st.session_state[_CLAVE_PENDIENTE] = destino
    st.query_params["vista"] = _SLUGS[destino]
    return destino


def ir_a(vista: Any) -> None:
    """Cambia de vista y vuelve a ejecutar la aplicación."""

    establecer_vista(vista)
    st.rerun()


def _selector(
    etiqueta: str,
    opciones: tuple[str, ...],
    actual: str,
    *,
    clave: str,
) -> str:
    # Si la sesión ya trae un valor, no se pasa ``default``/``index``:
    # Streamlit avisaría de que el widget recibe dos valores iniciales.
    inicializado = clave in st.session_state
    if hasattr(st, "segmented_control"):
        opciones_widget = {"default": actual} if not inicializado else {}
        seleccion = st.segmented_control(
            etiqueta,
            options=list(opciones),
            key=clave,
            **opciones_widget,
        )
    else:  # Streamlit anterior a 1.44
        opciones_widget = {"index": opciones.index(actual)} if not inicializado else {}
        seleccion = st.radio(
            etiqueta,
            options=list(opciones),
            horizontal=True,
            key=clave,
            **opciones_widget,
        )
    return normalizar(seleccion) or actual


def _sincronizar(clave: str, valor: str) -> None:
    """Fuerza el widget a seguir a la vista resuelta, no a un valor anterior.

    Streamlit conserva el valor de los widgets entre ejecuciones. Sin esta
    sincronización, una visita previa podía imponer una vista distinta a la de
    la URL compartida y provocar una cadena de ``rerun`` que nunca convergía.
    """

    clave_sync = f"_{clave}_sincronizada"
    if st.session_state.get(clave_sync) != valor:
        st.session_state[clave] = valor
        st.session_state[clave_sync] = valor


def barra() -> str:
    """Dibuja la navegación superior y devuelve la vista activa."""

    actual = vista_actual()
    pendiente = st.session_state.pop(_CLAVE_PENDIENTE, None)
    if pendiente is not None:
        st.session_state[_CLAVE_NAV] = pendiente
        st.session_state[f"_{_CLAVE_NAV}_sincronizada"] = pendiente
    else:
        _sincronizar(_CLAVE_NAV, actual)
    st.markdown(
        '<span class="edo-nav-marker" aria-hidden="true"></span>',
        unsafe_allow_html=True,
    )
    elegida = _selector("Vista", VISTAS, actual, clave=_CLAVE_NAV)

    # Sin rerun: ``main`` despacha la vista elegida en esta misma ejecución.
    if elegida != actual:
        establecer_vista(elegida, diferir=False)
        # El usuario ya dejó el widget en este valor: marcarlo como sincronizado
        # evita que la siguiente ejecución lo reescriba con la URL anterior.
        st.session_state[f"_{_CLAVE_NAV}_sincronizada"] = elegida
    return elegida


def selector_interno(
    etiqueta: str,
    opciones: tuple[str, ...],
    *,
    parametro: str,
    defecto: str | None = None,
) -> str:
    """Selector secundario sincronizado con ``?parametro=``."""

    validas = tuple(opciones)
    preferida = defecto or validas[0]
    solicitada = st.query_params.get(parametro)
    if isinstance(solicitada, (list, tuple)):
        solicitada = solicitada[0] if solicitada else None
    valor = (
        solicitada
        if solicitada in validas
        else next(
            (opcion for opcion in validas if opcion.lower() == str(solicitada).lower()),
            preferida,
        )
    )
    clave = f"edo_{parametro}"
    _sincronizar(clave, valor)
    elegida = _selector(etiqueta, validas, valor, clave=clave)
    if elegida != valor:
        st.query_params[parametro] = elegida.lower().replace(" ", "-").replace("ó", "o")
    return elegida


__all__ = [
    "VISTAS",
    "barra",
    "establecer_vista",
    "ir_a",
    "normalizar",
    "selector_interno",
    "vista_actual",
]
