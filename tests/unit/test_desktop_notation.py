"""Pruebas headless de notación estándar y renderizado en la app de escritorio."""

from __future__ import annotations

import re
import types

import pytest

pytest.importorskip("matplotlib")

from apps.desktop import app as desktop  # noqa: E402
from core.notacion import NATURAL, adaptar_latex_mathtext  # noqa: E402
from odecalc.api import solve  # noqa: E402
from odecalc.methods import dsolve_fallback  # noqa: E402

PNG_HEADER = b"\x89PNG\r\n\x1a\n"


class _DummyVar:
    def __init__(self, value: str = "") -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class _DummyText:
    """Simula un ``tk.Text`` recogiendo prosa y fórmulas embebidas."""

    def __init__(self) -> None:
        self.state = "disabled"
        self.items: list[tuple[str, object]] = []

    def configure(self, **kwargs) -> None:
        if "state" in kwargs:
            self.state = str(kwargs["state"])

    def cget(self, key: str) -> str:
        return "#f6f9fb" if key == "bg" else ""

    def delete(self, *_args) -> None:
        self.items.clear()

    def insert(self, _index: str, text: str) -> None:
        self.items.append(("text", text))

    def window_create(self, _index: str, *, window: object) -> None:
        self.items.append(("formula", window))

    def yview_moveto(self, _pos: float) -> None:
        return None

    def plain_text(self) -> str:
        return "".join(
            value for kind, value in self.items if kind == "text" and isinstance(value, str)
        )


def _make_headless_desktop_app():
    app = object.__new__(desktop.ODEApp)
    app._notacion_salida = _DummyVar("Algebraica")
    app._ultima_solicitud = None
    app._busy = False
    app._reintentos_por_solicitud = 0
    app._math_preview = None
    app._input_preview = None
    app._math_images = []
    app._rendered_pngs = []
    app._rendered_formulas = []
    app.summary = _DummyText()
    app.methods = _DummyText()
    app.steps = _DummyText()
    app.warnings = _DummyText()
    app.explanation = _DummyText()

    def fake_insertar(widget: _DummyText, latex: str, notacion: str = NATURAL) -> None:
        png = desktop._renderizar_png_latex(latex)
        assert png[:8] == PNG_HEADER
        app._rendered_pngs.append(png)
        app._rendered_formulas.append(adaptar_latex_mathtext(latex))
        widget.window_create("end", window=latex)

    app._insertar_formula = fake_insertar  # type: ignore[method-assign]
    return app


@pytest.mark.parametrize(
    ("equation", "ic", "forced_method"),
    [
        ("dy/dx = x*y", (0.0, 2.0), "separable"),
        ("y' - (1/x)*y = sin(x)/x", None, "linear"),
        ("(2*x*y + 1)*dx + (x**2 + cos(y))*dy = 0", None, "exact"),
        ("(3*x*y + y**2)*dx + (x**2 + x*y)*dy = 0", None, "integrating_factor_x"),
        ("y' + y/x = x*y**3", (1.0, 1.0), "bernoulli"),
        ("dy/dx = (x**2 + y**2)/(x*y)", None, "homogeneous"),
        ("dy/dx = (x + y - 1)/(x - y + 3)", None, "reducible_homogeneous"),
        ("dy/dx = sin(x + y)", None, "substitution_linear_combo"),
        ("y = x*y' + (y')**2", None, "clairaut"),
        ("dy/dx = Abs(x)/y", None, "exact"),
    ],
)
def test_desktop_renders_all_processes_in_standard_notation(
    equation: str,
    ic: tuple[float, float] | None,
    forced_method: str,
) -> None:
    result = solve(
        equation,
        x0=ic[0] if ic else None,
        y0=ic[1] if ic else None,
        method=forced_method,
        compute_numeric=False,
        timeout=30.0,
    )
    app = _make_headless_desktop_app()
    if ic is not None:
        app._ultima_solicitud = (equation, {"x0": ic[0], "y0": ic[1], "x_min": -5.0, "x_max": 5.0})

    for mode in ("Algebraica", NATURAL):
        app._rendered_pngs.clear()
        app._rendered_formulas.clear()
        app._notacion_salida.set(mode)
        app._render_resultado_completo(result)

        assert app._rendered_pngs, f"Sin fórmulas PNG para {equation} en modo {mode}"
        combined_formulas = "\n".join(app._rendered_formulas)
        assert "mathtt" not in combined_formulas
        assert "+ -" not in combined_formulas
        assert "- -" not in combined_formulas
        assert "Dy" not in combined_formulas
        assert not re.search(r"(?<!\\)\bfrac\{", combined_formulas)
        assert not re.search(r"(?<!\\)begin\{cases\}", combined_formulas)

        assert "Ecuación:" in app.summary.plain_text()
        assert "1." in app.steps.plain_text()


