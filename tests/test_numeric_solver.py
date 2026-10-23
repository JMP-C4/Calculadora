"""Tests unitarios del solver numérico."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from math_engine.numeric_solver import solve_numeric, x, y


def _conditions(x0=0.0, y0=1.0, x_min=0.0, x_max=2.0):
    return SimpleNamespace(
        x0=x0,
        y0=y0,
        x_min=x_min,
        x_max=x_max,
        y_min=None,
        y_max=None,
    )


def test_exponential_growth_is_accurate():
    result = solve_numeric(y, _conditions())

    assert result.success is True
    assert result.x_arr is not None
    assert result.y_arr is not None
    assert np.max(np.abs(result.y_arr - np.exp(result.x_arr))) < 1e-4


def test_at_least_five_hundred_points():
    result = solve_numeric(y, _conditions())

    assert result.x_arr is not None
    assert len(result.x_arr) >= 500


def test_solution_covers_interval():
    result = solve_numeric(y, _conditions(0.0, 1.0, -2.0, 2.0))

    assert result.success is True
    assert result.x_arr is not None
    assert np.isclose(result.x_arr[0], -2.0)
    assert np.isclose(result.x_arr[-1], 2.0)


def test_invalid_interval_returns_failure():
    result = solve_numeric(y, _conditions(0.0, 1.0, 2.0, 1.0))

    assert result.success is False
    assert result.x_arr is None
    assert result.y_arr is None
    assert result.message


def test_missing_conditions_returns_failure():
    result = solve_numeric(y, None)

    assert result.success is False
    assert "condiciones" in result.message.lower()


def test_rhs_without_y_is_supported():
    result = solve_numeric(x, _conditions(0.0, 0.0, 0.0, 2.0))

    assert result.success is True
    assert result.y_arr is not None
    assert np.max(np.abs(result.y_arr - result.x_arr**2 / 2)) < 1e-6
