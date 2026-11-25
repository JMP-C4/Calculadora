"""Pruebas de serialización JSON del resultado."""

from __future__ import annotations

import json

import pytest

import odecalc
from odecalc.api import solve
from odecalc.serialization import result_to_dict


def test_result_is_json_serializable() -> None:
    result = solve("y' = x + y", x0=0.0, y0=1.0, x_min=0.0, x_max=0.5)
    payload = result_to_dict(result)
    encoded = json.dumps(payload)
    assert "chosen_method" in encoded
    assert payload["general"]["form"] == "explicit"
    assert payload["particular"]["form"] == "explicit"
    assert payload["classifications"]
    assert payload["steps"]
    assert payload["verification"]
    assert payload["validity"]["domain"]


def test_numeric_arrays_become_lists() -> None:
    result = solve(
        "y' = x + y",
        x0=0.0,
        y0=1.0,
        x_min=0.0,
        x_max=0.5,
        compute_numeric=True,
    )
    payload = result_to_dict(result)
    assert isinstance(payload["numeric"]["x_arr"], list)
    assert isinstance(payload["numeric"]["y_arr"], list)
    json.dumps(payload)


def test_error_result_serializes() -> None:
    payload = result_to_dict(solve("no es una edo"))
    assert payload["error"]
    assert payload["general"] is None
    json.dumps(payload)


def test_lazy_package_exports() -> None:
    from odecalc.classify import classify as classify_function

    assert callable(odecalc.solve)
    assert callable(odecalc.parse_ode)
    assert callable(classify_function)
    assert callable(odecalc.result_to_dict)
    assert odecalc.__version__ == "2.0.0"
    with pytest.raises(AttributeError):
        odecalc.nonexistent
