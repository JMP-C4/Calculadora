"""Pruebas de las figuras Plotly que consume la interfaz web."""

from __future__ import annotations

import pytest

pytest.importorskip("plotly")

from core.hibrido import curvas_familia, resolver  # noqa: E402
from ui.graficas import figura_familia, figura_solucion  # noqa: E402

_CLAIRAUT = r"$$y = x\frac{dy}{dx} - \left(\frac{dy}{dx}\right)^2$$"


@pytest.fixture(scope="module")
def clairaut():
    return resolver(
        _CLAIRAUT, x0=2.0, y0=1.0, x_min=-4.0, x_max=4.0, timeout=30
    )


def test_clairaut_solution_shows_envelope_and_tangency(clairaut) -> None:
    figura = figura_solucion(clairaut)
    nombres = [traza.name for traza in figura.data]
    assert "Solución" in nombres
    assert "Envolvente singular" in nombres
    assert "Tangencia" in nombres


def test_clairaut_family_shows_tangent_lines_and_envelope(clairaut) -> None:
    figura = figura_familia(curvas_familia(clairaut), resultado=clairaut)
    nombres = [traza.name for traza in figura.data]
    assert "C = -3" in nombres
    assert "C = 3" in nombres
    assert "Envolvente singular" in nombres