def test_desktop_renders_numeric_fallback_in_standard_notation(monkeypatch) -> None:
    monkeypatch.setattr(
        dsolve_fallback,
        "solve",
        lambda _parsed: (_ for _ in ()).throw(ValueError("sin solución elemental")),
    )
    result = solve("y' = x*y + sin(x)", x0=0.0, y0=1.0, compute_numeric=True, timeout=2.0)
    app = _make_headless_desktop_app()
    app._ultima_solicitud = ("y' = x*y + sin(x)", {"x0": 0.0, "y0": 1.0, "x_min": -5.0, "x_max": 5.0})
    app._notacion_salida.set("Algebraica")
    app._render_resultado_completo(result)

    combined = "\n".join(app._rendered_formulas)
    assert app._rendered_pngs
    assert "mathtt" not in combined
    assert r"\frac{dy}{dx}" in combined
    assert "Respaldo numérico" in app.summary.plain_text()


def test_desktop_start_validates_busy_nan_and_bounds(monkeypatch) -> None:
    errors: list[tuple[str, str]] = []
    statuses: list[str] = []
    launches: list[float] = []

    app = object.__new__(desktop.ODEApp)
    app._busy = True
    app.equation = _DummyVar("y' = x + y")
    app.x0 = _DummyVar("0")
    app.y0 = _DummyVar("1")
    app.x_min = _DummyVar("-5")
    app.x_max = _DummyVar("5")
    app._set_status = lambda msg, _lvl="info": statuses.append(msg)  # type: ignore[method-assign]
    app._launch_solve = lambda t: launches.append(t)  # type: ignore[method-assign]
    monkeypatch.setattr(desktop.messagebox, "showerror", lambda title, msg, **_kw: errors.append((title, msg)))

    app._start()
    assert not launches
    assert statuses and "en curso" in statuses[0]

    app._busy = False
    app.x0.set("nan")
    app._start()
    assert errors and errors[-1][0] == "Datos inválidos"

    app.x0.set("0")
    app.x_min.set("5")
    app.x_max.set("5")
    app._start()
    assert errors[-1][0] == "Intervalo inválido"


def test_desktop_open_readme_handles_missing_file(tmp_path, monkeypatch) -> None:
    infos: list[tuple[str, str]] = []
    fake_app = object.__new__(desktop.ODEApp)
    monkeypatch.setattr(desktop, "__file__", str(tmp_path / "pkg" / "apps" / "desktop" / "app.py"))
    monkeypatch.setattr(desktop.messagebox, "showinfo", lambda title, msg, **_kw: infos.append((title, msg)))

    fake_app._open_readme()
    assert infos and "Manual" in infos[0][1]


def test_desktop_live_preview_formats_input_and_pvi() -> None:
    captured: list[tuple[str, object]] = []

    class _DummyPreview:
        def show_placeholder(self) -> None:
            captured.append(("__placeholder__", None))

        def render(self, latex: str, cond: object = None) -> None:
            captured.append((latex, cond))

    app = object.__new__(desktop.ODEApp)
    app._preview_after_id = None
    app._input_preview = _DummyPreview()
    app.equation = _DummyVar("dy/dx = x**2/y")
    app.x0 = _DummyVar("0")
    app.y0 = _DummyVar("1")

    app._actualizar_preview_entrada()
    assert captured[-1][0] == r"\frac{dy}{dx} = \frac{x^{2}}{y}"
    assert getattr(captured[-1][1], "x0", None) == 0.0
    assert getattr(captured[-1][1], "y0", None) == 1.0

    # Entrada parcial en edición no debe lanzar excepción.
    app.equation.set("y' = x/")
    app._actualizar_preview_entrada()
    assert captured[-1][0]

    app.equation.set("   ")
    app._actualizar_preview_entrada()
    assert captured[-1][0] == "__placeholder__"


