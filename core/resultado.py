"""Conversión del contrato interno del motor al contrato público de EDO-Lab."""

from __future__ import annotations

import sympy as sp

from odecalc.models import Solution as SolucionMotor
from odecalc.models import SolveResult
from odecalc.symbols import X, Y
from odecalc.timeout import run_with_timeout

from core.clasificador import clasificar, etiqueta_metodo, tipo_principal
from core.existencia import analizar_existencia
from core.parser import parsear
from core.pasos import pasos_desde_motor, pasos_numericos, pasos_para_tipo
from core.tipos import (
    Certificado,
    ResultadoNumerico,
    ResultadoSolucion,
    SolucionNoDisponible,
)
from core.verificador import certificar_motor, certificar_numerico


def _despejar_rama_real(particular) -> sp.Expr | None:
    """Intenta convertir una solución implícita compleja en una rama real."""

    if not getattr(particular, "is_implicit", False):
        return None
    try:
        valor = complex(sp.N(particular.value))
    except Exception:
        return None
    if abs(valor.imag) < 1e-10:
        return None
    try:
        ramas = run_with_timeout(
            sp.solve,
            sp.Eq(particular.expr, particular.value),
            Y,
            timeout=2.0,
        )
    except Exception:
        # La extracción de una rama real es opcional: si SymPy tarda o falla,
        # se conserva la solución implícita ya verificada.
        return None
    for rama in ramas:
        if not isinstance(rama, sp.Expr) or rama.has(Y):
            continue
        try:
            muestra = complex(sp.N(rama.subs(X, 0.73)))
        except Exception:
            continue
        if abs(muestra.imag) < 1e-9:
            return sp.simplify(rama)
    return None


def _numerico_desde_motor(motor: SolveResult) -> ResultadoNumerico | None:
    datos = motor.numeric
    if datos is None:
        return None
    import numpy as np

    return ResultadoNumerico(
        x=np.asarray(datos.x_arr if datos.x_arr is not None else [], dtype=float),
        y=np.asarray(datos.y_arr if datos.y_arr is not None else [], dtype=float),
        metodo=datos.method,
        exito=datos.success,
        mensaje=datos.message,
        error_max=datos.error_estimate,
        rigido=datos.stiff,
        explosion=datos.blow_up,
    )


def convertir_motor(
    motor: SolveResult,
    texto: str,
    *,
    camino: str,
    x0: float | None = None,
    y0: float | None = None,
    intervalo: tuple[float, float] | None = None,
) -> ResultadoSolucion:
    """Construye el :class:`ResultadoSolucion` que consume la interfaz."""

    if motor.error is not None and motor.general is None and (
        motor.numeric is None or not motor.numeric.success
    ):
        raise SolucionNoDisponible(motor.error)

    ecuacion = parsear(texto)
    tipos = clasificar(ecuacion)
    numerico = _numerico_desde_motor(motor)
    particular = motor.particular
    general = motor.general
    solucion_publica = particular or general

    general_latex = general.latex if general is not None else ""
    particular_latex = particular.latex if particular is not None else ""
    if particular is not None:
        rama_real = _despejar_rama_real(particular)
        if rama_real is not None:
            solucion_publica = SolucionMotor(
                form="explicit",
                expr=rama_real,
                latex=sp.latex(sp.Eq(Y, rama_real)),
            )
            particular_latex = solucion_publica.latex
        solucion_latex = particular_latex
    elif general is not None:
        solucion_latex = general_latex
    elif numerico is not None and numerico.exito:
        solucion_latex = (
            rf"y(x) \approx \text{{solución numérica ({numerico.metodo})}}"
        )
    else:
        solucion_latex = ""

    if particular is not None or general is not None:
        certificado: Certificado | None = certificar_motor(motor)
    elif numerico is not None:
        certificado = certificar_numerico(numerico, ecuacion.rhs)
    else:
        certificado = None

    if numerico is not None and numerico.exito:
        pasos = (
            pasos_desde_motor(motor)
            if motor.steps
            else pasos_numericos(numerico)
        )
    else:
        pasos = pasos_desde_motor(motor) or pasos_para_tipo(ecuacion, motor)

    limites = intervalo
    if limites is None and numerico is not None and numerico.intervalo is not None:
        limites = numerico.intervalo
    existencia = analizar_existencia(
        ecuacion.rhs,
        x0,
        y0,
        x_min=limites[0] if limites else None,
        x_max=limites[1] if limites else None,
    )

    advertencias = list(dict.fromkeys(motor.warnings))
    if certificado is not None:
        advertencias.extend(
            nota
            for nota in certificado.notas
            if "no " in nota.lower() and "superó" in nota.lower()
        )
    if existencia.no_unicidad:
        advertencias.append(
            existencia.motivo_no_unicidad
            or "La solución puede no ser única en el punto inicial."
        )
    if existencia.explota and existencia.tiempo_explosion is not None:
        advertencias.append(
            f"Posible explosión en x ≈ {existencia.tiempo_explosion:.6g}."
        )

    tipo = (
        etiqueta_metodo(motor.chosen_method)
        if motor.chosen_method
        else tipo_principal(ecuacion)
    )

    return ResultadoSolucion(
        ecuacion_texto=texto,
        ecuacion_latex=ecuacion.latex
        or (sp.latex(sp.Eq(sp.Symbol("y'"), ecuacion.rhs)) if ecuacion.rhs else texto),
        tipo=tipo,
        tipos=[tipo.etiqueta for tipo in tipos],
        camino="analitica" if general is not None else "numerica",
        solucion=solucion_publica if solucion_publica is not None else numerico,
        solucion_latex=solucion_latex,
        general_latex=general_latex,
        particular_latex=particular_latex,
        certificado=certificado,
        advertencias=list(dict.fromkeys(advertencias)),
        pasos=pasos,
        x0=x0,
        y0=y0,
        intervalo=limites,
        numerico=numerico,
        existencia=existencia,
        resultado_motor=motor,
    )


__all__ = ["convertir_motor"]
