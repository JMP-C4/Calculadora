"""Regresiones encontradas en la revisión completa del código."""

from __future__ import annotations

import sympy as sp

from core.corrector import corregir
from core.cualitativo import _raices_reales, equilibrios
from core.notacion import formatear_texto, fragmentos, latex_a_infijo
from odecalc.api import solve
from odecalc.symbols import Y


def test_dsolve_no_bloquea_ecuaciones_explicitas_lie_group() -> None:
    resultado = solve("y' = exp(y) + log(x)", compute_numeric=False)
    assert resultado.error is None
    assert resultado.chosen_method == "dsolve"
    assert resultado.verification is not None
    assert resultado.verification.status == "ok"


def test_paso_pvi_muestra_la_constante_de_la_rama_verificada() -> None:
    resultado = solve("y' = y/x + sqrt(y)", x0=1.0, y0=4.0, compute_numeric=False)
    assert resultado.particular is not None
    assert resultado.particular_verification is not None
    assert resultado.particular_verification.status == "ok"
    pasos = [paso for paso in resultado.steps if paso.title == "Despejar la constante C"]
    assert len(pasos) == 1
    assert pasos[0].latex == "C = 1"


def test_equilibrios_no_inventa_raices_de_funciones_sin_ceros() -> None:
    assert _raices_reales(sp.exp(Y)) == []
    assert equilibrios(sp.exp(Y)) == []

    raices = _raices_reales(sp.exp(Y) - 2 * Y - 2)
    assert any(abs(raiz - 1.6783) < 1e-2 for raiz in raices)


def test_notacion_no_rompe_delimitadores_con_integrales_en_prosa() -> None:
    texto = "Integramos ∫ f(x) dx = 1."
    formateado = formatear_texto(texto, "Algebraica")
    assert formateado == r"Integramos $\int f(x) dx = 1$."
    assert formateado.count("$") == 2
    assert [parte[1] for parte in fragmentos(texto, "Algebraica")] == [False, True, False]

    assert formatear_texto("∫ g(y) dy/f(y).", "Algebraica").count("$") == 2


def test_notacion_infija_conserva_agrupacion_del_exponente() -> None:
    assert formatear_texto("dy/dx = y^(x+1)", "Infija") == "(dy)/(dx) = y^(x+1)"
    assert latex_a_infijo("x^(2*n)") == "x^(2*n)"


def test_corrector_acepta_constante_C1_con_suposicion_real() -> None:
    assert corregir("y - C1*exp(x) = 0", "y' = y").correcto
