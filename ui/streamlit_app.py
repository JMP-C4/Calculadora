"""Aplicación Streamlit de EDO-Lab: cabecera, barra lateral y pestañas."""

from __future__ import annotations

import traceback
from typing import Callable

import streamlit as st

from core.ia_opcional import estado_ia
from core.hibrido import resolver
from core.tipos import (
    EntradaInvalida,
    ResultadoSolucion,
    SolucionNoDisponible,
    TiempoAgotado,
)

from ui import estilos
from ui.componentes import mensaje_error, tarjeta, teclado_ayuda, tema_actual
from ui.pagina_aprendizaje import render as render_aprendizaje
from ui.pagina_cualitativo import render as render_cualitativo
from ui.pagina_datos import render as render_datos
from ui.pagina_incertidumbre import render as render_incertidumbre
from ui.pagina_informes import render as render_informes
from ui.pagina_numerico import render as render_numerico
from ui.pagina_resolver import render as render_resolver

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


def _sugerencia_error(exc: Exception) -> str:
    texto = str(exc).lower()
    if "paréntesis" in texto:
        return "Revisa que todos los paréntesis estén balanceados."
    if "multiplicación" in texto or "falta un" in texto:
        return "Parece que falta un `*`: por ejemplo, escribe `2*x` en lugar de `2x`."
    if "sólo se admiten" in texto:
        return "Usa únicamente x, y y funciones habituales; los parámetros se exploran aparte."
    if "intervalo" in texto:
        return "Comprueba que x_mín < x₀ < x_máx."
    if "tiempo" in texto:
        return "El cálculo tardó demasiado; prueba un intervalo más corto o el método numérico."
    return "Revisa la ecuación y la condición inicial, o carga uno de los ejemplos."


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
    except EntradaInvalida as exc:
        st.session_state["error_resolver"] = str(exc)
        st.session_state["resultado"] = None
        return
    except SolucionNoDisponible as exc:
        st.session_state["error_resolver"] = str(exc)
        st.session_state["resultado"] = None
        return
    except TiempoAgotado as exc:
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


def _cabecera() -> None:
    columnas = st.columns([5, 3, 2], vertical_alignment="center")
    with columnas[0]:
        st.markdown(
            '<div class="edo-marca">🧪 EDO-Lab</div>'
            '<div class="edo-lema">Laboratorio inteligente de ecuaciones '
            "diferenciales de primer orden</div>",
            unsafe_allow_html=True,
        )
    with columnas[1]:
        st.caption("«La IA propone, el motor matemático comprueba.»")
    with columnas[2]:
        st.toggle("🌙 Tema oscuro", key="tema_oscuro")


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
        st.markdown("### 🧭 Panel de control")
        st.caption("Una tarea por pestaña. Los resultados se conservan al cambiar de pestaña.")

        st.markdown("#### 1 · Ecuación")
        st.text_area(
            "EDO",
            key="ecuacion_input",
            height=92,
            help="Escribe y' = f(x, y) o dy/dx = f(x, y).",
        )
        ejemplo = st.selectbox(
            "Ejemplos precargados",
            options=["—"] + list(_EJEMPLOS),
            key="ejemplo_selector",
        )
        if st.button("Cargar ejemplo", key="cargar_ejemplo", use_container_width=True):
            if ejemplo != "—":
                _aplicar_ejemplo(ejemplo)
                st.rerun()

        st.markdown("#### 2 · Condición inicial")
        columnas = st.columns(2)
        columnas[0].number_input("x₀", key="x0_input", format="%.6g")
        columnas[1].number_input("y₀", key="y0_input", format="%.6g")

        st.markdown("#### 3 · Intervalo")
        columnas = st.columns(2)
        columnas[0].number_input("x mínimo", key="x_min_input", format="%.6g")
        columnas[1].number_input("x máximo", key="x_max_input", format="%.6g")

        st.markdown("#### 4 · Método")
        st.selectbox(
            "Método numérico de respaldo",
            options=["Automático", "RK45", "DOP853", "BDF", "Radau", "RK4", "Heun", "Euler"],
            key="metodo_input",
        )

        if st.button("🚀 Resolver", key="resolver_boton", type="primary", use_container_width=True):
            _resolver_actual()

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
                st.success(f"IA opcional activa ({estado.modelo}).")
            else:
                st.caption("IA opcional desactivada.")

        historial = st.session_state.get("historial", [])
        if historial:
            st.markdown("#### 🕘 Historial")
            with st.container(height=220, border=True):
                for indice, entrada in enumerate(historial[:10]):
                    etiqueta = f"{entrada['ecuacion']} · y({entrada['x0']:g})={entrada['y0']:g}"
                    if st.button(etiqueta, key=f"hist_{indice}", use_container_width=True):
                        st.session_state["_cargar_ecuacion"] = {
                            "ecuacion": entrada["ecuacion"],
                            "x0": entrada["x0"],
                            "y0": entrada["y0"],
                            "x_min": entrada["x_min"],
                            "x_max": entrada["x_max"],
                        }
                        st.rerun()

        teclado_ayuda()


def _render_seguro(nombre: str, funcion: Callable[[], None]) -> None:
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
    st.set_page_config(
        page_title="EDO-Lab",
        page_icon="🧪",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inicializar_estado()
    _aplicar_pendientes()
    st.markdown(estilos.css(tema_actual()), unsafe_allow_html=True)
    _cabecera()
    st.markdown(estilos.css(tema_actual()), unsafe_allow_html=True)
    _barra_lateral()

    if st.session_state.pop("_resolver_automatico", False):
        _resolver_actual()

    pestañas = st.tabs(
        [
            "🧮 Resolver",
            "🧭 Cualitativo",
            "📐 Numérico",
            "📊 Datos",
            "🎲 Incertidumbre",
            "🎓 Aprender",
            "📄 Informes",
        ]
    )
    with pestañas[0]:
        _render_seguro("Resolver", render_resolver)
    with pestañas[1]:
        _render_seguro("Cualitativo", render_cualitativo)
    with pestañas[2]:
        _render_seguro("Numérico", render_numerico)
    with pestañas[3]:
        _render_seguro("Datos", render_datos)
    with pestañas[4]:
        _render_seguro("Incertidumbre", render_incertidumbre)
    with pestañas[5]:
        _render_seguro("Aprender", render_aprendizaje)
    with pestañas[6]:
        _render_seguro("Informes", render_informes)

    estado = estado_ia()
    st.markdown(
        '<div class="edo-pie">EDO-Lab · núcleo determinista · '
        f"IA opcional: {'activa' if estado.activa else 'desactivada'} · "
        "los resultados se recalculan sólo cuando lo pides."
        "</div>",
        unsafe_allow_html=True,
    )


__all__ = ["main"]
