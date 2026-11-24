"""Pruebas de datos, incertidumbre, corrección, informes e IA opcional."""

from __future__ import annotations

import numpy as np
import pytest

from core.ajuste import (
    ajustar,
    cargar_ejemplo,
    predecir,
    seleccionar_mejor_modelo,
)
from core.corrector import corregir
from core.ejercicios import PerfilEstudiante, cargar_perfil, guardar_perfil, recomendar_siguiente
from core.hibrido import resolver
from core.ia_opcional import estado_ia, explicar_resultado, traducir_texto
from core.incertidumbre import Distribucion, monte_carlo, sobol_indices
from core.informes import generar_latex, generar_pdf
from core.parser import parsear_con_parametros
from core.tipos import EntradaInvalida


def test_ajuste_logistico_recupera_parametros() -> None:
    datos = cargar_ejemplo("logistico")
    assert datos.n >= 20
    resultados = ajustar(datos, modelos=["logistico", "exponencial"])
    mejor = seleccionar_mejor_modelo(resultados)
    assert mejor is not None
    assert mejor.modelo == "logistico"
    r = mejor.parametros["r"].valor
    k = mejor.parametros["K"].valor
    assert abs(r - 0.8) / 0.8 < 0.05
    assert abs(k - 100.0) / 100.0 < 0.05
    aic = {resultado.modelo: resultado.aic for resultado in resultados}
    assert aic["logistico"] < aic["exponencial"]


def test_prediccion_con_banda() -> None:
    datos = cargar_ejemplo("logistico")
    resultados = ajustar(datos, modelos=["logistico"])
    mejor = seleccionar_mejor_modelo(resultados)
    assert mejor is not None
    prediccion = predecir(
        mejor,
        np.linspace(float(datos.x[-1]) + 1.0, float(datos.x[-1]) + 5.0, 10),
        n_muestras=80,
        semilla=42,
    )
    assert prediccion is not None
    assert prediccion.y.shape == (10,)
    assert np.all(prediccion.ic_inf <= prediccion.ic_sup)


def test_monte_carlo_determinista() -> None:
    rhs = parsear_con_parametros("y' = r*y").rhs
    parametros = {"r": Distribucion("r", "normal", 0.8, 0.1)}
    argumentos = dict(
        parametros=parametros,
        n_muestras=80,
        semilla=123,
        nivel=0.9,
    )
    x_eval = np.linspace(0, 1, 12)
    primera = monte_carlo(rhs, 0.0, 1.0, x_eval, **argumentos)
    segunda = monte_carlo(rhs, 0.0, 1.0, x_eval, **argumentos)
    assert np.allclose(primera.media, segunda.media)
    assert np.allclose(primera.banda_inf, segunda.banda_inf)
    assert primera.semilla == 123


def test_sobol_indices_basicos() -> None:
    rhs = parsear_con_parametros("y' = r*y").rhs
    resultado = sobol_indices(
        rhs,
        0.0,
        1.0,
        1.0,
        limites={"r": (0.3, 1.2)},
        n_muestras=16,
        semilla=42,
    )
    assert resultado.nombres == ["r"]
    assert resultado.S1.shape == (1,)
    assert np.all(np.isfinite(resultado.ST))


def test_corrector_detecta_error_de_signo() -> None:
    desarrollo = [
        "y' = y",
        "dy/y = dx",
        "ln|y| = x + C",
        "y = C*exp(-x)",
    ]
    resultado = corregir(desarrollo, "y' = y")
    assert not resultado.correcto
    assert resultado.primer_error is not None
    assert resultado.primer_error.pista


def test_corrector_acepta_desarrollo_correcto() -> None:
    desarrollo = [
        "y' = y",
        "dy/y = dx",
        "ln|y| = x + C",
        "y = C*exp(x)",
    ]
    resultado = corregir(desarrollo, "y' = y")
    assert resultado.correcto


def test_informes_pdf_y_latex() -> None:
    resultado = resolver("y' = y", x0=0, y0=1, x_min=0, x_max=1, timeout=5)
    latex = generar_latex(resultado)
    assert r"\documentclass" in latex
    assert "Certificado" in latex
    pdf = generar_pdf(resultado)
    assert pdf.contenido.startswith(b"%PDF")
    assert pdf.tamano_bytes > 1000


def test_ia_desactivada_por_defecto(monkeypatch) -> None:
    monkeypatch.delenv("EDO_LAB_IA_ACTIVA", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    estado = estado_ia()
    assert estado.activa is False
    sugerencia = traducir_texto("crecimiento logístico de una población")
    assert sugerencia.texto.startswith("y' =")
    with pytest.raises(EntradaInvalida):
        traducir_texto("hola sin contenido matemático")
    resultado = resolver("y' = y", x0=0, y0=1, x_min=0, x_max=1, timeout=5)
    explicacion = explicar_resultado(resultado)
    assert "verificada" in explicacion.lower()


def test_perfil_estudiante_persistente(tmp_path) -> None:
    perfil = PerfilEstudiante()
    perfil.registrar("separable", True)
    perfil.registrar("lineal", False)
    ruta = tmp_path / "perfil.json"
    guardar_perfil(perfil, ruta)
    recuperado = cargar_perfil(ruta)
    assert recuperado.aciertos == {"separable": 1}
    assert recuperado.errores == {"lineal": 1}
    assert recomendar_siguiente(recuperado) in {"exacta", "bernoulli", "logistica"}
