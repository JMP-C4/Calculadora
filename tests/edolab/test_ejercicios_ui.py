"""Pruebas de ejercicios y de la interfaz Streamlit (importación)."""

from __future__ import annotations

import importlib

import pytest

from core.ejercicios import TIPOS, generar_ejercicio


@pytest.mark.slow
def test_generar_ejercicio_separable_verificado() -> None:
    ejercicio = generar_ejercicio("separable", 1, semilla=42)
    assert ejercicio.tipo in TIPOS
    assert ejercicio.solucion_latex
    assert ejercicio.certificado is not None
    assert ejercicio.certificado.es_confiable


def test_importacion_de_paginas_streamlit() -> None:
    modulos = [
        "ui.estilos",
        "ui.componentes",
        "ui.graficas",
        "ui.pagina_resolver",
        "ui.pagina_cualitativo",
        "ui.pagina_numerico",
        "ui.pagina_datos",
        "ui.pagina_incertidumbre",
        "ui.pagina_aprendizaje",
        "ui.pagina_informes",
        "ui.streamlit_app",
    ]
    for nombre in modulos:
        modulo = importlib.import_module(nombre)
        assert modulo is not None
    from ui.streamlit_app import main

    assert callable(main)
