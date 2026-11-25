"""Secciones reutilizables del flujo Resolver.

El resultado se divide en cinco vistas (calculadora, salida, lienzo,
procedimiento e historial) y en piezas pequeñas que pueden combinarse sin
duplicar lógica.
"""

from __future__ import annotations

import numpy as np
import streamlit as st

from core.clasificador import clasificar
from core.cualitativo import (
    comportamiento_asintotico,
    datos_isoclinas,
    equilibrios,
    es_autonoma,
)
from core.hibrido import (
    curva_desde_punto,
    curvas_familia,
    curva_solucion,
    evaluar_solucion,
)
from core.ia_opcional import estado_ia, explicar_resultado
from core.modelos import MODELOS, instanciar_modelo
from core.notacion import formatear_texto
from core.parser import parsear
from core.tipos import EntradaInvalida

from ui.componentes import (
    bloque_scroll,
    lienzo,
    mensaje_error,
    metadatos_resultado,
    mostrar_advertencias,
    mostrar_certificado,
    mostrar_ecuacion,
    mostrar_existencia,
    mostrar_formula,
    mostrar_metodos,
    mostrar_pasos,
    mostrar_solucion,
    mostrar_texto,
    notacion_actual,
    resumen_numerico,
    selector_notacion,
    sin_resultado,
    sugerencia_error,
    tarjeta,
    tema_actual,
    titulo_pagina,
)
from ui.graficas import (
    CLAVE_GRAFICA,
    GRAFICAS,
    figura_campo_direcciones,
    figura_familia,
    figura_fase,
    figura_isoclinas,
    figura_solucion,
    figura_superficie,
)
from ui.navegacion import establecer_vista


def resultado_actual(*, avisar_error: bool = True) -> object | None:
    """Devuelve el resultado vigente y muestra errores pendientes."""

    error = st.session_state.get("error_resolver")
    if error and avisar_error:
        mensaje_error(str(error), sugerencia_error(error))
    return st.session_state.get("resultado")


def _puntos_seleccion(evento: object) -> list[object]:
    seleccion = getattr(evento, "selection", None)
    if seleccion is None and isinstance(evento, dict):
        seleccion = evento.get("selection", {})
    if seleccion is None:
        return []
    if hasattr(seleccion, "get"):
        crudos = seleccion.get("points", [])
    else:
        crudos = getattr(seleccion, "points", [])
    return list(crudos or [])


def _coordenada(punto: object, eje: str) -> float | None:
    if isinstance(punto, dict):
        valor = punto.get(eje)
    else:
        valor = getattr(punto, eje, None)
    try:
        return None if valor is None else float(valor)
    except (TypeError, ValueError):
        return None


def _anadir_curva_clic(figura) -> None:
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


def seccion_campo(resultado) -> None:
    """Campo de direcciones con curva opcional desde un clic."""

    try:
        ecuacion = parsear(resultado.ecuacion_texto)
    except EntradaInvalida:
        return
    if resultado.intervalo is None:
        return
    x_min, x_max = resultado.intervalo

    y_actual = (
        resultado.numerico.y if resultado.numerico is not None else np.asarray([])
    )
    if y_actual.size:
        finitos = y_actual[np.isfinite(y_actual)]
        centro = float(np.median(finitos)) if finitos.size else 0.0
        amplitud = max(3.0, float(np.ptp(finitos)) if finitos.size else 6.0)
    else:
        centro = float(resultado.y0 or 0.0)
        amplitud = 5.0
    margen = 0.6 * amplitud
    y_min, y_max = centro - margen, centro + margen
    if y_min == y_max:
        y_min, y_max = -5.0, 5.0

    activar_clic = st.checkbox(
        "Trazar curva haciendo clic en el campo",
        key="activar_clic_campo",
        help="Haz clic sobre un punto del campo para integrar la curva que pasa por él.",
    )
    figura = figura_campo_direcciones(
        ecuacion.rhs,
        float(x_min),
        float(x_max),
        y_min,
        y_max,
        n=23,
        seleccionable=activar_clic,
        tema_oscuro=tema_actual(),
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
    _anadir_curva_clic(figura)

    if activar_clic:
        evento = lienzo(
            figura,
            on_select="rerun",
            selection_mode="points",
            key="grafico_campo_clic",
        )
        puntos = _puntos_seleccion(evento)
        if puntos:
            x_punto = _coordenada(puntos[0], "x")
            y_punto = _coordenada(puntos[0], "y")
            if x_punto is not None and y_punto is not None:
                anterior = st.session_state.get("punto_clic")
                if (
                    anterior is None
                    or abs(anterior[0] - x_punto) > 1e-9
                    or abs(anterior[1] - y_punto) > 1e-9
                ):
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
                            "otro punto del campo.",
                            icon=None,
                        )
        if st.session_state.get("curva_clic") is not None:
            st.caption("La curva roja se integró desde el último punto seleccionado.")
            if st.button("Limpiar traza del campo", key="limpiar_clic"):
                st.session_state["curva_clic"] = None
                st.session_state["punto_clic"] = None
                st.rerun()
    else:
        lienzo(figura)


