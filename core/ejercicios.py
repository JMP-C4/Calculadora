"""Generador determinista de ejercicios con solución verificada por el motor."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.hibrido import resolver
from core.tipos import Certificado, SolucionNoDisponible

TIPOS = ("separable", "lineal", "exacta", "bernoulli", "logistica")

_PISTAS = {
    "separable": "Separa las variables y recuerda la constante de integración.",
    "lineal": "Escribe la forma estándar y calcula el factor integrante μ(x).",
    "exacta": "Comprueba que ∂M/∂y = ∂N/∂x y busca la función potencial F(x,y).",
    "bernoulli": "Usa la sustitución v = y^(1-n) para convertirla en lineal.",
    "logistica": "Es autónoma: busca los equilibrios y estudia el signo de f(y).",
}

_BANCO_FALLBACK: dict[str, list[dict[str, Any]]] = {
    "separable": [
        {"ecuacion": "y' = x*y", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "y' = 2*x*y", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "y' = y*cos(x)", "x0": 0.0, "y0": 1.0},
    ],
    "lineal": [
        {"ecuacion": "y' + y = x", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "y' + 2*y = 4", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "y' + y = exp(-x)", "x0": 0.0, "y0": 1.0},
    ],
    "exacta": [
        {"ecuacion": "2*x*y + (x^2+1)*y' = 0", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "2*x*y + (x^2+2)*y' = 0", "x0": 0.0, "y0": 2.0},
    ],
    "bernoulli": [
        {"ecuacion": "y' + y = y^2", "x0": 0.0, "y0": 0.5},
        {"ecuacion": "y' + 2*y = y^3", "x0": 0.0, "y0": 0.5},
    ],
    "logistica": [
        {"ecuacion": "y' = y*(1-y/10)", "x0": 0.0, "y0": 1.0},
        {"ecuacion": "y' = 0.5*y*(1-y/100)", "x0": 0.0, "y0": 5.0},
    ],
}


@dataclass
class Ejercicio:
    """Ejercicio propuesto con su solución ya certificada."""

    id: str
    tipo: str
    dificultad: int
    enunciado: str
    ecuacion: str
    solucion_latex: str
    pista: str
    x0: float
    y0: float
    certificado: Certificado | None = None
    advertencias: list[str] = field(default_factory=list)

    @property
    def resumen(self) -> str:
        return f"{self.tipo.capitalize()} · dificultad {self.dificultad}/5"


def _plantilla(tipo: str, dificultad: int, rng: random.Random) -> dict[str, Any]:
    dificultad = max(1, min(5, int(dificultad)))
    if tipo == "separable":
        a = rng.choice([1, 2, 3]) * dificultad
        p = rng.choice([1, 1, 2, 3])
        return {
            "ecuacion": f"y' = {a}*x^{p}*y",
            "x0": 0.0,
            "y0": 1.0,
        }
    if tipo == "lineal":
        a = rng.choice([1, 2, 3])
        b = rng.choice([1, 2])
        c = rng.choice([0, 1, 2]) * (dificultad - 1)
        if dificultad >= 4:
            return {
                "ecuacion": f"y' + {a}*y = {b}*exp(-x) + {c}",
                "x0": 0.0,
                "y0": 1.0,
            }
        return {
            "ecuacion": f"y' + {a}*y = {b}*x + {c}",
            "x0": 0.0,
            "y0": 1.0,
        }
    if tipo == "exacta":
        b = rng.choice([1, 2, 3])
        return {
            "ecuacion": f"2*{b}*x*y + ({b}*x^2 + 1)*y' = 0",
            "x0": 0.0,
            "y0": float(rng.choice([1, 2])),
        }
    if tipo == "bernoulli":
        n = rng.choice([2, 2, 3])
        a = rng.choice([1, 2])
        return {
            "ecuacion": f"y' + {a}*y = y^{n}",
            "x0": 0.0,
            "y0": 0.5,
        }
    if tipo == "logistica":
        r = rng.choice([0.5, 1, 2])
        K = rng.choice([10, 20, 50, 100])
        return {
            "ecuacion": f"y' = {r}*y*(1-y/{K})",
            "x0": 0.0,
            "y0": float(rng.choice([1, 5])),
        }
    raise ValueError(f"Tipo de ejercicio desconocido: {tipo}")


def _construir(tipo: str, dificultad: int, plantilla: dict[str, Any], semilla: int) -> Ejercicio:
    x0 = float(plantilla["x0"])
    y0 = float(plantilla["y0"])
    ecuacion = str(plantilla["ecuacion"])
    resultado = resolver(
        ecuacion,
        x0=x0,
        y0=y0,
        timeout=8.0,
        incluir_numerico=False,
    )
    if not resultado.confiable or not resultado.solucion_latex:
        raise SolucionNoDisponible("La solución generada no superó la verificación.")
    enunciado = (
        f"Resuelve la ecuación diferencial {ecuacion} con la condición "
        f"inicial y({x0:g}) = {y0:g}."
    )
    return Ejercicio(
        id=f"{tipo}-{dificultad}-{semilla}",
        tipo=tipo,
        dificultad=max(1, min(5, dificultad)),
        enunciado=enunciado,
        ecuacion=ecuacion,
        solucion_latex=resultado.solucion_latex,
        pista=_PISTAS[tipo],
        x0=x0,
        y0=y0,
        certificado=resultado.certificado,
        advertencias=resultado.advertencias,
    )


def generar_ejercicio(
    tipo: str = "separable",
    dificultad: int = 1,
    *,
    semilla: int = 42,
) -> Ejercicio:
    """Genera un ejercicio determinista y lo verifica antes de devolverlo."""

    tipo = tipo.lower().strip()
    if tipo not in TIPOS:
        raise ValueError(
            f"Tipo desconocido: {tipo}. Usa uno de: {', '.join(TIPOS)}."
        )
    rng = random.Random((int(semilla) * 1009) + (int(dificultad) * 97) + TIPOS.index(tipo))
    plantilla = _plantilla(tipo, dificultad, rng)
    try:
        return _construir(tipo, dificultad, plantilla, int(semilla))
    except Exception:
        # Respaldo curado: también se verifica antes de mostrarlo.
        for alternativa in _BANCO_FALLBACK[tipo]:
            try:
                ejercicio = _construir(tipo, dificultad, alternativa, int(semilla))
                ejercicio.advertencias.append(
                    "Se usó un ejercicio de respaldo porque la variante aleatoria "
                    "no pudo certificarse."
                )
                return ejercicio
            except Exception:
                continue
        raise SolucionNoDisponible(
            "No se pudo generar un ejercicio verificado para este tipo. "
            "Prueba otro tipo o dificultad."
        )


@dataclass
class PerfilEstudiante:
    """Progreso por tipo de EDO y recomendación del siguiente ejercicio."""

    aciertos: dict[str, int] = field(default_factory=dict)
    errores: dict[str, int] = field(default_factory=dict)
    historial: list[dict[str, Any]] = field(default_factory=list)

    def registrar(self, tipo: str, correcto: bool, **detalle: Any) -> None:
        destino = self.aciertos if correcto else self.errores
        destino[tipo] = destino.get(tipo, 0) + 1
        self.historial.append({"tipo": tipo, "correcto": bool(correcto), **detalle})

    def precision(self, tipo: str) -> float | None:
        aciertos = self.aciertos.get(tipo, 0)
        errores = self.errores.get(tipo, 0)
        total = aciertos + errores
        return aciertos / total if total else None

    @property
    def total(self) -> int:
        return sum(self.aciertos.values()) + sum(self.errores.values())

    def resumen(self) -> dict[str, dict[str, float | int | None]]:
        return {
            tipo: {
                "aciertos": self.aciertos.get(tipo, 0),
                "errores": self.errores.get(tipo, 0),
                "precision": self.precision(tipo),
            }
            for tipo in TIPOS
        }


def recomendar_siguiente(perfil: PerfilEstudiante) -> str:
    """Elige el tipo con menor precisión; si no hay datos, rota en orden."""

    sin_datos = [tipo for tipo in TIPOS if perfil.precision(tipo) is None]
    if sin_datos:
        return sin_datos[0]
    return min(TIPOS, key=lambda tipo: (perfil.precision(tipo) or 0.0, TIPOS.index(tipo)))


def _ruta_perfil(ruta: str | Path | None) -> Path:
    if ruta is not None:
        return Path(ruta)
    return Path(__file__).resolve().parent.parent / "data" / "perfil_estudiante.json"


def cargar_perfil(ruta: str | Path | None = None) -> PerfilEstudiante:
    """Carga el perfil desde JSON; si no existe, empieza vacío."""

    archivo = _ruta_perfil(ruta)
    if not archivo.exists():
        return PerfilEstudiante()
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
    except Exception:
        return PerfilEstudiante()
    return PerfilEstudiante(
        aciertos={str(k): int(v) for k, v in datos.get("aciertos", {}).items()},
        errores={str(k): int(v) for k, v in datos.get("errores", {}).items()},
        historial=list(datos.get("historial", [])),
    )


def guardar_perfil(
    perfil: PerfilEstudiante,
    ruta: str | Path | None = None,
) -> Path:
    """Guarda el perfil de forma determinista y devuelve la ruta."""

    archivo = _ruta_perfil(ruta)
    archivo.parent.mkdir(parents=True, exist_ok=True)
    datos = {
        "aciertos": perfil.aciertos,
        "errores": perfil.errores,
        "historial": perfil.historial[-500:],
    }
    archivo.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return archivo


__all__ = [
    "TIPOS",
    "Ejercicio",
    "PerfilEstudiante",
    "generar_ejercicio",
    "recomendar_siguiente",
    "cargar_perfil",
    "guardar_perfil",
]
