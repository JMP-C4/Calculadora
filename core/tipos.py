"""Contratos de datos y excepciones de EDO-Lab.

La capa ``core`` es independiente de cualquier interfaz.  Las interfaces
(Streamlit, Tk o web) sólo consumen estos objetos; nunca contienen lógica
matemática propia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class EstadoVerificacion(str, Enum):
    """Nivel de confianza de una solución presentada."""

    SIMBOLICA = "verificada_simbolica"
    NUMERICA = "verificada_numerica"
    NO_VERIFICADA = "no_verificada"


@dataclass
class Certificado:
    """Certificado de verificación que acompaña a toda solución."""

    estado: EstadoVerificacion
    residuo_max: float | None
    dominio_valido: str
    notas: list[str] = field(default_factory=list)
    metodo: str = ""

    @property
    def etiqueta(self) -> str:
        return {
            EstadoVerificacion.SIMBOLICA: "Verificada simbólicamente",
            EstadoVerificacion.NUMERICA: "Verificada numéricamente",
            EstadoVerificacion.NO_VERIFICADA: "No verificada",
        }[self.estado]

    @property
    def icono(self) -> str:
        return {
            EstadoVerificacion.SIMBOLICA: "✅",
            EstadoVerificacion.NUMERICA: "⚠️",
            EstadoVerificacion.NO_VERIFICADA: "❌",
        }[self.estado]

    @property
    def es_confiable(self) -> bool:
        return self.estado in (
            EstadoVerificacion.SIMBOLICA,
            EstadoVerificacion.NUMERICA,
        )


@dataclass
class Paso:
    """Un paso explicativo con su justificación y su fórmula LaTeX."""

    titulo: str
    explicacion: str
    latex: str


@dataclass
class ResultadoNumerico:
    """Resultado de un integrador numérico de un paso."""

    x: np.ndarray = field(default_factory=lambda: np.asarray([], dtype=float))
    y: np.ndarray = field(default_factory=lambda: np.asarray([], dtype=float))
    metodo: str = ""
    exito: bool = False
    mensaje: str = ""
    f_evaluaciones: int = 0
    h: float | None = None
    error_max: float | None = None
    rigido: bool = False
    explosion: bool = False

    @property
    def puntos(self) -> int:
        return int(self.x.size)

    @property
    def intervalo(self) -> tuple[float, float] | None:
        if self.x.size < 2:
            return None
        return float(self.x[0]), float(self.x[-1])


@dataclass
class InfoExistencia:
    """Diagnóstico de existencia, unicidad, singularidades y explosión."""

    f_continua: bool | None = None
    dfdy_continua: bool | None = None
    lipschitz: bool | None = None
    puntos_singularidad: list[str] = field(default_factory=list)
    no_unicidad: bool = False
    motivo_no_unicidad: str | None = None
    explota: bool = False
    tiempo_explosion: float | None = None
    direccion_explosion: str | None = None
    notas: list[str] = field(default_factory=list)

    @property
    def resumen(self) -> str:
        if self.no_unicidad:
            return "La solución puede no ser única en el punto inicial."
        if self.explota:
            tiempo = (
                f" en x ≈ {self.tiempo_explosion:.6g}"
                if self.tiempo_explosion is not None
                else ""
            )
            return f"Posible explosión en tiempo finito{tiempo}."
        if self.lipschitz:
            return "Se cumplen las condiciones de Picard-Lindelöf (solución local única)."
        return "No se pudo certificar existencia y unicidad con los datos dados."


@dataclass
class Equilibrio:
    """Punto de equilibrio de una EDO autónoma y su estabilidad."""

    valor: float
    estabilidad: str
    f_prima: float | None = None
    notas: list[str] = field(default_factory=list)

    @property
    def icono(self) -> str:
        if self.estabilidad.startswith("estable"):
            return "🟢"
        if self.estabilidad.startswith("inestable"):
            return "🔴"
        return "🟡"


@dataclass
class PuntoBifurcacion:
    """Equilibrio de una familia parametrizada ``y' = f(y; mu)``."""

    parametro: float
    equilibrio: float
    estabilidad: str