def seccion_solucion_grafica(resultado) -> None:
    """Curva de solución con zoom, paneo y altura fluida."""

    lienzo(figura_solucion(resultado, tema_oscuro=tema_actual()))
    st.caption("Arrastra para desplazarte y usa la rueda para acercar o alejar.")


def grafica_activa() -> str:
    """Gráfica elegida en el selector «Tipo de gráfica» de Visualización."""

    modo = st.session_state.get(CLAVE_GRAFICA, GRAFICAS[0])
    return str(modo) if str(modo) in GRAFICAS else GRAFICAS[0]


def _rango_y(resultado) -> tuple[float, float]:
    """Rango vertical sugerido por la trayectoria numérica del resultado."""

    y_actual = (
        resultado.numerico.y if resultado.numerico is not None else np.asarray([])
    )
    if y_actual.size:
        finitos = y_actual[np.isfinite(y_actual)]
        centro = float(np.median(finitos)) if finitos.size else 0.0
        amplitud = max(3.0, float(np.ptp(finitos)) if finitos.size else 6.0)
    else:
        centro = float(resultado.y0 or 0.0)
        amplitud = 6.0
    margen = 0.6 * amplitud
    y_min, y_max = centro - margen, centro + margen
    return (y_min, y_max) if y_min != y_max else (-5.0, 5.0)


def _datos_malla(
    resultado, *, y_min: float | None = None, y_max: float | None = None
):
    """Malla ``f(x, y)`` para isóclinas y superficie 3D."""

    try:
        ecuacion = parsear(resultado.ecuacion_texto)
    except EntradaInvalida:
        return None
    if resultado.intervalo is None:
        x_min, x_max = -5.0, 5.0
    else:
        x_min, x_max = resultado.intervalo
    if x_min >= x_max:
        return None
    inferior, superior = _rango_y(resultado)
    try:
        return datos_isoclinas(
            ecuacion.rhs,
            x_min=float(x_min),
            x_max=float(x_max),
            y_min=float(y_min if y_min is not None else inferior),
            y_max=float(y_max if y_max is not None else superior),
        )
    except Exception:
        return None


def _datos_autonomos(
    resultado, *, y_min: float = -5.0, y_max: float = 5.0
):
    """Lado derecho y equilibrios de una EDO autónoma."""

    try:
        ecuacion = parsear(resultado.ecuacion_texto)
    except EntradaInvalida:
        return None
    if not es_autonoma(ecuacion.rhs):
        return None
    return ecuacion.rhs, equilibrios(ecuacion.rhs, y_min=y_min, y_max=y_max)


