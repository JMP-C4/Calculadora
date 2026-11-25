"""Iconografía vectorial en línea para la interfaz de EDO-Lab.

Los iconos son trazados SVG del estilo Lucide/Heroicons.  Se insertan como
HTML seguro (sin emoji, sin dependencias de fuentes de iconos externas).
"""

from __future__ import annotations

from html import escape

_TRAZOS: dict[str, str] = {
    "activity": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "alert": (
        '<path d="M10.3 3.8 2.5 17.2A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 '
        '1.7-2.8L13.7 3.8a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/>'
        '<path d="M12 17h.01"/>'
    ),
    "book": (
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2Z"/>'
    ),
    "calculator": (
        '<rect x="4" y="2" width="16" height="20" rx="2"/>'
        '<path d="M8 6h8M8 10h2m2 0h4M8 14h2m2 0h4M8 18h2m2 0h4"/>'
    ),
    "chart": (
        '<path d="M3 3v18h18"/>'
        '<path d="m7 15 4-5 3 3 5-7"/>'
    ),
    "check": '<path d="m5 13 4 4L19 7"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "compass": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="m15.2 8.8-2.1 4.3-4.3 2.1 2.1-4.3 4.3-2.1Z"/>'
    ),
    "download": (
        '<path d="M12 3v12m0 0 4-4m-4 4-4-4"/>'
        '<path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'
    ),
    "eye": '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "file": (
        '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/>'
        '<path d="M14 2v6h6"/>'
    ),
    "folder": (
        '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/>'
    ),
    "globe": (
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"/>'
    ),
    "history": (
        '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/>'
        '<path d="M3 3v5h5M12 7v5l4 2"/>'
    ),
    "infinity": '<path d="M6.5 8a4 4 0 1 0 0 8c2.2 0 3.3-1.6 5.5-4s3.3-4 5.5-4a4 4 0 1 1 0 8c-2.2 0-3.3-1.6-5.5-4S8.7 8 6.5 8Z"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 8h.01"/>',
    "keyboard": (
        '<rect x="2" y="5" width="20" height="14" rx="2"/>'
        '<path d="M6 9h.01M10 9h.01M14 9h.01M18 9h.01M6 13h.01M10 13h.01M14 13h.01M18 13h.01M8 16h8"/>'
    ),
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
    "map": '<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z"/><path d="M9 3v15M15 6v15"/>',
    "moon": '<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z"/>',
    "pin": '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
    "play": '<path d="m7 4 13 8-13 8Z"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7L20 14"/><path d="M20 5v6h-6"/>',
    "scale": '<path d="M12 3v18M7 21h10M4 7h16l-3 6H7Z"/><path d="M7 7 4 13m13-6 3 6"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "settings": (
        '<path d="M4 6h16M4 12h16M4 18h16"/>'
        '<circle cx="9" cy="6" r="2" fill="currentColor" stroke="none"/>'
        '<circle cx="15" cy="12" r="2" fill="currentColor" stroke="none"/>'
        '<circle cx="8" cy="18" r="2" fill="currentColor" stroke="none"/>'
    ),
    "shield": '<path d="M12 2 4 5v6c0 5 3.4 9.2 8 11 4.6-1.8 8-6 8-11V5Z"/><path d="m9 12 2 2 4-4"/>',
    "sliders": '<path d="M4 6h10m4 0h2M4 12h4m4 0h8M4 18h12m4 0h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "spark": '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8Z"/><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8Z"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
}


def svg(nombre: str = "", *, size: int = 16, etiqueta: str = "") -> str:
    """Devuelve un SVG accesible; un nombre desconocido cae a un marcador."""

    trazo = _TRAZOS.get(nombre, _TRAZOS["info"])
    accesible = (
        f' role="img" aria-label="{escape(etiqueta, quote=True)}"'
        if etiqueta
        else ' aria-hidden="true"'
    )
    return (
        f'<svg class="edo-icono" width="{int(size)}" height="{int(size)}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"'
        f'{accesible}>{trazo}</svg>'
    )


__all__ = ["svg"]
