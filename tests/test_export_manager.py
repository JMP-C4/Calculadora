"""Tests unitarios de la exportación de gráficas."""

from __future__ import annotations

from matplotlib.figure import Figure

from ui import export_manager


def _figure() -> Figure:
    figure = Figure(figsize=(3.0, 2.0))
    axes = figure.add_subplot(111)
    axes.plot([0.0, 1.0], [1.0, 0.0])
    return figure


def test_export_png(tmp_path, monkeypatch):
    target = tmp_path / "grafica.png"
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )

    path, error = export_manager.export_figure(_figure())

    assert error is None
    assert path == str(target)
    assert target.exists()
    assert target.stat().st_size > 0


def test_export_jpeg(tmp_path, monkeypatch):
    target = tmp_path / "grafica.jpg"
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )

    path, error = export_manager.export_figure(_figure())

    assert error is None
    assert path == str(target)
    assert target.read_bytes()[:2] == b"\xff\xd8"


def test_export_pdf(tmp_path, monkeypatch):
    target = tmp_path / "grafica.pdf"
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )

    path, error = export_manager.export_figure(_figure())

    assert error is None
    assert path == str(target)
    assert target.read_bytes()[:4] == b"%PDF"


def test_export_cancelled(monkeypatch):
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: "",
    )

    assert export_manager.export_figure(_figure()) == (None, None)


def test_export_rejects_unsupported_format(tmp_path, monkeypatch):
    target = tmp_path / "grafica.svg"
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )

    path, error = export_manager.export_figure(_figure())

    assert path is None
    assert "no soportado" in (error or "")
    assert not target.exists()


def test_export_without_pillow_reports_install_hint(tmp_path, monkeypatch):
    target = tmp_path / "grafica.png"
    monkeypatch.setattr(
        export_manager.filedialog,
        "asksaveasfilename",
        lambda **kwargs: str(target),
    )
    monkeypatch.setattr(export_manager, "_pillow_available", lambda: False)

    path, error = export_manager.export_figure(_figure())

    assert path is None
    assert "Pillow" in (error or "")
    assert not target.exists()