def seccion_graficas(resultado) -> None:
    """Lienzo protagonista, con el modo elegido en esta vista."""

    st.selectbox(
        "Tipo de gráfica",
        options=GRAFICAS,
        key=CLAVE_GRAFICA,
    )
    modo = grafica_activa()
    st.caption(
        f"Gráfica: {modo}. Arrastra para desplazarte y usa la rueda para acercar o alejar."
    )
    if modo == "Solución y(x)":
        seccion_solucion_grafica(resultado)
    elif modo == "Campo de direcciones":
        seccion_campo(resultado)
    elif modo == "Isoclinas":
        datos = _datos_malla(resultado, y_min=-6.0, y_max=6.0)
        if datos is None:
            st.info("No se pudieron calcular las isóclinas de esta ecuación.", icon=None)
        else:
            lienzo(
                figura_isoclinas(datos, tema_oscuro=tema_actual()),
                key="grafica_isoclinas",
            )
            st.caption(datos.nota)
    elif modo == "Familia de curvas":
        curvas = curvas_familia(resultado)
        if not curvas:
            st.info(
                "Esta solución no expone una constante de integración libre.",
                icon=None,
            )
        else:
            lienzo(
                figura_familia(curvas, tema_oscuro=tema_actual()),
                key="grafica_familia",
            )
            st.caption("Cada curva corresponde a un valor distinto de la constante C.")
    elif modo in ("Línea de fase", "Puntos de equilibrio"):
        datos = _datos_autonomos(resultado)
        if datos is None:
            st.info(
                "La línea de fase y los equilibrios requieren una ecuación "
                "autónoma y' = f(y).",
                icon=None,
            )
        else:
            rhs, puntos = datos
            if modo == "Puntos de equilibrio":
                filas = [
                    {
                        "y*": f"{punto.valor:.6g}",
                        "Estabilidad": punto.estabilidad,
                        "f'(y*)": "—" if punto.f_prima is None else f"{punto.f_prima:.6g}",
                    }
                    for punto in puntos
                ]
                if filas:
                    st.dataframe(filas, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay equilibrios reales en el rango elegido.", icon=None)
            lienzo(
                figura_fase(rhs, puntos, tema_oscuro=tema_actual()),
                key="grafica_fase",
            )
    elif modo == "Superficie 3D z = f(x,y)":
        datos = _datos_malla(resultado)
        if datos is None:
            st.info("No se pudo construir la superficie de esta ecuación.", icon=None)
        else:
            lienzo(
                figura_superficie(datos, tema_oscuro=tema_actual()),
                key="grafica_superficie",
            )
            st.caption("Arrastra para girar la superficie y usa la rueda para acercar.")


def seccion_solucion(resultado, *, mostrar_selector: bool = True) -> None:
    """Resultado analítico o numérico con metadatos."""

    with tarjeta("Resultado", icono="pin"):
        mostrar_solucion(resultado, mostrar_selector=mostrar_selector)
        metadatos_resultado(resultado)


def seccion_metodos(resultado, *, notacion: str | None = None) -> None:
    """Clasificaciones compatibles y método elegido."""

    notacion = notacion if notacion is not None else notacion_actual()
    st.markdown("#### Métodos aplicables")
    st.caption(f"Método elegido: {resultado.tipo}")
    try:
        metodos = clasificar(resultado.ecuacion_texto)
    except Exception:  # pragma: no cover - la ecuación ya fue resuelta
        metodos = list(getattr(resultado, "tipos", ()) or ())
    mostrar_metodos(metodos, notacion=notacion)


def seccion_pasos(resultado, *, notacion: str | None = None) -> None:
    """Procedimiento analítico paso a paso."""

    notacion = notacion if notacion is not None else notacion_actual()
    st.markdown("#### Procedimiento paso a paso")
    mostrar_pasos(resultado.pasos, altura=520, notacion=notacion)


def seccion_advertencias(resultado, *, notacion: str | None = None) -> None:
    """Advertencias y avisos del motor con la notación elegida."""

    notacion = notacion if notacion is not None else notacion_actual()
    st.markdown("#### Advertencias")
    mostrar_advertencias(resultado.advertencias, notacion=notacion)


def seccion_certificado(resultado, *, notacion: str | None = None) -> None:
    """Certificado de verificación."""

    mostrar_certificado(resultado.certificado, notacion=notacion)


def seccion_detalles(resultado, *, notacion: str | None = None) -> None:
    """Detalles numéricos y análisis de existencia en acordeones."""

    notacion = notacion if notacion is not None else notacion_actual()
    columnas = st.columns(2)
    with columnas[0]:
        with st.expander("Existencia, unicidad y explosión", expanded=False):
            mostrar_existencia(resultado.existencia, notacion=notacion)
    with columnas[1]:
        with st.expander("Detalles numéricos", expanded=False):
            if resultado.numerico is None:
                st.caption("No se ejecutó integración numérica.")
            else:
                resumen_numerico(resultado)
                if resultado.numerico.exito:
                    with bloque_scroll(240):
                        st.dataframe(
                            {"x": resultado.numerico.x, "y": resultado.numerico.y},
                            use_container_width=True,
                        )


def seccion_asintotico(resultado, *, notacion: str | None = None) -> None:
    """Comportamiento asintótico cuando la EDO es autónoma."""

    notacion = notacion if notacion is not None else notacion_actual()
    try:
        rhs = parsear(resultado.ecuacion_texto).rhs
    except EntradaInvalida:
        return
    if not es_autonoma(rhs):
        return
    comportamiento = comportamiento_asintotico(resultado)
    with st.expander("Comportamiento cuando x → ∞", expanded=False):
        mostrar_texto(comportamiento.texto, notacion)
        if comportamiento.limite is not None:
            st.caption(f"Límite estimado: {comportamiento.limite:.6g}")


def seccion_evaluacion(resultado) -> None:
    """Evaluación puntual de la solución."""

    with st.expander("Evaluar la solución en un punto", expanded=False):
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
                    "No se pudo evaluar la expresión; usa la curva numérica.",
                    icon=None,
                )
            else:
                st.success(f"y({float(x_eval):g}) ≈ {valor:.10g}", icon=None)


