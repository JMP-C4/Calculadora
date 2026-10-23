"""Tests unitarios de la biblioteca de ejercicios."""

from __future__ import annotations

import tkinter as tk

import pytest

from data.exercises import load_exercises
from ui.exercise_library import ExerciseLibrary


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_library_lists_all_exercises(root):
    library = ExerciseLibrary(root)

    assert len(library.tree.get_children()) == len(load_exercises())


def test_selecting_exercise_invokes_callback(root):
    received = []
    library = ExerciseLibrary(root, on_select=received.append)

    library.select_exercise("sep-01")
    library._on_selection()

    assert received
    assert received[0].id == "sep-01"


def test_selected_exercise_returns_object(root):
    library = ExerciseLibrary(root)
    library.select_exercise("lin-01")

    selected = library.selected_exercise()

    assert selected is not None
    assert selected.id == "lin-01"
    assert selected.equation_text == "dy/dx = x + y"


def test_copy_selected_equation(root):
    library = ExerciseLibrary(root)
    library.select_exercise("sep-01")
    root.update()

    assert library.copy_selected_equation() is True

    try:
        clipboard = root.clipboard_get()
    except tk.TclError:  # pragma: no cover - portapapeles no disponible
        pytest.skip("Portapapeles no disponible en el entorno")
    assert clipboard == "dy/dx = y"


def test_copy_without_selection_returns_false(root):
    library = ExerciseLibrary(root)

    assert library.copy_selected_equation() is False
