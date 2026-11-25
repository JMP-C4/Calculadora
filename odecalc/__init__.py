"""Motor puro de ecuaciones diferenciales ordinarias de primer orden.

El paquete no importa tkinter, Matplotlib ni frameworks web.  La interfaz
pública principal es :func:`odecalc.api.solve`.
"""

from __future__ import annotations

__version__ = "2.0.0"

__all__ = ["solve", "parse_ode", "result_to_dict", "__version__"]


def __getattr__(name: str):
    if name == "solve":
        from odecalc.api import solve

        return solve
    if name == "parse_ode":
        from odecalc.parsing import parse_ode

        return parse_ode
    if name == "result_to_dict":
        from odecalc.serialization import result_to_dict

        return result_to_dict
    raise AttributeError(name)
