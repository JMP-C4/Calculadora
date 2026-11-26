"""Regresión web del caso de Clairaut y su envolvente."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

_RAIZ = Path(__file__).resolve().parents[2] / "app.py"
_CLAIRAUT = r"$$y = x\frac{dy}{dx} - \left(\frac{dy}{dx}\right)^2$$"


def test_clairaut_se_resuelve_y_se_grafica_en_la_web() -> None:
    app = AppTest.from_file(str(_RAIZ), default_timeout=120)
    app.run()
    app.session_state["ecuacion_input"] = _CLAIRAUT
    app.session_state["x0_input"] = 2.0
    app.session_state["y0_input"] = 1.0
    app.session_state["x_min_input"] = -4.0
    app.session_state["x_max_input"] = 4.0
    app.run()
    app.button(key="resolver_boton").click().run()

    assert not app.exception
    resultado = app.session_state["resultado"]
    assert resultado is not None
    assert resultado.resultado_motor.chosen_method == "clairaut"

    app.button(key="edo_boton_graficas").click().run()
    selector = next(item for item in app.selectbox if item.key == "edo_grafica_activa")
    for modo in ("Familia de curvas", "Campo de direcciones"):
        selector.set_value(modo).run()
        assert not app.exception
        assert any("envolvente" in caption.value.lower() for caption in app.caption)
