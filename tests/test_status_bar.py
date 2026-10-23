"""Tests unitarios de la barra de estado."""

from __future__ import annotations

import tkinter as tk

import pytest

from ui.status_bar import StatusBar


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    window.withdraw()
    yield window
    window.destroy()


def test_default_message(root):
    bar = StatusBar(root)

    assert bar.message == "Listo"
    assert "Info" in bar.level_style


def test_status_levels_change_style(root):
    bar = StatusBar(root)

    bar.set_status("Error de sintaxis", "error")
    assert bar.message == "Error de sintaxis"
    assert "Error" in bar.level_style

    bar.set_status("Cuidado", "warning")
    assert "Warning" in bar.level_style

    bar.set_status("Todo bien", "info")
    assert "Info" in bar.level_style


def test_spinner_visibility(root):
    bar = StatusBar(root)

    bar.show_spinner()
    assert bar.spinner.winfo_manager() != ""

    bar.hide_spinner()
    assert bar.spinner.winfo_manager() == ""
