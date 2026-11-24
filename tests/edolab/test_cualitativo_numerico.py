"""Pruebas de análisis cualitativo, convergencia y modelos aplicados."""

from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from core.convergencia import estudio_convergencia, validar_orden
from core.cualitativo import bifurcacion, equilibrios, linea_fase
from core.modelos import MODELOS, instanciar_modelo, listar_modelos, resolver_modelo
from core.parser import parsear, parsear_parametrizada
from odecalc.symbols import X


def test_equilibrios_logisticos_estabilidad() -> None:
    rhs = parsear("y' = y*(1-y)").rhs
    puntos = equilibrios(rhs)
    valores = {round(punto.valor, 8): punto.estabilidad for punto in puntos}
    assert valores[0.0].startswith("inestable")
    assert valores[1.0].startswith("estable")


def test_linea_fase_devuelve_malla() -> None:
    rhs = parsear("y' = y*(1-y)").rhs
    datos = linea_fase(rhs, y_min=-1.0, y_max=2.0, n=50)
    assert datos["y"].shape == (50,)
    assert datos["f"].shape == (50,)


def test_bifurcacion_y_silla_nodo() -> None:
    familia = parsear_parametrizada("y' = mu - y^2")
    puntos = bifurcacion(familia.rhs, familia.parametro, np.linspace(-1, 1, 9))
    assert puntos
    estables = [p for p in puntos if p.estabilidad.startswith("estable")]
    inestables = [p for p in puntos if p.estabilidad.startswith("inestable")]
    assert estables and inestables


def test_orden_empirico_rk4() -> None:
    rhs = parsear("y' = y").rhs
    resultado = estudio_convergencia(
        rhs,
        0.0,
        1.0,
        1.0,
        exacto=sp.exp(X),
        metodos=("RK4",),
        hs=(0.2, 0.1, 0.05, 0.025, 0.0125),
    )
    orden = resultado.ordenes["RK4"]
    assert 3.8 <= orden <= 4.2
    assert validar_orden(orden, 4.0)


def test_modelos_disponibles_e_instanciacion() -> None:
    assert len(listar_modelos()) >= 6
    for modelo in listar_modelos():
        instancia = instanciar_modelo(modelo.id)
        assert instancia.ecuacion_texto.startswith("y' =")
        assert parsear(instancia.ecuacion_texto).rhs is not None
        assert instancia.x_min < instancia.x_max
    assert "resistencia_aire" in MODELOS


def test_modelo_logistico_se_resuelve_con_certificado() -> None:
    instancia = instanciar_modelo("poblacion")
    resultado = resolver_modelo(instancia, timeout=5.0)
    assert resultado.certificado is not None
    assert resultado.certificado.es_confiable
    assert resultado.solucion_latex
