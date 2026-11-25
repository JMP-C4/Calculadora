"""Aplicación Streamlit de EDO-Lab: cabecera, navegación e inspector."""

from __future__ import annotations

import traceback
from pathlib import Path

import streamlit as st

from core.ia_opcional import estado_ia
from core.hibrido import resolver
from core.tipos import EntradaInvalida, SolucionNoDisponible, TiempoAgotado

from ui import estilos, navegacion, vistas
from ui.componentes import (
    mensaje_error,
    tarjeta,
    teclado_ayuda,
    tema_actual,
)
from ui.iconos import svg

_EJEMPLOS = {
    "logística": {
        "ecuacion": "y' = y*(1-y)",
        "x0": 0.0,
        "y0": 0.2,
        "x_min": 0.0,
        "x_max": 10.0,
    },
    "lineal": {
        "ecuacion": "y' + y = x",
        "x0": 0.0,
        "y0": 1.0,
        "x_min": 0.0,
        "x_max": 5.0,
    },
    "separable": {
        "ecuacion": "y' = x*y",
        "x0": 0.0,
        "y0": 1.0,
        "x_min": -2.0,
        "x_max": 2.0,
    },
    "exacta": {
        "ecuacion": "2*x*y + (x^2+1)*y' = 0",
        "x0": 0.0,
        "y0": 1.0,
        "x_min": -2.0,
        "x_max": 2.0,
    },
    "explosión": {
        "ecuacion": "y' = y^2",
        "x0": 0.0,
        "y0": 1.0,
        "x_min": 0.0,
        "x_max": 1.5,
    },
    "sin unicidad": {
        "ecuacion": "y' = y^(1/3)",
        "x0": 0.0,
        "y0": 0.0,
        "x_min": 0.0,
        "x_max": 2.0,
    },
    "sin forma cerrada": {
        "ecuacion": "y' = x*y + sin(x)",
        "x0": 0.0,
        "y0": 1.0,
        "x_min": 0.0,
        "x_max": 3.0,
    },
    "enfriamiento": {
        "ecuacion": "y' = -0.08*(y - 20)",
        "x0": 0.0,
        "y0": 90.0,
        "x_min": 0.0,
        "x_max": 60.0,
    },
}


def _inicializar_estado() -> None:
    valores = {
        "ecuacion_input": "y' = y*(1-y)",
        "x0_input": 0.0,
        "y0_input": 0.2,
        "x_min_input": 0.0,
        "x_max_input": 10.0,
        "metodo_input": "Automático",
        "resultado": None,
        "error_resolver": None,
        "historial": [],
        "intervalo_actual": None,
        "tema_oscuro": False,
        "semilla_global": 42,
        "curva_clic": None,
        "punto_clic": None,
        "explicacion_resultado": None,
        "informe_pdf": None,
        "informe_latex": None,
        "num_resultados": None,
        "num_convergencia": None,
        "num_benchmark": None,
        "num_rigidez": None,
        "datos_ajuste": None,
        "datos_origen": None,
        "ajustes_datos": None,
        "mejor_ajuste": None,
        "prediccion_datos": None,
        "inci_mc": None,
        "sobol_resultado": None,
    }
    for clave, valor in valores.items():
        st.session_state.setdefault(clave, valor)


def _aplicar_pendientes() -> None:
    pendiente = st.session_state.pop("_cargar_ecuacion", None)
    if isinstance(pendiente, dict):
        if "ecuacion" in pendiente:
            st.session_state["ecuacion_input"] = str(pendiente["ecuacion"])
        for clave in ("x0", "y0", "x_min", "x_max"):
            if clave in pendiente:
                st.session_state[f"{clave}_input"] = float(pendiente[clave])
        st.session_state["curva_clic"] = None
        st.session_state["punto_clic"] = None
    if st.session_state.pop("_solicitar_resolver", False):
        st.session_state["_resolver_automatico"] = True


