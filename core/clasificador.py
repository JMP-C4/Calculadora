"""Clasificación amigable de EDOs de primer orden.

Se apoya en el clasificador multi-método del motor :mod:`odecalc` y traduce
sus identificadores a etiquetas legibles.  Añade dos lecturas didácticas que
el motor no necesita para resolver: ``autónoma`` y ``logística``.
"""

from __future__ import annotations

from dataclasses import dataclass

import sympy as sp

from odecalc.classify import classify as _clasificar_motor
from odecalc.symbols import X, Y

from core.parser import parsear
from core.tipos import Ecuacion

_ETIQUETAS: dict[str, str] = {
    "separable": "Separable",
    "linear": "Lineal de primer orden",
    "exact": "Exacta",
    "homogeneous": "Homogénea",
    "bernoulli": "Bernoulli",
    "riccati": "Riccati",
    "clairaut": "Clairaut",
    "lagrange": "Lagrange",
    "reducible_homogeneous": "Reducible a homogénea",
    "substitution_linear_combo": "Sustitución u = ax + by + c",
    "integrating_factor_x": "Factor integrante μ(x)",
    "integrating_factor_y": "Factor integrante μ(y)",
    "integrating_factor_xy": "Factor integrante μ(xy)",
    "integrating_factor_x_plus_y": "Factor integrante μ(x+y)",
    "integrating_factor_x2_plus_y2": "Factor integrante μ(x²+y²)",
    "dsolve": "Respaldo SymPy (dsolve)",
    "numeric": "Integración numérica",
}

_DESCRIPCIONES: dict[str, str] = {
    "separable": "Puede escribirse como g(x)·h(y) e integrarse por separación.",
    "linear": "Es lineal en y: y' + P(x)y = Q(x).",
    "exact": "Existe una función potencial F(x,y) con F_x = M y F_y = N.",
    "homogeneous": "f(x,y) depende sólo del cociente y/x.",
    "bernoulli": "Tiene la forma y' + P(x)y = Q(x)yⁿ.",
    "riccati": "Tiene la forma y' = a(x) + b(x)y + c(x)y².",
    "clairaut": "Se escribe como y = x·y' + ψ(y').",
    "lagrange": "Se escribe como y = x·φ(y') + ψ(y').",
}


@dataclass
class TipoDetectado:
    """Un tipo o método aplicable, con la evidencia que lo justifica."""

    id: str
    etiqueta: str
    evidencia: str
    prioridad: int = 100

    @property
    def descripcion(self) -> str:
        return _DESCRIPCIONES.get(self.id, self.evidencia)


def etiqueta_metodo(metodo: str | None) -> str:
    """Traduce un identificador interno a una etiqueta en español."""

    if not metodo:
        return "Sin clasificar"
    return _ETIQUETAS.get(metodo, metodo.replace("_", " ").capitalize())


def _es_logistica(rhs: sp.Expr) -> bool:
    """Detecta ``r·y·(1 - y/K)`` sin necesidad de conocer K."""

    if rhs.has(X) or not rhs.has(Y):
        return False
    try:
        polinomio = sp.Poly(sp.expand(rhs), Y)
    except Exception:
        return False
    if polinomio.degree() != 2:
        return False
    a2 = sp.simplify(polinomio.coeff_monomial(Y**2))
    a1 = sp.simplify(polinomio.coeff_monomial(Y))
    a0 = sp.simplify(polinomio.coeff_monomial(1))
    return bool(a2 != 0 and a1 != 0 and a0 == 0)


def detectados_desde_matches(
    matches: list[object],
    ecuacion: Ecuacion,
) -> list[TipoDetectado]:
    """Construye y ordena etiquetas de clasificación a partir de ``Match``."""

    detectados: list[TipoDetectado] = [
        TipoDetectado(
            id=match.method,
            etiqueta=etiqueta_metodo(match.method),
            evidencia=match.evidence,
            prioridad=match.priority,
        )
        for match in matches
    ]

    if ecuacion.es_autonoma:
        detectados.append(
            TipoDetectado(
                id="autonoma",
                etiqueta="Autónoma",
                evidencia="El lado derecho no depende de x: y' = f(y).",
                prioridad=90,
            )
        )
    if _es_logistica(ecuacion.rhs):
        detectados.append(
            TipoDetectado(
                id="logistica",
                etiqueta="Logística",
                evidencia=(
                    "Es autónoma y cuadrática en y, con la forma "
                    "y' = r·y·(1 - y/K)."
                ),
                prioridad=8,
            )
        )

    # Sin duplicados y con la prioridad como orden estable.
    unicos: dict[str, TipoDetectado] = {}
    for tipo in detectados:
        unicos.setdefault(tipo.id, tipo)
    return sorted(unicos.values(), key=lambda item: (item.prioridad, item.id))


def clasificar(ecuacion: str | Ecuacion) -> list[TipoDetectado]:
    """Devuelve todos los tipos aplicables, ordenados por prioridad."""

    if isinstance(ecuacion, str):
        ecuacion = parsear(ecuacion)

    return detectados_desde_matches(_clasificar_motor(ecuacion.parsed), ecuacion)


def tipo_principal(ecuacion: str | Ecuacion) -> str:
    """Etiqueta del primer tipo aplicable, útil para encabezados."""

    tipos = clasificar(ecuacion)
    if not tipos:
        return "Sin clasificar"
    preferido = next(
        (tipo for tipo in tipos if tipo.id not in {"autonoma", "logistica"}),
        tipos[0],
    )
    return preferido.etiqueta


__all__ = [
    "TipoDetectado",
    "clasificar",
    "detectados_desde_matches",
    "etiqueta_metodo",
    "tipo_principal",
]
