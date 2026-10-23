"""Tests unitarios del panel de condiciones."""

from __future__ import annotations

import tkinter as tk

import pytest

from ui.condition_panel import ConditionPanel, SolverConditions


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_default_interval_is_visible(root):
    panel = ConditionPanel(root)

    conditions = panel.get_conditions()

    assert conditions.x_min == -5.0
    assert conditions.x_max == 5.0
    assert conditions.x0 is None
    assert conditions.y0 is None


def test_set_and_get_roundtrip(root):
    panel = ConditionPanel(root)
    original = SolverConditions(
        x0=0.0,
        y0=1.5,
        x_min=-2.0,
        x_max=3.0,
        y_min=-4.0,
        y_max=4.0,
    )

    panel.set_conditions(original)

    assert panel.get_conditions() == original


def test_empty_fields_are_optional(root):
    panel = ConditionPanel(root)
    panel.set_conditions(
        SolverConditions(x0=1.0, y0=2.0, x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0)
    )

    panel._vars["x0"].set("")
    panel._vars["y0"].set("")

    conditions = panel.get_conditions()
    assert conditions.x0 is None
    assert conditions.y0 is None