def _resolver_actual(*, guardar: bool = True) -> None:
    texto = str(st.session_state.get("ecuacion_input", "")).strip()
    if not texto:
        st.session_state["error_resolver"] = "Escribe una ecuación diferencial."
        st.session_state["resultado"] = None
        return
    try:
        x0 = float(st.session_state.get("x0_input", 0.0))
        y0 = float(st.session_state.get("y0_input", 1.0))
        x_min = float(st.session_state.get("x_min_input", 0.0))
        x_max = float(st.session_state.get("x_max_input", 5.0))
        metodo = st.session_state.get("metodo_input", "Automático")
        metodo = None if metodo in (None, "Automático") else str(metodo)
        with st.spinner("Resolviendo y verificando con el motor…"):
            resultado = resolver(
                texto,
                x0=x0,
                y0=y0,
                x_min=x_min,
                x_max=x_max,
                metodo=metodo,
                timeout=10.0,
            )
    except (EntradaInvalida, SolucionNoDisponible, TiempoAgotado) as exc:
        st.session_state["error_resolver"] = str(exc)
        st.session_state["resultado"] = None
        return
    except Exception:
        traceback.print_exc()
        st.session_state["error_resolver"] = (
            "Ocurrió un error inesperado al resolver. El motor no pudo "
            "completar el cálculo; prueba con otra ecuación o intervalo."
        )
        st.session_state["resultado"] = None
        return

    st.session_state["resultado"] = resultado
    st.session_state["error_resolver"] = None
    st.session_state["intervalo_actual"] = (x_min, x_max)
    st.session_state["curva_clic"] = None
    st.session_state["punto_clic"] = None
    st.session_state["explicacion_resultado"] = None
    st.session_state["informe_pdf"] = None
    st.session_state["informe_latex"] = None
    st.session_state["num_resultados"] = None
    st.session_state["num_convergencia"] = None
    st.session_state["num_benchmark"] = None
    st.session_state["num_rigidez"] = None
    if guardar:
        entrada = {
            "ecuacion": texto,
            "x0": x0,
            "y0": y0,
            "x_min": x_min,
            "x_max": x_max,
            "tipo": resultado.tipo,
            "camino": resultado.camino,
        }
        historial = [
            item
            for item in st.session_state.get("historial", [])
            if not (
                item.get("ecuacion") == texto
                and item.get("x0") == x0
                and item.get("y0") == y0
                and item.get("x_min") == x_min
                and item.get("x_max") == x_max
            )
        ]
        historial.insert(0, entrada)
        st.session_state["historial"] = historial[:12]

    navegacion.establecer_vista("Salida")
    st.rerun()


def _ir_a_graficas() -> None:
    """El selector de la cabecera abre siempre la vista de visualización."""

    navegacion.establecer_vista("Visualización")


def _ir_al_ejercicio() -> None:
    """Vuelve a la vista donde se muestra el ejercicio resuelto."""

    vista = "Salida" if st.session_state.get("resultado") is not None else "Calculadora"
    navegacion.establecer_vista(vista)


def _instrucciones() -> None:
    """Guía rápida de uso, accesible desde la cabecera."""

    st.markdown(
        """
        1. Escribe la ecuación en el inspector con `y'` o `dy/dx`.
        2. Indica `x₀` e `y₀` juntos si quieres una solución particular.
        3. Pulsa **Resolver**: el motor verifica la solución antes de mostrarla.
        4. Usa **Gráficas** para explorar el lienzo y **Ver ejercicio** para
           volver a la salida del problema resuelto.
        5. En **Salida** puedes elegir la notación; se aplica a todas las vistas.
        6. El historial, la teoría, los ejercicios y los informes están en
           **Historial y teoría**.
        """
    )
    teclado_ayuda()


def _cabecera() -> None:
    columnas = st.columns([5, 1.2, 3.4], vertical_alignment="center", gap="small")
    with columnas[0]:
        st.markdown(
            f'<div class="edo-marca">{svg("activity", size=22)}'
            "<span>EDO-Lab</span></div>"
            '<div class="edo-lema">Laboratorio de ecuaciones diferenciales '
            "de primer orden</div>",
            unsafe_allow_html=True,
        )
    with columnas[1]:
        st.toggle("Tema oscuro", key="tema_oscuro")
    with columnas[2]:
        botones = st.columns([1, 1.1, 1.1], gap="small")
        with botones[0]:
            st.button(
                "Gráficas",
                key="edo_boton_graficas",
                help="Abre el lienzo de visualización.",
                on_click=_ir_a_graficas,
            )
        with botones[1]:
            st.button(
                "Ver ejercicio",
                key="edo_boton_ejercicio",
                help="Vuelve a la salida del ejercicio resuelto.",
                on_click=_ir_al_ejercicio,
            )
        with botones[2]:
            with st.popover("Instrucciones"):
                _instrucciones()


