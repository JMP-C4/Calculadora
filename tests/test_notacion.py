"""Pruebas del formateo compartido de notación de salida."""

from __future__ import annotations

import sympy as sp

from core.notacion import (
    NATURAL,
    formatear,
    formatear_texto,
    fragmentos,
    infijo,
    latex_a_infijo,
    latex_a_natural,
    normalizar,
)
from odecalc.models import Solution


def test_infijo_explicita_usa_operadores_tradicionales() -> None:
    x = sp.Symbol("x")
    solucion = Solution(form="explicit", expr=sp.Symbol("C1") * sp.exp(x) + 1)

    texto = infijo(r"y = C_1 e^{x} + 1", solucion)

    assert texto == "y = C1*exp(x) + 1"


def test_infijo_implicita_incluye_valor() -> None:
    x = sp.Symbol("x")
    y = sp.Symbol("y")
    solucion = Solution(form="implicit", expr=x + y, value=sp.Integer(1))

    assert infijo("x + y = 1", solucion) == "x + y = 1"


def test_infijo_latex_simple_sin_objeto() -> None:
    texto = infijo(r"y = \frac{1}{x^2} + \sqrt{x}", None)

    assert "sqrt(x)" in texto
    assert "(1)/(x^2)" in texto
    assert "\\" not in texto


def test_formatear_respeta_notacion() -> None:
    x = sp.Symbol("x")
    solucion = Solution(form="explicit", expr=sp.exp(x))

    algebraica, es_latex = formatear(r"y = e^{x}", solucion, "Algebraica")
    tradicional, es_texto = formatear(r"y = e^{x}", solucion, "Infija")

    assert algebraica == r"y = e^{x}"
    assert es_latex is True
    assert tradicional == "y = exp(x)"
    assert es_texto is False


def test_normalizar_valores_desconocidos() -> None:
    assert normalizar("Infija") == "Infija"
    assert normalizar("Algebraica") == "Algebraica"
    assert normalizar(None) == NATURAL
    assert normalizar("otra") == NATURAL


def test_normalizar_alias_de_notacion_natural() -> None:
    for alias in ("Natural", "Pretty Print", "2D Math", "Leibniz", "Lagrange"):
        assert normalizar(alias) == NATURAL


def test_formatear_texto_no_toca_la_prosa() -> None:
    texto = "La solución fue verificada simbólicamente."

    assert formatear_texto(texto, "Algebraica") == texto
    assert formatear_texto(texto, "Infija") == texto


def test_formatear_texto_convierte_fragmentos_delimitados() -> None:
    texto = r"Dominio: $(-\infty, \infty)$ y $y = \frac{1}{x^2}$."

    algebraica = formatear_texto(texto, "Algebraica")
    infija = formatear_texto(texto, "Infija")

    assert r"$(-\infty, \infty)$" in algebraica
    assert r"$y = \frac{1}{x^2}$" in algebraica
    assert "Dominio:" in infija
    assert "(-∞, ∞)" in infija
    assert "(1)/(x^2)" in infija
    assert "\\" not in infija


def test_formatear_texto_envuelve_comandos_sin_duplicarlos() -> None:
    texto = r"\mu(x) = e^{\int P(x)\,dx}"

    algebraica = formatear_texto(texto, "Algebraica")

    assert algebraica.count("$") == 2
    assert r"\mu(x) = e^{\int P(x)\,dx}" in algebraica


def test_latex_a_infijo_traduce_flechas_y_fracciones() -> None:
    texto = r"\text{clasificar} \rightarrow \text{resolver} \rightarrow \frac{1}{2}"

    assert latex_a_infijo(texto) == "clasificar -> resolver -> (1)/(2)"


def test_fragmentos_separa_prosa_y_formulas() -> None:
    partes = fragmentos(
        r"Dominio: $(-\infty, \infty)$ y $y = \frac{1}{x^2}$.", "Algebraica"
    )

    assert [es_latex for _texto, es_latex in partes] == [
        False,
        True,
        False,
        True,
        False,
    ]
    assert partes[1][0] == r"(-\infty, \infty)"
    assert "Dominio:" in partes[0][0]
    assert partes[-1][0].startswith(".")


def test_latex_a_natural_usa_derivadas_y_simbolos() -> None:
    texto = latex_a_natural(r"\frac{dy}{dx} = y' + \mu\sqrt{x}")

    assert "dy/dx" in texto
    assert "y′" in texto
    assert "μ" in texto
    assert "√" in texto
    assert "\\" not in texto


def test_formatear_natural_devuelve_latex_legible() -> None:
    x = sp.Symbol("x")
    solucion = Solution(form="explicit", expr=sp.exp(x), latex=r"y = e^{x}")

    texto, es_latex = formatear(r"y = e^{x}", solucion, NATURAL)

    assert texto == "y = e^x"
    assert es_latex is True


def test_formatear_texto_natural_respeta_la_prosa() -> None:
    texto = r"La ecuación y' = y y \frac{dy}{dx} = x."

    preparado = formatear_texto(texto, NATURAL)

    assert "La ecuación y′ = y" in preparado
    assert "$dy/dx = x$" in preparado
    assert "\\frac" not in preparado


def test_fragmentos_acepta_notacion_natural() -> None:
    partes = fragmentos(r"Dominio: $(-\infty, \infty)$ y $y' = y$.", NATURAL)

    assert partes[1][0] == "(-∞, ∞)"
    assert partes[3][0] == "y′ = y"


def test_codigo_matematico_se_convierte_a_latex() -> None:
    algebraica, es_latex = formatear("y = C1*exp(x) + sqrt(x)", None, "Algebraica")

    assert es_latex is True
    assert r"C_1\cdot e^{x}" in algebraica
    assert r"\sqrt{x}" in algebraica
    assert "**" not in algebraica
    assert "sqrt(" not in algebraica
    assert "*" not in algebraica


def test_formatear_texto_envuelve_formulas_dentro_de_la_prosa() -> None:
    texto = "La solución es y = C*exp(x) y deriva de dy/dx = x**2."

    natural = formatear_texto(texto, NATURAL)
    infija = formatear_texto(texto, "Infija")

    assert "$y = C· e^x$" in natural
    assert "dy/dx = x^2" in natural
    assert "exp(" not in natural
    assert "**" not in natural
    assert "y = C*exp(x)" in infija
    assert "**" not in infija
