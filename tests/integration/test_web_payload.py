"""Pruebas del adaptador web (sin abrir sockets)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.web.plotting import PLOT_MODES
from apps.web.server import plot_payload, solve_payload


def test_web_payload_solves_and_serializes() -> None:
    payload = solve_payload(
        {
            "equation": "y' = x + y",
            "x0": 0,
            "y0": 1,
            "x_min": 0,
            "x_max": 1,
            "timeout": 30,
        }
    )
    assert payload["error"] is None
    assert payload["particular"] is not None
    assert json.dumps(payload)


def test_web_payload_requires_equation() -> None:
    with pytest.raises(ValueError):
        solve_payload({})


def test_web_payload_requires_both_initial_conditions() -> None:
    with pytest.raises(ValueError):
        solve_payload({"equation": "y' = y", "x0": 0})


def test_web_payload_rejects_bad_number() -> None:
    with pytest.raises(ValueError):
        solve_payload({"equation": "y' = y", "x0": "abc", "y0": 1})


def test_web_payload_reports_parse_error_without_exception() -> None:
    payload = solve_payload({"equation": "no es una edo"})
    assert payload["error"]


def test_result_to_dict_is_stable() -> None:
    payload = solve_payload({"equation": "y' = y", "timeout": 30})
    assert {"classifications", "general", "verification", "steps"} <= payload.keys()


def test_web_payload_accepts_latex_equation() -> None:
    payload = solve_payload(
        {"equation": r"$$\frac{dy}{dx} = \frac{x^2}{y}$$", "timeout": 30}
    )
    assert payload["error"] is None
    assert payload["general"] is not None


# ---------------------------------------------------------------------------
# /plot: datos de gráficas para el selector del navegador
# ---------------------------------------------------------------------------
_WEB_CASE = {"equation": "y' = x + y", "x0": 0, "y0": 1, "x_min": 0, "x_max": 2}


def _web_plot_cases() -> dict[str, dict[str, object]]:
    return {
        "solution": _WEB_CASE,
        "direction_field": _WEB_CASE,
        "isoclines": _WEB_CASE,
        "surface": _WEB_CASE,
        "family": {"equation": "y' = y", "x_min": 0, "x_max": 2},
        "phase_line": {
            "equation": "y' = y*(1-y)",
            "x0": 0,
            "y0": 0.5,
            "x_min": 0,
            "x_max": 2,
        },
        "equilibria": {
            "equation": "y' = y*(1-y)",
            "x0": 0,
            "y0": 0.5,
            "x_min": 0,
            "x_max": 2,
        },
    }


@pytest.mark.parametrize("mode", sorted(PLOT_MODES))
def test_plot_payload_every_mode_is_available_and_json_safe(mode: str) -> None:
    payload = _web_plot_cases()[mode]
    data = plot_payload({**payload, "mode": mode})

    assert data["mode"] == mode
    assert data["label"] == PLOT_MODES[mode]
    assert data["available"] is True
    assert data["figure"] is not None
    json.dumps(data, allow_nan=False)

    figure = data["figure"]
    if mode == "surface":
        assert figure["kind"] == "3d"
        assert figure["surface"]["z"]
    else:
        assert figure["kind"] == "2d"
        assert figure["traces"]


def test_plot_payload_points_and_text_for_equilibria() -> None:
    data = plot_payload(
        {"equation": "y' = y*(1-y)", "x0": 0, "y0": 0.5, "mode": "equilibria"}
    )
    points = [
        trace
        for trace in data["figure"]["traces"]
        if trace["type"] == "points"
    ]
    ys = sorted(float(point["x"][0]) for point in points)
    assert ys == [0.0, 1.0]
    assert all(point["text"] for point in points)


def test_plot_payload_phase_line_unavailable_for_non_autonomous() -> None:
    data = plot_payload({**_WEB_CASE, "mode": "phase_line"})
    assert data["available"] is False
    assert "autónomas" in data["notice"]
    assert data["figure"] is None


def test_plot_payload_equilibria_unavailable_for_non_autonomous() -> None:
    data = plot_payload({**_WEB_CASE, "mode": "equilibria"})
    assert data["available"] is False
    assert "autónomas" in data["notice"]


def test_plot_payload_solution_falls_back_to_family_without_pvi() -> None:
    data = plot_payload(
        {"equation": "y' = y", "mode": "solution", "x_min": 0, "x_max": 2}
    )
    # Sin PVI no hay solución particular explícita, pero SÍ familia general.
    assert data["available"] is True
    assert "familia" in data["notice"].lower()
    titles = {trace["label"] for trace in data["figure"]["traces"]}
    assert any(label and label.startswith("C =") for label in titles)


def test_plot_payload_reports_solve_error() -> None:
    data = plot_payload({"equation": "no es una edo", "mode": "solution"})
    assert data["available"] is False
    assert "No se puede graficar" in data["notice"]


def test_plot_payload_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError) as excinfo:
        plot_payload({**_WEB_CASE, "mode": "polar"})
    assert "Modo de gráfica inválido" in str(excinfo.value)


def test_web_page_lists_every_plot_mode() -> None:
    html = Path("apps/web/static/index.html").read_text(encoding="utf-8")
    assert "cdn.plot.ly/plotly" in html
    for key, label in PLOT_MODES.items():
        assert f'<option value="{key}">' in html
        assert label in html