def _aplicar_ejemplo(nombre: str) -> None:
    datos = _EJEMPLOS[nombre]
    st.session_state["_cargar_ecuacion"] = {
        "ecuacion": datos["ecuacion"],
        "x0": datos["x0"],
        "y0": datos["y0"],
        "x_min": datos["x_min"],
        "x_max": datos["x_max"],
    }
    st.session_state["_solicitar_resolver"] = True


def _barra_lateral() -> None:
    with st.sidebar:
        st.markdown(
            f'<div class="edo-titulo">{svg("sliders", size=18)}'
            "<h3>Inspector</h3></div>",
            unsafe_allow_html=True,
        )
        st.caption("Los resultados se conservan al cambiar de vista.")

        st.text_area(
            "Ecuación diferencial",
            key="ecuacion_input",
            height=96,
            help="Escribe y' = f(x, y) o dy/dx = f(x, y).",
        )
        columnas = st.columns(2)
        columnas[0].number_input("x₀", key="x0_input", format="%.6g")
        columnas[1].number_input("y₀", key="y0_input", format="%.6g")

        if st.button("Resolver", key="resolver_boton", type="primary"):
            _resolver_actual()

        with st.expander("Intervalo y método", expanded=False):
            intervalo = st.columns(2)
            intervalo[0].number_input("x mínimo", key="x_min_input", format="%.6g")
            intervalo[1].number_input("x máximo", key="x_max_input", format="%.6g")
            st.selectbox(
                "Método numérico de respaldo",
                options=[
                    "Automático",
                    "RK45",
                    "DOP853",
                    "BDF",
                    "Radau",
                    "RK4",
                    "Heun",
                    "Euler",
                ],
                key="metodo_input",
            )

        with tarjeta("Ejemplos", icono="folder"):
            ejemplo = st.selectbox(
                "Ejemplo precargado",
                options=["—"] + list(_EJEMPLOS),
                key="ejemplo_selector",
            )
            if st.button(
                "Cargar ejemplo", key="cargar_ejemplo", use_container_width=True
            ):
                if ejemplo != "—":
                    _aplicar_ejemplo(ejemplo)
                    st.rerun()

        with st.expander("Opciones avanzadas", expanded=False):
            st.number_input(
                "Semilla global",
                min_value=0,
                step=1,
                key="semilla_global",
                help="Se usa en Monte Carlo, Sobol y ejercicios para reproducir resultados.",
            )
            st.caption(
                "Los cálculos simbólicos tienen un límite de 10 s y degradan a "
                "integración numérica."
            )
            estado = estado_ia()
            if estado.activa:
                st.success(f"IA opcional activa ({estado.modelo}).", icon=None)
            else:
                st.caption("IA opcional desactivada.")

        teclado_ayuda()
        if st.button("Ver historial y teoría", key="inspector_ir_historial"):
            navegacion.ir_a("Historial y teoría")


def _render_seguro(nombre: str, funcion) -> None:
    try:
        funcion()
    except Exception:
        traceback.print_exc()
        mensaje_error(
            f"La sección «{nombre}» no pudo mostrarse.",
            "Revisa la ecuación, el intervalo y los parámetros; el resto de la "
            "aplicación sigue disponible.",
        )


def main() -> None:
    icono = str(Path(__file__).with_name("favicon.svg"))
    st.set_page_config(
        page_title="EDO-Lab",
        page_icon=icono,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inicializar_estado()
    _aplicar_pendientes()
    st.markdown(estilos.css(tema_actual()), unsafe_allow_html=True)
    _cabecera()
    vista = navegacion.barra()
    _barra_lateral()

    if st.session_state.pop("_resolver_automatico", False):
        _resolver_actual()

    _render_seguro(vista, lambda: vistas.despachar(vista))
    vistas.pie()


__all__ = ["main"]
