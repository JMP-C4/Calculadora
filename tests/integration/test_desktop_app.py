"""Pruebas de la interfaz de escritorio Tk basada en ``odecalc``."""

from __future__ import annotations

import time
import types

import pytest
import sympy as sp

tk = pytest.importorskip("tkinter")
pytest.importorskip("matplotlib")

from apps.desktop import app as desktop  # noqa: E402
from apps.desktop.plot_panel import PlotMode  # noqa: E402
from core.notacion import NATURAL, normalizar  # noqa: E402
from odecalc.models import Solution  # noqa: E402
from odecalc.symbols import C, X  # noqa: E402


@pytest.fixture
def window():
    try:
        application = desktop.ODEApp()
    except tk.TclError as exc:  # pragma: no cover - entorno sin display
        pytest.skip(f"Tk no disponible: {exc}")
    application.withdraw()
    yield application
    application.destroy()


def _wait_until(application: tk.Tk, predicate, timeout: float = 60.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.update()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _fake_result(**overrides) -> types.SimpleNamespace:
    verification = types.SimpleNamespace(status="ok", message="Residuo numérico 0.")
    defaults = {
        "input_text": "y' = y",
        "error": None,
        "standard_form": "y' - y = 0",
        "chosen_method": "linear",
        "general": types.SimpleNamespace(
            is_explicit=True,
            latex="y = C1*exp(x)",
            expr=C * sp.exp(X),
            value=C,
        ),
        "particular": types.SimpleNamespace(
            is_explicit=True,
            latex="y = exp(x)",
            expr=sp.exp(X),
            value=None,
        ),
        "verification": verification,
        "particular_verification": types.SimpleNamespace(
            status="ok", message="El PVI se cumple."
        ),
        "validity": types.SimpleNamespace(domain="Reales", interval="(0, oo)"),
        "numeric": types.SimpleNamespace(success=False, message="RK45 correcto."),
        "singular_solutions": [types.SimpleNamespace(latex="y = 0")],
        "classifications": [
            types.SimpleNamespace(
                priority=12,
                name="Lineal de primer orden",
                method="linear",
                evidence="P(x) y Q(x) continuas.",
            )
        ],
        "steps": [
            types.SimpleNamespace(
                number=1,
                title="Forma estándar",
                latex="y' - y = 0",
                explanation="Se identifica P y Q.",
            )
        ],
        "warnings": ["Advertencia de prueba."],
    }
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def _record_errors(monkeypatch) -> list[tuple]:
    calls: list[tuple] = []

    def fake_showerror(*args, **kwargs) -> None:
        calls.append((args, kwargs))

    monkeypatch.setattr(desktop.messagebox, "showerror", fake_showerror)
    return calls


def test_initial_state(window: tk.Tk) -> None:
    assert window.equation.get() == desktop.EXAMPLES[0]
    assert window.status.cget("text") == "Listo."
    for widget in (
        window.summary,
        window.methods,
        window.steps,
        window.warnings,
        window.explanation,
    ):
        assert str(widget.cget("state")) == "disabled"
    assert window.plot_panel is not None
    assert window.plot_panel.mode_selector.get() == PlotMode.SOLUTION.value
    assert len(window.plot_panel.mode_selector.cget("values")) == len(PlotMode)
    assert window.header_plot_button.cget("text") == "Gráficas"


def test_header_graph_menu_switches_canvas(window: tk.Tk) -> None:
    window._vista.set("Salida")
    window._set_plot_mode(PlotMode.DIRECTION_FIELD.value)

    assert window._vista.get() == "Lienzo"
    assert window.plot_panel.mode_selector.get() == PlotMode.DIRECTION_FIELD.value


def test_header_graph_button_opens_canvas(window: tk.Tk, monkeypatch) -> None:
    popped: list[tuple[int, int]] = []
    monkeypatch.setattr(
        window.header_plot_menu,
        "tk_popup",
        lambda x, y: popped.append((x, y)),
    )
    window._vista.set("Salida")

    window.header_plot_button.invoke()
    window.update_idletasks()
    window.update()

    assert window._vista.get() == "Lienzo"
    assert popped
    etiqueta = window.header_plot_menu.entryconfigure(1)["label"][-1]
    assert etiqueta == PlotMode.DIRECTION_FIELD.value

    window.header_plot_menu.invoke(1)
    assert window.plot_panel.mode_selector.get() == PlotMode.DIRECTION_FIELD.value


def test_header_exercise_and_instructions_buttons(window: tk.Tk) -> None:
    assert window.header_exercise_button.cget("text") == "Ver ejercicio"
    assert window.header_instructions_button.cget("text") == "Instrucciones"

    window._vista.set("Lienzo")
    window.header_exercise_button.invoke()
    assert window._vista.get() == "Salida"

    window.header_instructions_button.invoke()
    window.update_idletasks()
    manual = window._manual_window
    assert manual is not None and manual.winfo_exists()
    manual.destroy()


def test_empty_equation_is_rejected(window: tk.Tk, monkeypatch) -> None:
    errors = _record_errors(monkeypatch)
    window.equation.set("   ")
    window._start()
    assert errors


def test_invalid_numbers_are_rejected(window: tk.Tk, monkeypatch) -> None:
    errors = _record_errors(monkeypatch)
    window.x0.set("no-numero")
    window._start()
    assert errors


def test_incomplete_initial_conditions_are_rejected(window: tk.Tk, monkeypatch) -> None:
    errors = _record_errors(monkeypatch)
    window.x0.set("0")
    window.y0.set("")
    window._start()
    assert errors


def test_successful_solve_renders_all_tabs(window: tk.Tk, monkeypatch) -> None:
    resultado = _fake_result()
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: resultado)
    window._notacion_salida.set("Algebraica")

    window.equation.set("y' = y")
    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")

    assert "verificada" in window.status.cget("text").lower()
    assert "Solución particular" in window.summary.get("1.0", "end")
    assert window._math_images
    assert (
        window._expr(resultado.particular.latex, resultado.particular, "Infija")
        == "y = exp(x)"
    )
    assert "Lineal de primer orden" in window.methods.get("1.0", "end")
    assert "Forma estándar" in window.steps.get("1.0", "end")
    assert "Advertencia de prueba." in window.warnings.get("1.0", "end")
    assert window.explanation.get("1.0", "end").strip()
    assert window._vista.get() == "Salida"
    assert str(window.solve_button.cget("state")) == "normal"
    assert window.plot_panel is not None
    assert window.plot_panel.axes.lines


