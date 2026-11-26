"""Pruebas de integración de ``odecalc.api.solve``."""

from __future__ import annotations

import time

import numpy as np
import pytest
import sympy as sp

import odecalc.api as api_module
from odecalc.api import _compare_numeric, _numeric_steps, solve
from odecalc.models import NumericResult, Solution, SolveResult
from odecalc.symbols import C, X
from odecalc.timeout import TimeoutError, run_with_timeout


def test_solve_returns_full_contract() -> None:
    result = solve("y' = x + y", x0=0.0, y0=1.0, x_min=0.0, x_max=1.0, timeout=60)
    assert result.error is None
    assert result.general is not None
    assert result.particular is not None
    assert result.verification is not None and result.verification.status == "ok"
    assert result.particular_verification is not None
    assert result.particular_verification.status == "ok"
    assert result.classifications
    assert result.chosen_method
    assert result.steps
    assert result.validity.domain
    assert result.numeric is not None and result.numeric.success
    assert result.timing_ms["total"] > 0


def test_forced_method_is_used() -> None:
    result = solve("y' = y**2 - x*y + 1", method="riccati")
    assert result.chosen_method == "riccati"


def test_unknown_forced_method_falls_back_with_warning() -> None:
    result = solve("y' = x*y", method="metodo_inexistente")
    assert result.chosen_method
    assert any("no figura" in warning for warning in result.warnings)


def test_parse_error_is_reported_without_exception() -> None:
    result = solve("esto no es una edo")
    assert result.error is not None
    assert result.general is None
    assert result.classifications == []


def test_security_error_is_reported() -> None:
    result = solve("y' = __import__('os').system('echo pwned')")
    assert result.error is not None
    assert "no permitid" in result.error.lower() or "guion" in result.error.lower()


def test_numeric_backup_covers_interval() -> None:
    result = solve(
        "y' = y**2 - x*y + 1",
        x0=0.0,
        y0=1.0,
        x_min=0.0,
        x_max=0.5,
        compute_numeric=True,
    )
    assert result.numeric is not None
    assert result.numeric.success
    assert result.numeric.x_arr is not None
    assert result.numeric.y_arr is not None
    assert len(result.numeric.x_arr) > 100
    assert np.isclose(result.numeric.y_arr[0], 1.0)


def test_implicit_pvi() -> None:
    result = solve("y' = -(2*x*y+1)/(x**2+3*y**2)", x0=1.0, y0=1.0)
    assert result.particular is not None
    assert result.particular.is_implicit
    assert result.particular_verification is not None
    assert result.particular_verification.status == "ok"


def test_timeout_kills_slow_process() -> None:
    with pytest.raises(TimeoutError):
        run_with_timeout(time.sleep, 5.0, timeout=0.2)


def test_timeout_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        run_with_timeout(time.sleep, 0.0, timeout=0.0)


def test_warnings_are_unique() -> None:
    result = solve("y' = y + 1/x", x0=1.0, y0=0.0)
    assert len(result.warnings) == len(set(result.warnings))


@pytest.mark.parametrize(
    "equation, method",
    [
        ("y' = x + y", "linear"),
        ("y' = x*y", "separable"),
        ("y' = y/x", "homogeneous"),
        ("y' = y**2 - x*y + 1", "riccati"),
        ("y' = y/x + sqrt(y)", "bernoulli"),
        ("y' = (x+y)**2", "substitution_linear_combo"),
        ("y' = (x+y+1)/(x-y-3)", "reducible_homogeneous"),
        ("y' = -(2*x*y+1)/(x**2+3*y**2)", "exact"),
        ("y = x*y' + y'**2", "clairaut"),
        ("y dx - x dy = 0", "integrating_factor_xy"),
        ("(x+y) dx + dy = 0", "integrating_factor_x_plus_y"),
    ],
)
def test_forced_methods_are_available_and_verify(equation: str, method: str) -> None:
    result = solve(equation, method=method, compute_numeric=False)
    assert result.chosen_method == method
    assert result.verification is not None
    assert result.verification.status == "ok"


def test_unimplemented_lagrange_is_never_presented_as_solution() -> None:
    result = solve("y = x*y'**2 + y'", method="lagrange", compute_numeric=False)
    assert result.general is None
    assert result.error is not None
    assert any("Lagrange" in warning for warning in result.warnings)
    assert any(not attempt.success for attempt in result.attempts)


def test_numeric_only_solution_includes_steps() -> None:
    result = solve(
        "y' = sin(x*y)",
        x0=0.0,
        y0=1.0,
        x_min=0.0,
        x_max=1.0,
        compute_numeric=True,
    )
    assert result.error is None
    assert result.general is None
    assert result.chosen_method == "numeric"
    assert result.numeric is not None and result.numeric.success
    assert len(result.steps) >= 2
    assert result.validity.domain


def test_numeric_failure_is_reported_without_hiding_symbolic_solution() -> None:
    result = solve("y' = y", x0=0.0, y0=1.0, x_min=1.0, x_max=0.0, compute_numeric=True)
    assert result.general is not None
    assert result.numeric is not None and not result.numeric.success
    assert any("intervalo" in warning for warning in result.warnings)
    assert result.error is None


