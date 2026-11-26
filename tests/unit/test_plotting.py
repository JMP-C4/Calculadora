"""Pruebas de los datos de gráficas (sin interfaz)."""

from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from odecalc.api import solve
from odecalc.models import Solution, SolveResult
from odecalc.plotting import (
    direction_field,
    equilibrium_points,
    family_curves,
    isoclines,
    phase_line,
    singular_curves,
    solution_curve,
    tangency_points,
)
from odecalc.symbols import C, X, Y


def test_direction_field_shapes_and_normalization() -> None:
    data = direction_field(X + Y, density=11)
    assert data["x"].shape == (11, 11)
    assert data["u"].shape == (11, 11)
    lengths = np.hypot(data["u"], data["v"])
    assert np.allclose(lengths, 1.0)


def test_direction_field_without_normalization() -> None:
    data = direction_field(X, density=5, normalize=False)
    assert np.allclose(data["u"], 1.0)
    assert np.allclose(data["v"], data["x"])


def test_direction_field_broadcasts_constant_rhs() -> None:
    data = direction_field(sp.Integer(2), density=4)
    assert data["u"].shape == (4, 4)
    assert np.allclose(data["v"], 2.0 / np.hypot(1.0, 2.0))


def test_solution_curve_from_numeric_result() -> None:
    result = solve(
        "y' = y",
        x0=0.0,
        y0=1.0,
        x_min=0.0,
        x_max=0.5,
        compute_numeric=True,
    )
    curve = solution_curve(result)
    assert curve is not None
    assert len(curve["x"]) > 10
    assert np.all(np.isfinite(curve["y"]))


def test_solution_curve_from_symbolic_particular() -> None:
    result = SolveResult(
        input_text="y' = y",
        particular=Solution(form="explicit", expr=sp.exp(X)),
    )
    curve = solution_curve(result)
    assert curve is not None
    assert len(curve["x"]) == 500
    assert np.all(np.isfinite(curve["y"]))


def test_solution_curve_broadcasts_constant_solution() -> None:
    result = SolveResult(
        input_text="y' = 0",
        particular=Solution(form="explicit", expr=sp.Integer(3)),
    )
    curve = solution_curve(result)
    assert curve is not None
    assert curve["x"].shape == curve["y"].shape == (500,)
    assert np.allclose(curve["y"], 3.0)


def test_solution_curve_rejects_implicit_and_constant_family() -> None:
    implicit = SolveResult(
        input_text="F",
        particular=Solution(form="implicit", expr=X * Y, value=sp.Integer(1)),
    )
    assert solution_curve(implicit) is None

    generic = SolveResult(
        input_text="y' = y",
        particular=Solution(form="explicit", expr=C * sp.exp(X)),
    )
    assert solution_curve(generic) is None


def test_family_curves() -> None:
    curves = family_curves(C * sp.exp(X), constants=(0, 1, 2))
    assert len(curves) == 3
    assert all(len(curve["x"]) > 0 for curve in curves)


def test_family_curves_broadcasts_constant_expression() -> None:
    curves = family_curves(sp.Integer(2), constants=(0,), n_points=20)
    assert len(curves) == 1
    assert curves[0]["x"].shape == curves[0]["y"].shape == (20,)


def test_family_curves_rejects_more_than_one_constant() -> None:
    c1, c2 = sp.symbols("C1 C2")
    try:
        family_curves(c1 * X + c2)
    except ValueError as exc:
        assert "constante" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba ValueError")


def test_family_curves_skips_unusable_expression() -> None:
    assert family_curves(sp.Function("f")(X)) == []


def test_singular_curves_and_tangency_point_of_clairaut() -> None:
    resultado = SolveResult(
        input_text=r"$$y = x\frac{dy}{dx} - \left(\frac{dy}{dx}\right)^2$$",
        general=Solution(form="explicit", expr=C * (X - C), constant=C),
        particular=Solution(form="explicit", expr=X - 1),
        singular_solutions=[Solution(form="explicit", expr=X**2 / 4)],
    )
    curvas = singular_curves(resultado, x_min=-4, x_max=4, n_points=50)
    assert len(curvas) == 1
    assert curvas[0]["label"] == "Envolvente singular"
    assert curvas[0]["x"].shape == curvas[0]["y"].shape == (50,)
    assert np.allclose(curvas[0]["y"], curvas[0]["x"] ** 2 / 4)

    puntos = tangency_points(resultado, x_min=-4, x_max=4)
    assert len(puntos) == 1
    assert puntos[0]["x"] == pytest.approx(2.0)
    assert puntos[0]["y"] == pytest.approx(1.0)


def test_singular_helpers_ignore_results_without_singular_solution() -> None:
    resultado = SolveResult(input_text="y' = y")
    assert singular_curves(resultado) == []
    assert tangency_points(resultado) == []


def test_isoclines_skip_non_real_branches() -> None:
    lines = isoclines(Y**2, levels=(-1.0, 1.0))
    assert [line["level"] for line in lines] == [1.0, 1.0]
    assert len(lines[0]["x"]) > 0


def test_equilibrium_points_autonomous_only() -> None:
    assert equilibrium_points(X + Y) == []
    assert equilibrium_points(Y**2 + 1) == []


def test_equilibrium_points_indeterminate_stability() -> None:
    points = equilibrium_points(Y**3)
    assert len(points) == 1
    assert points[0]["stability"].startswith("indeterminado")


def test_isoclines() -> None:
    lines = isoclines(X + Y, levels=(-1, 0, 1))
    assert len(lines) == 3
    assert all("level" in line for line in lines)


def test_isoclines_constant_branches_have_matching_shapes() -> None:
    lines = isoclines(Y, levels=(-1, 0, 1), n_points=20)
    assert len(lines) == 3
    assert all(line["x"].shape == line["y"].shape == (20,) for line in lines)


def test_equilibrium_points_and_stability() -> None:
    points = equilibrium_points(Y * (1 - Y))
    assert [point["y"] for point in points] == [0.0, 1.0]
    assert points[0]["stability"].startswith("inestable")
    assert points[1]["stability"].startswith("asint")


def test_phase_line() -> None:
    data = phase_line(Y * (1 - Y), n_points=50)
    assert data["y"].shape == (50,)
    assert data["f(y)"].shape == (50,)


def test_phase_line_broadcasts_constant_rhs() -> None:
    data = phase_line(sp.Integer(0), n_points=20)
    assert data["y"].shape == data["f(y)"].shape == (20,)
    assert np.allclose(data["f(y)"], 0.0)


def test_phase_line_rejects_non_autonomous() -> None:
    try:
        phase_line(X + Y)
    except ValueError as exc:
        assert "autónoma" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Se esperaba ValueError")