def test_notacion_switch_updates_salida(window: tk.Tk, monkeypatch) -> None:
    solucion = Solution(form="explicit", expr=sp.exp(X), latex=r"y = e^{x}")
    resultado = _fake_result(general=None, particular=solucion)
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: resultado)
    monkeypatch.setattr(desktop, "guardar_preferencia", normalizar)

    window._notacion_salida.set("Algebraica")
    window._on_notacion_cambiada()
    window.equation.set("y' = y")
    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")
    algebraica = window.summary.get("1.0", "end")

    window._notacion_salida.set("Infija")
    window._on_notacion_cambiada()
    infija = window.summary.get("1.0", "end")

    assert "exp(x)" not in algebraica
    assert "exp(x)" in infija
    assert window._vista.get() == "Salida"


def test_natural_notation_applies_to_steps(window: tk.Tk, monkeypatch) -> None:
    resultado = _fake_result(
        steps=[
            types.SimpleNamespace(
                number=1,
                title="Derivada",
                latex="",
                explanation="La ecuación y' = y se escribe como dy/dx = y.",
            )
        ]
    )
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: resultado)
    monkeypatch.setattr(desktop, "guardar_preferencia", normalizar)

    window._notacion_salida.set(NATURAL)
    window._on_notacion_cambiada()
    window.equation.set("y' = y")
    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")

    assert "y′" in window.steps.get("1.0", "end")
    assert window._expr(r"\frac{dy}{dx} = y'", None, NATURAL) == "dy/dx = y′"
    assert window._vista.get() == "Salida"


def test_plot_mode_without_support_shows_notice(window: tk.Tk, monkeypatch) -> None:
    result = _fake_result(input_text="y' = x + y")
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: result)

    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")
    assert window.plot_panel is not None

    window.plot_panel.mode_selector.set(PlotMode.PHASE_LINE.value)
    window.plot_panel._on_mode_selected()
    assert "autónomas" in window.plot_panel.notice.cget("text")


def test_unverified_result_is_shown_as_warning(window: tk.Tk, monkeypatch) -> None:
    result = _fake_result(
        verification=types.SimpleNamespace(status="failed", message="Residuo distinto de cero.")
    )
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: result)

    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")
    assert "advertencias" in window.status.cget("text").lower()


def test_parse_error_result_is_shown(window: tk.Tk, monkeypatch) -> None:
    result = _fake_result(
        error="No se pudo interpretar la ecuación.",
        general=None,
        particular=None,
        verification=None,
        particular_verification=None,
        numeric=None,
        singular_solutions=[],
        classifications=[],
        steps=[],
        warnings=[],
    )
    monkeypatch.setattr(desktop, "solve", lambda *args, **kwargs: result)

    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")
    assert "sin solución" in window.status.cget("text").lower()
    assert "No se pudo interpretar" in window.summary.get("1.0", "end")


