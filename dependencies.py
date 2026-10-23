"""Verificación de dependencias externas al iniciar la aplicación."""

from __future__ import annotations

import importlib.util

REQUIRED_MODULES: tuple[str, ...] = ("sympy", "scipy", "matplotlib", "numpy")


def missing_dependencies() -> list[str]:
    """Devuelve los módulos requeridos que no están instalados."""

    return [
        module
        for module in REQUIRED_MODULES
        if importlib.util.find_spec(module) is None
    ]


__all__ = ["REQUIRED_MODULES", "missing_dependencies"]
