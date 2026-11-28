"""Pruebas del formateo compartido de notación de salida."""

from __future__ import annotations

import sympy as sp

from core.notacion import (
    NATURAL,
    adaptar_latex_mathtext,
    codigo_a_latex,
    formatear,
    formatear_texto,
    fragmentos,
    infijo,
    latex_a_infijo,
    latex_a_natural,
    leer_preferencia,
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


def test_envolver_comandos_no_parte_prefijos_de_ecuacion() -> None:
    texto = r"Se despeja y = v^{-\frac{1}{2}}. Luego G(u) = \sin{\left(u \right)}."

    for modo in ("Algebraica", NATURAL):
        frags = fragmentos(texto, modo)
        formulas = [contenido for contenido, es_m in frags if es_m]
        assert len(formulas) == 2
        for formula in formulas:
            adaptado = adaptar_latex_mathtext(formula)
            assert adaptado.count("{") == adaptado.count("}")


def test_formatear_texto_multilinea_no_omite_formulas_en_prosa() -> None:
    texto = "Solución: $y = C e^{x}$\nForma estándar: dy/dx = (x**3 - 2*y)/x\nIntervalo: (-∞, ∞)"

    algebraica = formatear_texto(texto, "Algebraica")

    assert r"$\frac{dy}{dx} = (x^3 - 2\cdot y)/x$" in algebraica
    assert r"$(-\infty, \infty)$" in algebraica


def test_latex_a_natural_y_codigo_con_anidacion() -> None:
    nat_exp = latex_a_natural(r"y = 2 e^{\frac{x^{2}}{2}}")
    nat_atan = latex_a_natural(r"\operatorname{atan}{\left(\frac{y - 2}{x + 1} \right)}")
    cod_anidado = codigo_a_latex("y = exp(-(x**2)/2) + sqrt(1 + (y - 1)**2)")

    assert "frac" not in nat_exp
    assert "{" in nat_exp and "}" in nat_exp
    assert "(y - 2)/(x + 1)" in nat_atan
    assert "{" not in nat_atan
    assert r"e^{-(x^2)/2}" in cod_anidado
    assert r"\sqrt{1 + (y - 1)^2}" in cod_anidado


def test_adaptar_latex_mathtext_soporta_cases_y_flechas() -> None:
    adaptado = adaptar_latex_mathtext(
        r"\begin{cases} \frac{x^{2}}{2} & \text{for}\: x \leq 0 \\ - \frac{x^{2}}{2} & \text{otherwise} \end{cases}"
    )
    assert r"\begin{cases}" not in adaptado
    assert r"\left\{" in adaptado
    assert r"A \Longrightarrow B" == adaptar_latex_mathtext(r"A \implies B")
    assert r"A \Leftrightarrow B" == adaptar_latex_mathtext(r"A \iff B")


def test_leer_preferencia_acepta_default_para_escritorio(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert leer_preferencia() == NATURAL
    assert leer_preferencia(default="Algebraica") == "Algebraica"


def test_fragmentos_no_captura_prosa_y_soporta_intervalos_y_signos() -> None:
    texto = (
        "Si x ≠ 0, la ecuación μ(x)·y' = 0 implica y = C o x = 0. "
        "Intervalo: (0, ∞). Regla de signos: (-2)*(-3) = +6."
    )
    frags_est = fragmentos(texto, "Algebraica")
    textos_math = [c for c, es_tex in frags_est if es_tex]
    assert any(r"\neq" in t for t in textos_math)
    assert any(r"\infty" in t for t in textos_math)
    assert any("(-2)" in t for t in textos_math)
    assert all("implica" not in t for t in textos_math)

    adaptado = adaptar_latex_mathtext(
        r"\begin{cases} x & \text{for}\: x \ge 0 \\ -x & \text{otherwise} \end{cases}"
    )
    assert r"\geq" in adaptado
    assert r"\ge " not in adaptado
    assert r"\sqrt{x + 1}" in adaptar_latex_mathtext("√(x + 1)")
    assert r"e^{\int P(x) dx}" in adaptar_latex_mathtext("e^(∫ P(x) dx)")