def test_timeout_is_reported(window: tk.Tk, monkeypatch) -> None:
    def fake_solve(*args, **kwargs):
        raise desktop.TimeoutError("tiempo agotado")

    preguntas: list[str] = []
    monkeypatch.setattr(desktop, "solve", fake_solve)
    monkeypatch.setattr(
        window,
        "_confirmar_continuacion",
        lambda mensaje: preguntas.append(mensaje) or False,
    )

    window._start()
    assert _wait_until(window, lambda: window.status.cget("text") != "Calculando…")
    assert window.status.cget("text") == "Error"
    assert "TimeoutError" in window.summary.get("1.0", "end")
    assert str(window.solve_button.cget("state")) == "normal"
    assert preguntas and "No se puede graficar: TimeoutError:" in preguntas[0]


def test_timeout_can_continue_with_longer_deadline(
    window: tk.Tk, monkeypatch
) -> None:
    plazos: list[float] = []

    def fake_solve(*args, **kwargs):
        plazos.append(kwargs["timeout"])
        if len(plazos) == 1:
            raise desktop.TimeoutError(
                "El cálculo excedió el tiempo límite de 30 s. "
                "Se recomienda simplificar la ecuación o usar el respaldo numérico."
            )
        return _fake_result()

    monkeypatch.setattr(desktop, "solve", fake_solve)
    monkeypatch.setattr(window, "_confirmar_continuacion", lambda mensaje: True)

    window._start()
    assert _wait_until(window, lambda: len(plazos) == 2)
    assert _wait_until(
        window,
        lambda: window.status.cget("text") != "Calculando…"
        and window.status.cget("text") != "Error",
    )
    assert plazos == [30.0, 90.0]
    assert window.status.cget("text").startswith("Solución verificada")
    assert str(window.solve_button.cget("state")) == "normal"


def test_timeout_dialog_labels_and_choices(window: tk.Tk, monkeypatch) -> None:
    ttk = pytest.importorskip("tkinter.ttk")
    boton_a_pulsar = "Continuar cálculo"

    def fake_wait(dialog) -> None:
        botones: dict[str, object] = {}

        def walk(widget) -> None:
            for child in widget.winfo_children():
                if isinstance(child, ttk.Button):
                    botones[str(child.cget("text"))] = child
                walk(child)

        walk(dialog)
        assert set(botones) == {"Continuar cálculo", "Cancelar"}
        botones[boton_a_pulsar].invoke()

    monkeypatch.setattr(window, "wait_window", fake_wait)
    assert window._confirmar_continuacion("mensaje de prueba") is True

    boton_a_pulsar = "Cancelar"
    assert window._confirmar_continuacion("mensaje de prueba") is False


def test_output_card_has_general_scroll(window: tk.Tk) -> None:
    window.update_idletasks()
    window.update()

    scroll = window.output_scroll
    sections = scroll.content.winfo_children()
    assert len(sections) == 5

    region = str(scroll.canvas.cget("scrollregion")).split()
    assert len(region) == 4
    assert float(region[3]) > float(region[1])

    scroll.reset()
    assert scroll.canvas.yview()[0] == 0.0


def test_manual_window_opens_and_is_reused(window: tk.Tk) -> None:
    window._show_manual()
    window.update_idletasks()
    window.update()

    manual = window._manual_window
    assert manual.winfo_exists()
    assert "Manual" in manual.title()

    texts: list[tk.Text] = []

    def walk(widget: tk.Misc) -> None:
        for child in widget.winfo_children():
            if isinstance(child, tk.Text):
                texts.append(child)
            walk(child)

    walk(manual)
    assert texts
    content = texts[0].get("1.0", "end")
    assert "MANUAL DE INSTRUCCIONES" in content
    assert "LaTeX" in content

    window._show_manual()
    assert window._manual_window is manual


def test_real_solve_updates_interface(window: tk.Tk) -> None:
    window.equation.set("y' = x")
    window.x0.set("0")
    window.y0.set("1")
    window.x_min.set("0")
    window.x_max.set("1")
    window._start()
    assert _wait_until(
        window,
        lambda: window.status.cget("text") != "Calculando…",
        timeout=60.0,
    )
    assert "verificada" in window.status.cget("text").lower()
    assert "Verificación: Verificada (residuo 0)" in window.summary.get("1.0", "end")
    assert window.steps.get("1.0", "end").strip()
    assert window.plot_panel is not None
    assert window.plot_panel.axes.lines