@dataclass
class FilaConvergencia:
    """Una fila del estudio error frente a paso."""

    metodo: str
    h: float
    error_max: float
    puntos: int


@dataclass
class ResultadoConvergencia:
    """Estudio completo de convergencia y órdenes empíricos."""

    filas: list[FilaConvergencia]
    ordenes: dict[str, float]
    referencia: str = "solución exacta"
    notas: list[str] = field(default_factory=list)


@dataclass
class BenchmarkItem:
    """Medición de rendimiento de un método numérico."""

    metodo: str
    tiempo_ms: float
    f_evaluaciones: int
    error_max: float | None
    pasos: int
    exito: bool
    notas: str = ""


@dataclass
class InfoRigidez:
    """Diagnóstico de rigidez de una EDO."""

    rigida: bool
    motivo: str
    metodo_recomendado: str = "RK45"
    jacobiano_max: float | None = None
    nfev_rk45: int | None = None


@dataclass
class ResultadoSolucion:
    """Resultado público de :func:`core.hibrido.resolver`.

    ``solucion`` conserva el objeto del motor (una ``Solution`` de
    :mod:`odecalc`) o un :class:`ResultadoNumerico` cuando no hubo forma
    cerrada.  Las cadenas LaTeX facilitan la presentación sin acoplar la UI al
    motor.
    """

    ecuacion_texto: str
    ecuacion_latex: str
    tipo: str
    tipos: list[str]
    camino: str
    solucion: Any
    solucion_latex: str = ""
    general_latex: str = ""
    particular_latex: str = ""
    certificado: Certificado | None = None
    advertencias: list[str] = field(default_factory=list)
    pasos: list[Paso] = field(default_factory=list)
    x0: float | None = None
    y0: float | None = None
    intervalo: tuple[float, float] | None = None
    numerico: ResultadoNumerico | None = None
    existencia: InfoExistencia | None = None
    resultado_motor: Any = field(default=None, repr=False, compare=False)

    @property
    def es_analitica(self) -> bool:
        return self.camino == "analitica"

    @property
    def tiene_certificado(self) -> bool:
        return self.certificado is not None

    @property
    def confiable(self) -> bool:
        return bool(self.certificado and self.certificado.es_confiable)


@dataclass
class Ecuacion:
    """Ecuación ya validada y lista para el motor."""

    texto: str
    latex: str
    rhs: Any
    parsed: Any
    tipos: list[str] = field(default_factory=list)
    es_autonoma: bool = False
    es_lineal: bool = False
    advertencias: list[str] = field(default_factory=list)
    parametros: tuple[str, ...] = ()


class EntradaInvalida(ValueError):
    """El texto de entrada no representa una EDO válida."""


class SolucionNoDisponible(RuntimeError):
    """No fue posible obtener una solución simbólica ni numérica."""


class TiempoAgotado(RuntimeError):
    """El cálculo excedió el tiempo máximo configurado."""


class DatosInvalidos(ValueError):
    """Los datos experimentales no tienen el formato mínimo requerido."""


class IADesactivada(RuntimeError):
    """La capa opcional de IA no está configurada."""


__all__ = [
    "EstadoVerificacion",
    "Certificado",
    "Paso",
    "ResultadoNumerico",
    "InfoExistencia",
    "Equilibrio",
    "PuntoBifurcacion",
    "FilaConvergencia",
    "ResultadoConvergencia",
    "BenchmarkItem",
    "InfoRigidez",
    "ResultadoSolucion",
    "Ecuacion",
    "EntradaInvalida",
    "SolucionNoDisponible",
    "TiempoAgotado",
    "DatosInvalidos",
    "IADesactivada",
]
