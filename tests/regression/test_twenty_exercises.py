"""Pruebas de regresión e integración sobre la batería de 20 ejercicios y hallazgos."""

from __future__ import annotations

import pytest
import sympy as sp

from core.ejercicios import TIPOS, generar_ejercicio
from core.hibrido import curva_solucion, resolver
from core.tipos import ResultadoSolucion
import odecalc.api as odecalc_api
from odecalc.api import solve
from odecalc.symbols import X
from odecalc.timeout import TimeoutError as MotorTimeoutError


TWENTY_EXERCISES: list[tuple[int, str, float | None, float | None, tuple[str, ...]]] = [
    (1, "y' = 3*x**2", 0.0, 2.0, ("linear", "separable", "exact")),
    (2, "y' = 2*x*y", 0.0, 5.0, ("linear", "separable")),
    (3, "y' + 4*y = 0", 0.0, 3.0, ("linear", "separable")),
    (4, "y' = cos(x) / y", 0.0, 2.0, ("separable", "exact")),
    (5, "(y - 2)*(dy/dx) = x + 1", 0.0, 4.0, ("separable", "exact")),
    (6, "y' + 2*y = e^-x", 0.0, 1.0, ("linear",)),
    (7, "y' + (1/x)*y = 3*x", 1.0, 2.0, ("linear",)),
    (8, "dy/dx = y*(1 - y/10)", 0.0, 2.0, ("separable", "bernoulli")),
    (9, "(2*x*y + 3)*dx + (x**2 + 4*y)*dy = 0", None, None, ("exact",)),
    (10, "(exp(x)*sin(y) + 2*x)*dx + (exp(x)*cos(y) + 1)*dy = 0", 0.0, 0.0, ("exact",)),
    (11, "y' = (x + y) / x", 1.0, 3.0, ("linear", "homogeneous")),
    (12, "y' = (x + y + 1)**2", 0.0, 0.0, ("substitution_linear_combo",)),
    (13, "y' + y = x*y**2", 0.0, 1.0, ("bernoulli",)),
    (14, "xy' + y = y^{-1}", 1.0, 2.0, ("separable", "bernoulli")),
    (15, "(3*x*y + y**2)*dx + (x**2 + x*y)*dy = 0", None, None, ("integrating_factor_x", "homogeneous")),
    (16, "y' = (y**2 + 2*x*y) / x**2", 1.0, 1.0, ("homogeneous", "bernoulli", "integrating_factor_y")),
    (17, "y' = y**2 - 2*y + 1", None, None, ("separable", "riccati")),
    (18, "y = xy' + (y')^2", None, None, ("clairaut",)),
    (19, "y' = y**2", 0.0, 1.0, ("separable", "riccati")),
    (20, "y' = |y|^{1/3}", 0.0, 0.0, ("separable",)),
]


@pytest.mark.parametrize(
    ("num", "equation", "x0", "y0", "expected_methods"),
    TWENTY_EXERCISES,
    ids=[f"ex-{item[0]:02d}" for item in TWENTY_EXERCISES],
)
def test_twenty_exercises_odecalc_solve(
    num: int,
    equation: str,
    x0: float | None,
    y0: float | None,
    expected_methods: tuple[str, ...],
) -> None:
    result = solve(equation, x0=x0, y0=y0, x_min=-5.0, x_max=5.0, timeout=10.0)
    assert result.error is None, f"#{num} falló con error: {result.error}"
    assert result.chosen_method in expected_methods
    assert result.general is not None
    if x0 is not None and y0 is not None:
        assert result.particular is not None, f"#{num} no devolvió particular"
        assert not result.particular.expr.has(sp.I), f"#{num} devolvió unidad imaginaria: {result.particular}"
        assert result.numeric is not None and result.numeric.success


