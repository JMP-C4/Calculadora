"""Tests unitarios de la previsualización matemática."""

from __future__ import annotations

import tkinter as tk
from types import SimpleNamespace

import pytest

from ui.math_preview import MathPreview


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_placeholder_is_shown_initially(root):
    preview = MathPreview(root)

    assert preview.axes.texts
    assert "f(x" in preview.current_latex


def test_render_equation(root):
    preview = MathPreview(root)

    preview.render(r"\frac{dy}{dx} = x + y")

    assert preview.axes.texts
    rendered = preview.axes.texts[-1].get_text()
    assert "x + y" in rendered
    assert rendered.startswith("$")


def test_empty_equation_restores_placeholder(root):
    preview = MathPreview(root)
    preview.render(r"\frac{dy}{dx} = y")

    preview.render("")

    assert "f(x" in preview.current_latex


def test_conditions_are_rendered_together(root):
    preview = MathPreview(root)
    conditions = SimpleNamespace(x0=0.0, y0=1.0)

    preview.render(r"\frac{dy}{dx} = y", conditions)

    rendered = preview.axes.texts[-1].get_text()
    assert "y(0) = 1" in rendered
