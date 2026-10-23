"""Tests unitarios del campo de ecuación y la barra de símbolos."""

from __future__ import annotations

import tkinter as tk

import pytest

from ui.equation_input import EquationInput
from ui.symbol_toolbar import SymbolToolbar


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_get_and_set_text(root):
    field = EquationInput(root)

    field.set_text("dy/dx = x + y")

    assert field.get_text() == "dy/dx = x + y"


def test_insert_token_places_cursor_inside_parentheses(root):
    field = EquationInput(root)
    field.set_text("")

    field.insert_token("exp()", place_cursor_inside=True)

    assert field.get_text() == "exp()"
    assert field.get_cursor_position() == 4


def test_insert_token_without_parentheses_leaves_cursor_at_end(root):
    field = EquationInput(root)
    field.set_text("")

    field.insert_token("pi")

    assert field.get_text() == "pi"
    assert field.get_cursor_position() == 2


def test_on_change_callback_is_triggered(root):
    changes: list[str] = []
    field = EquationInput(root, on_change=changes.append)

    field.set_text("dy/dx = y")
    field.insert_token("+1")

    assert changes
    assert changes[-1] == "dy/dx = y+1"


def test_keyboard_shortcut_is_bound_and_inserts_token(root):
    field = EquationInput(root)

    assert field._text.bind("<Control-e>")

    field._on_shortcut("exp()", True, None)

    assert "exp()" in field.get_text()
    assert field.get_cursor_position() == field.get_text().index(")")


def test_toolbar_buttons_insert_tokens(root):
    field = EquationInput(root)
    field.pack()
    toolbar = SymbolToolbar(root, field)
    toolbar.pack()

    toolbar.buttons["sqrt()"].invoke()

    assert "sqrt()" in field.get_text()
    assert field.get_cursor_position() == field.get_text().index(")")
