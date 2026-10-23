"""Tests del verificador de dependencias al arrancar."""

from __future__ import annotations

import dependencies


def test_all_required_dependencies_are_installed():
    assert dependencies.missing_dependencies() == []


def test_missing_dependency_is_detected(monkeypatch):
    real_find_spec = dependencies.importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name == "scipy":
            return None
        return real_find_spec(name, *args, **kwargs)

    monkeypatch.setattr(dependencies.importlib.util, "find_spec", fake_find_spec)

    assert dependencies.missing_dependencies() == ["scipy"]
