"""Tests unitarios del panel paso a paso."""

from __future__ import annotations

import tkinter as tk

import pytest

from math_engine.step_generator import SolutionStep
from ui.step_by_step_panel import StepByStepPanel


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def _steps() -> list[SolutionStep]:
    return [
        SolutionStep(
            number=1,
            operation="Identificar el tipo de EDO",
            latex_expr=r"\frac{dy}{dx} = y",
            justification="La ecuación es separable.",
            detail="f(x) = 1, h(y) = y.",
            ascii_expr="dy/dx = y",
        ),
        SolutionStep(
            number=2,
            operation="Separar variables",
            latex_expr=r"\frac{1}{y}\,dy = dx",
            justification="Se agrupan las variables.",
            detail=None,
            ascii_expr="dy/y = dx",
        ),
    ]


def test_display_steps_shows_number_and_justification(root):
    panel = StepByStepPanel(root)

    panel.display_steps(_steps(), ascii_text="texto ascii")

    content = panel.text.get("1.0", "end")
    assert "Paso 1" in content
    assert "Paso 2" in content
    assert "La ecuación es separable." in content
    assert panel.ascii_text == "texto ascii"


def test_math_figures_are_embedded(root):
    panel = StepByStepPanel(root)

    panel.display_steps(_steps())

    assert len(panel._embedded) == 2


def test_ascii_is_built_when_not_provided(root):
    panel = StepByStepPanel(root)

    panel.display_steps(_steps())

    assert "Paso 1" in panel.ascii_text
    assert "dy/dx = y" in panel.ascii_text


def test_clear_removes_content(root):
    panel = StepByStepPanel(root)
    panel.display_steps(_steps())

    panel.clear()

    assert panel.text.get("1.0", "end").strip() == ""
    assert panel.ascii_text == ""
    assert panel._embedded == []


def test_copy_to_clipboard(root):
    panel = StepByStepPanel(root)
    panel.display_steps(_steps(), ascii_text="contenido para copiar")

    panel.copy_to_clipboard()
    root.update()

    try:
        clipboard = root.clipboard_get()
    except tk.TclError:  # pragma: no cover - portapapeles no disponible
        pytest.skip("Portapapeles no disponible en el entorno")
    assert clipboard == "contenido para copiar"
