"""Pruebas de regresión que reproducen los hallazgos de REPORTE_AUDITORIA_TECNICA.md.

Cada prueba marcada con ``xfail(strict=True)`` documenta un defecto verificado
que debe pasar a verde cuando se aplique su corrección correspondiente.
"""

from __future__ import annotations

import pandas as pd
import pytest
import sympy as sp

from apps.web.server import _validated
from core.ajuste import ajustar, cargar_datos, cargar_ejemplo
from core.corrector import corregir
from core.cualitativo import datos_isoclinas
from core.existencia import analizar_existencia, estimar_explosion
from core.modelos import instanciar_modelo
from core.parser import parsear_con_parametros
from core.tipos import DatosInvalidos
from odecalc.api import _numeric_steps, solve
from odecalc.classify.classifier import clairaut_or_lagrange
from odecalc.models import NumericResult, SolveResult
from odecalc.numeric.solver import solve_numeric
from odecalc.parsing import parse_ode
from odecalc.symbols import X


@pytest.mark.parametrize("equation", ["y' = x^-2", "y' = e^-x"])
def test_c01_negative_exponent_without_braces(equation: str) -> None:
    parsed = parse_ode(equation)
    assert parsed.error is None
    assert parsed.rhs is not None


def test_c02_latex_function_implicit_product_argument() -> None:
    parsed = parse_ode(r"$$\frac{dy}{dx} = \sin 2x$$")
    assert parsed.error is None
    assert parsed.rhs is not None
    assert sp.simplify(parsed.rhs - sp.sin(2 * X)) == 0


def test_c03_solve_degrades_to_numeric_on_symbolic_timeout() -> None:
    result = solve("y' = x*y + sin(x)", x0=0.0, y0=1.0, x_min=0.0, x_max=1.0, timeout=2.0)
    assert result.error is None
    assert result.numeric is not None
    assert result.numeric.success


@pytest.mark.xfail(strict=True, reason="C-04: exponencial fuerza k >= 1e-6 y falla en decaimiento")
def test_c04_exponential_fit_supports_decay() -> None:
    datos = cargar_ejemplo("decaimiento")
    resultado = ajustar(datos, modelos=["exponencial"])[0]
    assert resultado.exito
    assert resultado.parametros["k"].valor < 0.0
    assert resultado.r2 > 0.95


@pytest.mark.xfail(strict=True, reason="C-04: cargar_datos valida len >= 5 antes de drop_duplicates")
def test_c04_cargar_datos_validates_unique_x_count() -> None:
    tabla = pd.DataFrame({"x": [0.0, 0.0, 1.0, 1.0, 2.0], "y": [1.0, 2.0, 3.0, 4.0, 5.0]})
    with pytest.raises(DatosInvalidos):
        cargar_datos(tabla)


@pytest.mark.xfail(strict=True, reason="C-05: resistencia_aire con c=0.0 lanza ZeroDivisionError")
def test_c05_air_resistance_zero_drag_does_not_crash() -> None:
    instancia = instanciar_modelo("resistencia_aire", parametros={"c": 0.0})
    assert instancia.parametros["c"] == 0.0


@pytest.mark.xfail(strict=True, reason="C-05: lambda es bloqueada por _DANGEROUS_WORDS")
def test_c05_decay_model_parameter_accepted_with_parameters_parser() -> None:
    ecuacion = parsear_con_parametros("y' = -lambda*y")
    assert "lambda" in ecuacion.parametros


def test_a02_numeric_steps_latex_not_corrupted() -> None:
    res = SolveResult(
        input_text="y' = x + y",
        input_latex=r"\frac{dy}{dx} = x + y",
        standard_form="dy/dx = x + y",
        numeric=NumericResult(None, None, True, "ok", "RK45", interval=(0.0, 1.0)),
    )
    step = _numeric_steps(res)[0]
    assert r"\text{dy/dx" not in step.latex
    assert step.latex == r"\frac{dy}{dx} = x + y"


def test_a03_validity_checks_even_root_domain() -> None:
    result = solve("y' = -x/sqrt(1-x^2)", x0=2.0, y0=0.0, compute_numeric=False)
    assert result.validity.interval != "(-∞, ∞) en ausencia de otras singularidades"


@pytest.mark.xfail(strict=True, reason="A-05: clairaut_or_lagrange exige psi.has(DY) para Lagrange")
def test_a05_lagrange_with_constant_psi_is_classified() -> None:
    parsed = parse_ode("y = 2*x*y' + 1")
    detected = clairaut_or_lagrange(parsed)
    assert detected is not None
    assert detected[0] == "lagrange"


@pytest.mark.xfail(strict=True, reason="A-07: _validated acepta NaN y x_min >= x_max")
@pytest.mark.parametrize(
    "payload",
    [
        {"equation": "y' = x + y", "x_min": float("nan"), "x_max": 5.0},
        {"equation": "y' = x + y", "x_min": 5.0, "x_max": 1.0},
    ],
)
def test_a07_web_server_rejects_nonfinite_or_inverted_bounds(payload: dict) -> None:
    with pytest.raises(ValueError):
        _validated(payload)


@pytest.mark.xfail(strict=True, reason="A-10: corrector rechaza y - C*exp(x) = 0 por C libre")
def test_a10_corrector_accepts_rearranged_general_solution() -> None:
    resultado = corregir("y - C*exp(x) = 0", "y' = y")
    assert resultado.correcto


@pytest.mark.xfail(strict=True, reason="A-11: datos_isoclinas no hace broadcast para rhs constante")
def test_a11_isoclines_constant_rhs_returns_2d_grid() -> None:
    datos = datos_isoclinas(parse_ode("y' = 2").rhs, n=20)
    assert datos.z.shape == (20, 20)


def test_m01_numeric_solver_supports_allowed_special_functions() -> None:
    parsed = parse_ode("y' = erfi(x)")
    assert parsed.rhs is not None
    numeric = solve_numeric(parsed.rhs, 0.0, 0.0, 0.0, 0.5)
    assert numeric.success


def test_m03_singularities_report_both_log_and_sqrt_notes() -> None:
    info = analizar_existencia(parse_ode("y' = log(x) + sqrt(y)").rhs)
    notas = " ".join(info.notas).lower()
    assert "logaritmo" in notas
    assert "raíz cuadrada" in notas


def test_m03_explosion_forward_detected_when_y0_negative_and_rhs_positive() -> None:
    explota, tiempo, direccion = estimar_explosion(parse_ode("y' = y^2 + 1").rhs, 0.0, -1.0)
    assert explota
    assert direccion == "hacia adelante"
    assert tiempo is not None and tiempo > 0.0