def test_twenty_exercises_mathematical_details() -> None:
    # #02 y #03 crecen rápido en [-5, 5], pero son analíticas sin blow-up finito.
    for eq, x0, y0 in (("y' = 2*x*y", 0.0, 5.0), ("y' + 4*y = 0", 0.0, 3.0)):
        res = solve(eq, x0=x0, y0=y0, x_min=-5.0, x_max=5.0, timeout=10.0)
        assert res.numeric is not None and res.numeric.success
        assert not res.numeric.blow_up

    # #08 logístico real sin +i*pi y constante exacta en #12
    res8 = solve("dy/dx = y*(1 - y/10)", x0=0.0, y0=2.0, timeout=10.0)
    assert res8.particular is not None
    assert sp.simplify(res8.particular.expr - 10 / (1 + 4 * sp.exp(-X))) == 0

    res12 = solve("y' = (x + y + 1)**2", x0=0.0, y0=0.0, timeout=10.0)
    assert res12.particular is not None
    assert sp.simplify(res12.particular.expr - (sp.tan(X + sp.pi / 4) - X - 1)) == 0
    assert res12.numeric is not None and res12.numeric.success and res12.numeric.blow_up

    # #14 notación compacta LaTeX con exponente exacto ln(3)/2
    res14 = solve("xy' + y = y^{-1}", x0=1.0, y0=2.0, timeout=10.0)
    assert res14.particular is not None
    assert res14.particular.value == sp.log(3) / 2

    # #18 Clairaut con envolvente singular -x^2 / 4
    res18 = solve("y = xy' + (y')^2", timeout=10.0)
    assert any(sp.simplify(s.expr + X**2 / 4) == 0 for s in res18.singular_solutions)

    # #19 blow-up en x = 1 e intervalo numérico truncado antes de explotar
    res19 = solve("y' = y**2", x0=0.0, y0=1.0, x_min=-5.0, x_max=5.0, timeout=10.0)
    assert res19.numeric is not None and res19.numeric.success and res19.numeric.blow_up
    assert res19.numeric.x_arr is not None and float(res19.numeric.x_arr[-1]) < 1.0

    # #20 pérdida de unicidad detectada en análisis de existencia
    res20 = resolver("y' = |y|^{1/3}", x0=0.0, y0=0.0, x_min=-2.0, x_max=2.0, timeout=10.0)
    assert res20.existencia.no_unicidad


def test_equilibrium_ic_uses_singular_solution_branch() -> None:
    res = solve("y' = y*(1 - y/10)", x0=0.0, y0=10.0, timeout=10.0)
    assert res.error is None
    assert res.particular is not None
    assert sp.simplify(res.particular.expr - 10) == 0


def test_c03_forced_timeout_degrades_to_numeric_only_when_allowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):
        raise MotorTimeoutError("Tiempo simbólico agotado simulado.")

    monkeypatch.setattr(odecalc_api, "run_with_timeout", _boom)

    result = odecalc_api.solve(
        "y' = x + y", x0=0.0, y0=1.0, x_min=0.0, x_max=1.0, timeout=0.5
    )
    assert result.error is None
    assert result.chosen_method == "numeric"
    assert result.numeric is not None and result.numeric.success
    assert any("respaldo numérico" in w.lower() for w in result.warnings)

    with pytest.raises(MotorTimeoutError):
        odecalc_api.solve(
            "y' = x + y",
            x0=0.0,
            y0=1.0,
            compute_numeric=False,
            timeout=0.5,
        )


def test_m04_curva_solucion_respects_custom_bounds() -> None:
    res = resolver("y' = y", x0=0.0, y0=1.0, x_min=-5.0, x_max=5.0, timeout=10.0)
    xs, ys = curva_solucion(res, x_min=0.0, x_max=2.0, n_points=50)
    assert len(xs) == 50
    assert xs[0] == pytest.approx(0.0)
    assert xs[-1] == pytest.approx(2.0)

    # También cuando sólo hay curva numérica cacheada en [-5, 5]
    res_num = ResultadoSolucion(
        ecuacion_texto="y' = y",
        ecuacion_latex="y' = y",
        tipo="Integración numérica",
        tipos=[],
        camino="numerica",
        solucion=res.numerico,
        x0=0.0,
        y0=1.0,
        intervalo=(-5.0, 5.0),
        numerico=res.numerico,
    )
    xs_sub, ys_sub = curva_solucion(res_num, x_min=0.0, x_max=2.0)
    assert xs_sub.size > 0
    assert float(xs_sub[0]) >= 0.0 - 1e-9
    assert float(xs_sub[-1]) <= 2.0 + 1e-9


def test_generar_ejercicio_smoke() -> None:
    for tipo in TIPOS:
        ejercicio = generar_ejercicio(tipo, dificultad=2)
        assert ejercicio.solucion_latex
        res = resolver(ejercicio.ecuacion, x0=ejercicio.x0, y0=ejercicio.y0, timeout=10.0)
        assert res.solucion_latex
