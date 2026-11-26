"""Pruebas del diálogo de tiempo límite en la interfaz Streamlit."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from core.tipos import TiempoAgotado  # noqa: E402
from ui import streamlit_app  # noqa: E402

_RAIZ = Path(__file__).resolve().parents[2] / "app.py"


def _app() -> AppTest:
    return AppTest.from_file(str(_RAIZ), default_timeout=90)


def test_timeout_ofrece_continuar_y_cancelar(monkeypatch: pytest.MonkeyPatch) -> None:
    resolver_real = streamlit_app.resolver
    plazos: list[float] = []

    def resolver_falso(*args, **kwargs):
        plazos.append(float(kwargs["timeout"]))
        if len(plazos) == 1:
            raise TiempoAgotado(
                "El cálculo excedió el tiempo límite de 10 s. "
                "Se recomienda simplificar la ecuación o usar el respaldo numérico."
            )
        return resolver_real(*args, **kwargs)

    monkeypatch.setattr(streamlit_app, "resolver", resolver_falso)
    app = _app()
    app.run()
    app.button(key="resolver_boton").click().run()

    assert not app.exception
    assert app.session_state["timeout_pendiente"] is not None
    assert any(
        "Continuar cálculo" in str(getattr(boton, "label", ""))
        for boton in app.button
    )
    assert any("Cancelar" in str(getattr(boton, "label", "")) for boton in app.button)

    app.button(key="edo_timeout_continuar").click().run()

    assert plazos == [10.0, 90.0]
    assert app.session_state["timeout_pendiente"] is None
    assert app.session_state["resultado"] is not None
    assert not app.exception


def test_timeout_se_puede_cancelar(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolver_falso(*args, **kwargs):
        raise TiempoAgotado("El cálculo excedió el tiempo límite de 10 s.")

    monkeypatch.setattr(streamlit_app, "resolver", resolver_falso)
    app = _app()
    app.run()
    app.button(key="resolver_boton").click().run()
    app.button(key="edo_timeout_cancelar").click().run()

    assert not app.exception
    assert app.session_state["timeout_pendiente"] is None
    assert app.session_state["resultado"] is None
    assert "cancelada" in str(app.session_state["error_resolver"]).lower()