def seccion_explicacion(resultado, *, notacion: str | None = None) -> None:
    """Explicación local u opcionalmente redactada con IA."""

    notacion = notacion if notacion is not None else notacion_actual()
    with st.expander("Explicación en lenguaje sencillo", expanded=False):
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
            mostrar_texto(explicacion, notacion)


def seccion_modelos() -> None:
    """Modelos aplicados, plegados por defecto."""

    with st.expander("Modelos aplicados", expanded=False):
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
                etiqueta = (
                    f"{parametro.etiqueta} ({parametro.unidad})"
                    if parametro.unidad
                    else parametro.etiqueta
                )
                valor = st.number_input(
                    etiqueta,
                    value=float(parametro.valor_defecto),
                    min_value=parametro.minimo,
                    max_value=parametro.maximo,
                    key=f"modelo_{id_modelo}_{parametro.nombre}",
                    help=parametro.descripcion,
                )
                parametros[parametro.nombre] = float(valor)
        iniciales = st.columns(4)
        x0 = iniciales[0].number_input(
            "x₀", value=float(modelo.x0), key=f"modelo_{id_modelo}_x0"
        )
        y0 = iniciales[1].number_input(
            "y₀", value=float(modelo.y0), key=f"modelo_{id_modelo}_y0"
        )
        x_min = iniciales[2].number_input(
            "x mínimo", value=float(modelo.x_min), key=f"modelo_{id_modelo}_xmin"
        )
        x_max = iniciales[3].number_input(
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
            st.warning(str(exc), icon=None)
            return
        st.markdown("**Ecuación instanciada**")
        mostrar_ecuacion(instancia.ecuacion_latex)
        if instancia.solucion_conocida:
            st.caption(
                "Solución de referencia: "
                + formatear_texto(instancia.solucion_conocida, notacion_actual())
            )
        if st.button("Cargar modelo en el inspector", key="cargar_modelo"):
            st.session_state["_cargar_ecuacion"] = {
                "ecuacion": instancia.ecuacion_texto,
                "x0": instancia.x0,
                "y0": instancia.y0,
                "x_min": instancia.x_min,
                "x_max": instancia.x_max,
            }
            st.session_state["_solicitar_resolver"] = True
            st.rerun()


# ---------------------------------------------------------------------------
# Vistas completas
# ---------------------------------------------------------------------------


def render_calculadora() -> None:
    """Vista de cálculo: resultado, certificado y detalles plegables."""

    titulo_pagina(
        "Calculadora",
        "Resultado verificado de la EDO y sus condiciones iniciales.",
        icono="calculator",
    )
    resultado = resultado_actual()
    if resultado is None:
        sin_resultado()
        seccion_modelos()
        return

    seccion_solucion(resultado)
    acciones = st.columns(3)
    acciones[0].button(
        "Ver salida completa",
        key="calc_ir_salida",
        on_click=establecer_vista,
        args=("Salida",),
    )
    acciones[1].button(
        "Abrir visualización",
        key="calc_ir_visualizacion",
        on_click=establecer_vista,
        args=("Visualización",),
    )
    acciones[2].button(
        "Ver procedimiento",
        key="calc_ir_pasos",
        on_click=establecer_vista,
        args=("Paso a paso",),
    )
    seccion_certificado(resultado)
    seccion_detalles(resultado)
    seccion_modelos()


def render_visualizacion() -> None:
    """Vista de gráficas: lienzo protagonista y análisis complementario."""

    titulo_pagina(
        "Visualización",
        "Campo de direcciones, curvas solución y retratos de fase en un lienzo escalable.",
        icono="chart",
    )
    from ui.pagina_cualitativo import render as render_cualitativo
    from ui.pagina_datos import render as render_datos
    from ui.pagina_incertidumbre import render as render_incertidumbre
    from ui.pagina_numerico import render as render_numerico

    pestanas = st.tabs(
        ["Solución y campo", "Cualitativo", "Numérico", "Datos", "Incertidumbre"]
    )
    with pestanas[0]:
        resultado = resultado_actual()
        if resultado is None:
            sin_resultado()
        else:
            seccion_graficas(resultado)
    with pestanas[1]:
        render_cualitativo(cabecera=False)
    with pestanas[2]:
        render_numerico(cabecera=False)
    with pestanas[3]:
        render_datos(cabecera=False)
    with pestanas[4]:
        render_incertidumbre(cabecera=False)


def render_salida() -> None:
    """Vista de salida completa: resultado, métodos, pasos y advertencias."""

    titulo_pagina(
        "Salida",
        "Resultado, métodos, pasos, advertencias y explicación en una sola vista.",
        icono="file",
    )
    resultado = resultado_actual()
    if resultado is None:
        sin_resultado()
        seccion_modelos()
        return

    st.caption("Notación")
    notacion = selector_notacion()
    seccion_solucion(resultado, mostrar_selector=False)
    seccion_metodos(resultado, notacion=notacion)
    seccion_certificado(resultado, notacion=notacion)
    seccion_pasos(resultado, notacion=notacion)
    seccion_advertencias(resultado, notacion=notacion)
    seccion_explicacion(resultado, notacion=notacion)
    seccion_detalles(resultado, notacion=notacion)


def render_pasos() -> None:
    """Vista analítica: procedimiento, evaluación y explicación."""

    titulo_pagina(
        "Paso a paso",
        "Procedimiento certificado, evaluación puntual y explicación accesible.",
        icono="layers",
    )
    resultado = resultado_actual()
    if resultado is None:
        sin_resultado()
        seccion_modelos()
        return

    with tarjeta("Solución de referencia", icono="pin"):
        mostrar_solucion(resultado)
    seccion_pasos(resultado)
    seccion_certificado(resultado)
    seccion_evaluacion(resultado)
    seccion_asintotico(resultado)
    seccion_explicacion(resultado)


def render() -> None:
    """Compatibilidad: muestra todas las secciones en una sola página."""

    titulo_pagina(
        "Resolver",
        "Solución verificada, gráfica, pasos y exploración del campo de direcciones.",
        icono="calculator",
    )
    resultado = resultado_actual()
    if resultado is None:
        sin_resultado()
        seccion_modelos()
        return

    seccion_solucion(resultado)
    seccion_graficas(resultado)
    seccion_pasos(resultado)
    seccion_certificado(resultado)
    seccion_detalles(resultado)
    seccion_asintotico(resultado)
    seccion_evaluacion(resultado)
    seccion_explicacion(resultado)
    seccion_modelos()


__all__ = [
    "resultado_actual",
    "seccion_advertencias",
    "seccion_asintotico",
    "seccion_campo",
    "seccion_certificado",
    "seccion_detalles",
    "seccion_evaluacion",
    "seccion_explicacion",
    "seccion_graficas",
    "seccion_metodos",
    "seccion_modelos",
    "seccion_pasos",
    "seccion_solucion",
    "seccion_solucion_grafica",
    "render_calculadora",
    "render_visualizacion",
    "render_salida",
    "render_pasos",
    "render",
]