def test_desktop_plot_panel_uses_bounds_and_sanitizes_surface_inf(monkeypatch) -> None:
    plot_panel = pytest.importorskip("apps.desktop.plot_panel")
    import numpy as np
    import sympy as sp
    from odecalc.models import SolveResult
    from odecalc.symbols import X, Y

    recorded_bounds: list[tuple[float, float]] = []

    def fake_solution_curve(_res, *, x_min=-5.0, x_max=5.0):
        recorded_bounds.append((x_min, x_max))
        return {"x": np.array([x_min, x_max]), "y": np.array([1.0, 2.0])}

    monkeypatch.setattr(plot_panel, "solution_curve", fake_solution_curve)

    panel = object.__new__(plot_panel.PlotPanel)
    panel._bounds = (-2.0, 7.0)
    panel.figure = types.SimpleNamespace(clear=lambda: None, tight_layout=lambda: None, colorbar=lambda *a, **kw: None)
    plotted_z: list[np.ndarray] = []

    class _DummyAxes:
        def grid(self, *_a, **_kw) -> None:
            return None

        def set_xlabel(self, *_a) -> None:
            return None

        def set_ylabel(self, *_a) -> None:
            return None

        def set_zlabel(self, *_a) -> None:
            return None

        def set_title(self, *_a) -> None:
            return None

        def plot(self, *_a, **_kw) -> None:
            return None

        def legend(self, *_a, **_kw) -> None:
            return None

        def plot_surface(self, _gx, _gy, gz, **_kw):
            plotted_z.append(gz)
            return None

    panel.axes = _DummyAxes()
    panel.notice = types.SimpleNamespace(configure=lambda **_kw: None)
    panel.figure.add_subplot = lambda *_a, **_kw: panel.axes
    panel._plot_singular = lambda _res: False

    dummy_res = SolveResult(input_text="y' = 1/(x*y)")
    panel._draw_solution(dummy_res)
    assert recorded_bounds == [(-2.0, 7.0)]

    panel._bounds = (0.0, 2.0)
    panel._draw_surface(dummy_res)
    assert plotted_z
    assert not np.any(np.isinf(plotted_z[0]))


def test_desktop_kpis_use_human_labels_and_piecewise_renders() -> None:
    assert desktop._etiqueta_kpi_metodo("substitution_linear_combo") == "Sust. u = ax+by"
    assert desktop._etiqueta_kpi_metodo("integrating_factor_xy") == "Factor μ(xy)"
    assert desktop._etiqueta_kpi_metodo(None) == "—"

    app = _make_headless_desktop_app()
    app._notacion_salida.set(NATURAL)
    app._started_at = None
    kpis: dict[str, str] = {}
    app.kpi_method = types.SimpleNamespace(configure=lambda **kw: kpis.__setitem__("method", kw["text"]))
    app.kpi_verification = types.SimpleNamespace(configure=lambda **kw: kpis.__setitem__("ver", kw["text"]))
    app.kpi_time = types.SimpleNamespace(configure=lambda **kw: kpis.__setitem__("time", kw["text"]))

    from odecalc.api import solve

    res = solve("dy/dx = Abs(x)/y", compute_numeric=False)
    app._render_resultado_completo(res)
    app._update_kpis(res)
    assert kpis["method"] in {"Exacta", "Separable"}
    assert kpis["ver"] == "residuo 0"
    assert "Verificada (residuo 0)" in app.summary.plain_text()
    assert app._rendered_pngs
    assert app.steps.plain_text()

