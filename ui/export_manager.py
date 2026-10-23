"""Exportación de gráficas a PNG, JPEG o PDF."""

from __future__ import annotations

import importlib.util
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure

_SUPPORTED_RASTERS = {".png", ".jpg", ".jpeg"}


def _pillow_available() -> bool:
    return importlib.util.find_spec("PIL") is not None


def export_figure(
    fig: Figure,
    parent: tk.Misc | None = None,
) -> tuple[str | None, str | None]:
    """Abre un diálogo de guardado y exporta ``fig`` a 300 DPI.

    Returns
    -------
    tuple[str | None, str | None]
        Ruta guardada (o ``None`` si se cancela) y mensaje de error opcional.
    """

    selected = filedialog.asksaveasfilename(
        parent=parent,
        title="Exportar gráfica",
        defaultextension=".png",
        filetypes=[
            ("Imagen PNG", "*.png"),
            ("Imagen JPEG", "*.jpg *.jpeg"),
            ("Documento PDF", "*.pdf"),
        ],
    )
    if not selected:
        return None, None

    path = Path(selected)
    suffix = path.suffix.lower()
    if not suffix:
        path = path.with_suffix(".png")
        suffix = ".png"

    if suffix == ".pdf":
        try:
            with PdfPages(path) as pdf:
                pdf.savefig(fig, dpi=300)
        except Exception as exc:
            return None, f"No se pudo exportar a PDF: {exc}"
        return str(path), None

    if suffix not in _SUPPORTED_RASTERS:
        return None, "Formato no soportado. Elige PNG, JPEG o PDF."

    if not _pillow_available():
        return None, (
            "Pillow no está instalado. Instálalo con: pip install 'Pillow>=10.0'"
        )

    try:
        fig.savefig(
            path,
            dpi=300,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
    except Exception as exc:
        return None, f"No se pudo exportar la gráfica: {exc}"
    return str(path), None


__all__ = ["export_figure"]