def test_missing_symbolic_and_numeric_solution_sets_error() -> None:
    result = solve(
        "y' = sin(x*y)",
        x0=0.0,
        y0=1.0,
        x_min=1.0,
        x_max=0.0,
        compute_numeric=True,
    )
    assert result.general is None
    assert result.numeric is not None and not result.numeric.success
    assert result.error is not None


def test_numeric_steps_describe_blow_up() -> None:
    assert _numeric_steps(SolveResult(input_text="")) == []
    result = SolveResult(
        input_text="y' = 1/y",
        numeric=NumericResult(
            x_arr=None,
            y_arr=None,
            success=False,
            message="posible explosión",
            blow_up=True,
        ),
    )
    steps = _numeric_steps(result)
    assert len(steps) == 3
    assert "explosión" in steps[-1].title


def test_compare_numeric_skips_incomplete_results() -> None:
    empty = SolveResult(input_text="")
    _compare_numeric(empty)
    assert empty.warnings == []

    implicit = SolveResult(
        input_text="",
        numeric=NumericResult(
            x_arr=np.array([0.0, 1.0]),
            y_arr=np.array([1.0, 2.0]),
            success=True,
            message="ok",
        ),
        particular=Solution(form="implicit", expr=X, value=sp.Integer(1)),
    )
    _compare_numeric(implicit)
    assert implicit.warnings == []

    no_arrays = SolveResult(
        input_text="",
        numeric=NumericResult(
            x_arr=None, y_arr=None, success=True, message="ok"
        ),
        particular=Solution(form="explicit", expr=X),
    )
    _compare_numeric(no_arrays)
    assert no_arrays.warnings == []


def test_compare_numeric_ignores_nonfinite_or_unlambdifiable_solutions() -> None:
    nonfinite = SolveResult(
        input_text="",
        numeric=NumericResult(
            x_arr=np.array([1.0, 2.0]),
            y_arr=np.array([1.0, 2.0]),
            success=True,
            message="ok",
        ),
        particular=Solution(form="explicit", expr=sp.sqrt(-1 - X**2)),
    )
    _compare_numeric(nonfinite)
    assert nonfinite.numeric is not None
    assert nonfinite.numeric.error_estimate is None

    unusable = SolveResult(
        input_text="",
        numeric=NumericResult(
            x_arr=np.array([1.0, 2.0]),
            y_arr=np.array([1.0, 2.0]),
            success=True,
            message="ok",
        ),
        particular=Solution(form="explicit", expr=sp.Function("f")(X)),
    )
    _compare_numeric(unusable)
    assert unusable.numeric is not None
    assert unusable.numeric.error_estimate is None


def test_compare_numeric_warns_on_large_difference() -> None:
    result = SolveResult(
        input_text="",
        numeric=NumericResult(
            x_arr=np.array([0.0, 1.0]),
            y_arr=np.array([1.0, 2.718281828]),
            success=True,
            message="ok",
        ),
        particular=Solution(form="explicit", expr=X**2),
    )
    _compare_numeric(result)
    assert result.numeric is not None
    assert result.numeric.error_estimate is not None
    assert any("difieren" in warning for warning in result.warnings)


def test_clairaut_latex_yields_family_envelope_and_particular() -> None:
    ecuacion = r"$$y = x\frac{dy}{dx} - \left(\frac{dy}{dx}\right)^2$$"
    general = solve(ecuacion, timeout=20)
    assert general.error is None
    assert general.chosen_method == "clairaut"
    assert general.general is not None
    assert sp.simplify(general.general.expr - C * (X - C)) == 0
    assert len(general.singular_solutions) == 1
    assert sp.simplify(general.singular_solutions[0].expr - X**2 / 4) == 0

    pvi = solve(
        ecuacion,
        x0=2.0,
        y0=1.0,
        x_min=-4.0,
        x_max=4.0,
        timeout=20,
    )
    assert pvi.error is None
    assert pvi.particular is not None
    assert sp.simplify(pvi.particular.expr - (X - 1)) == 0


def test_singular_initial_point_does_not_hang() -> None:
    ecuacion = r"$$(3xy + y^2)dx + (x^2 + xy)dy = 0$$"
    resultado = solve(
        ecuacion,
        x0=0.0,
        y0=1.0,
        x_min=-5.0,
        x_max=5.0,
        timeout=10,
    )
    assert resultado.error is None
    assert resultado.general is not None
    assert resultado.numeric is not None and not resultado.numeric.success
    assert any(
        "derivada" in aviso and "inicial" in aviso
        for aviso in resultado.warnings
    )


def test_failed_methods_fall_back_to_dsolve(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args, **kwargs):
        raise RuntimeError("método roto a propósito")

    monkeypatch.setattr(api_module, "solve_method", broken)
    result = api_module.solve("y' = y", compute_numeric=False)
    assert result.chosen_method == "dsolve"
    assert result.general is not None
    assert result.verification is not None and result.verification.status == "ok"
    assert any("dsolve" in warning for warning in result.warnings)
    assert any(not attempt.success for attempt in result.attempts)
