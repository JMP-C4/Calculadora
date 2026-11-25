"""Pruebas del núcleo de EDO-Lab (entrada, clasificación y solución híbrida)."""

from __future__ import annotations

import pytest
import sympy as sp

from core.clasificador import clasificar, tipo_principal
from core.hibrido import resolver
from core.parser import parsear, parsear_con_parametros, parsear_parametrizada
from core.tipos import EntradaInvalida, EstadoVerificacion


def test_parser_acepta_formatos_habituales() -> None:
    ecuacion = parsear("y' = x*y + sin(x)")
    assert ecuacion.es_autonoma is False
    assert "y" in str(ecuacion.rhs)
    assert parsear("dy/dx = y").rhs is not None
    assert parsear("y' = 2x").rhs is not None


def test_parser_rechaza_simbolos_desconocidos() -> None:
    with pytest.raises(EntradaInvalida):
        parsear("y' = z*y")
    with pytest.raises(EntradaInvalida):
        parsear("")


def test_parser_parametrizado() -> None:
    familia = parsear_parametrizada("y' = mu*y - y^2")
    assert familia.parametro_nombre == "mu"
    assert "mu" in str(familia.rhs)


def test_parser_con_parametros_para_incertidumbre() -> None:
    ecuacion = parsear_con_parametros("dy/dx = r*y + a*sin(x)")
    assert ecuacion.parametros == ("a", "r")
    assert ecuacion.rhs.free_symbols & {sp.Symbol("r", real=True)}
    with pytest.raises(EntradaInvalida):
        parsear_con_parametros("y' = funcion_rara(y)")


def test_clasificacion_logistica_y_lineal() -> None:
    logistica = parsear("y' = y*(1-y)")
    etiquetas = [tipo.etiqueta.lower() for tipo in clasificar(logistica)]
    assert any("autónoma" in etiqueta or "separable" in etiqueta for etiqueta in etiquetas)
    lineal = parsear("y' + y = x")
    assert tipo_principal(lineal)


def test_solucion_simbolica_certificada() -> None:
    resultado = resolver("y' = y", x0=0.0, y0=1.0, x_min=0.0, x_max=2.0, timeout=5.0)
    assert resultado.camino == "analitica"
    assert resultado.certificado is not None
    assert resultado.certificado.estado == EstadoVerificacion.SIMBOLICA
    assert resultado.particular_latex


@pytest.mark.parametrize(
    "enunciado",
    [
        r"$$\frac{dy}{dx} + \frac{2}{x}y = 4x, \quad x > 0$$",
        r"$$(2xy + 3x^2)dx + (x^2 + 4y^3)dy = 0$$",
        r"$$\frac{dy}{dx} - y = e^{2x} y^3$$",
        r"$$\frac{dy}{dx} = y^2 - \frac{2}{x}y - \frac{1}{x^2}, \quad x > 0$$",
    ],
)
def test_enunciados_de_lista_resuelven(enunciado: str) -> None:
    resultado = resolver(
        enunciado, x0=1.0, y0=1.0, x_min=0.1, x_max=3.0, timeout=15.0
    )
    assert resultado.certificado is not None
    assert resultado.solucion_latex.strip()
    if "x > 0" in enunciado:
        assert any("Dominio declarado" in aviso for aviso in resultado.advertencias)


def test_respaldo_numerico_con_certificado() -> None:
    resultado = resolver(
        "y' = x*y + sin(x)",
        x0=0.0,
        y0=1.0,
        x_min=0.0,
        x_max=2.0,
        timeout=2.0,
    )
    assert resultado.camino == "numerica"
    assert resultado.numerico is not None and resultado.numerico.exito
    assert resultado.certificado is not None
    assert resultado.certificado.estado == EstadoVerificacion.NUMERICA


def test_explosion_en_tiempo_finito() -> None:
    resultado = resolver("y' = y^2", x0=0.0, y0=1.0, x_min=0.0, x_max=2.0, timeout=5.0)
    assert resultado.existencia is not None
    assert resultado.existencia.explota
    assert resultado.existencia.tiempo_explosion == pytest.approx(1.0, abs=0.15)


def test_no_unicidad_potencia_fraccionaria() -> None:
    resultado = resolver(
        "y' = y^(1/3)",
        x0=0.0,
        y0=0.0,
        x_min=0.0,
        x_max=2.0,
        timeout=4.0,
    )
    assert resultado.existencia is not None
    assert resultado.existencia.no_unicidad


def test_certificado_siempre_presente_si_hay_solucion() -> None:
    for texto in ("y' = y", "y' + 2*y = exp(-x)", "y' = x*y"):
        resultado = resolver(texto, x0=0.0, y0=1.0, x_min=0.0, x_max=1.0, timeout=5.0)
        assert resultado.certificado is not None
