"""Carga de datos y ajuste de modelos de EDO con selección AIC/BIC.

Los modelos se integran con SciPy en cada evaluación de residuos.  Se
devuelven parámetros con intervalos de confianza, errores, AIC/BIC,
predicción con banda y sensibilidad local.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import least_squares

from core.tipos import DatosInvalidos, SolucionNoDisponible


@dataclass
class DatosAjuste:
    """Datos experimentales ya validados y ordenados."""

    x: np.ndarray
    y: np.ndarray
    nombres: tuple[str, str] = ("x", "y")
    fuente: str = "datos"

    @property
    def n(self) -> int:
        return int(self.x.size)

    @property
    def resumen(self) -> str:
        return (
            f"{self.n} puntos, x ∈ [{self.x[0]:.6g}, {self.x[-1]:.6g}], "
            f"y ∈ [{np.min(self.y):.6g}, {np.max(self.y):.6g}]"
        )


@dataclass
class ParametroAjustado:
    """Parámetro estimado con su incertidumbre."""

    nombre: str
    valor: float
    error_estandar: float | None = None
    ic_inf: float | None = None
    ic_sup: float | None = None
    unidad: str = ""


@dataclass
class Prediccion:
    """Predicción con banda de confianza."""

    x: np.ndarray
    y: np.ndarray
    ic_inf: np.ndarray
    ic_sup: np.ndarray
    nivel: float = 0.95


@dataclass
class ResultadoAjuste:
    """Resultado completo del ajuste de un modelo candidato."""

    modelo: str
    nombre: str
    parametros: dict[str, ParametroAjustado]
    y0: float
    aic: float
    bic: float
    rmse: float
    r2: float
    exito: bool
    mensaje: str
    residuales: np.ndarray = field(default_factory=lambda: np.asarray([]))
    prediccion: Prediccion | None = None
    sensibilidad: dict[str, float] = field(default_factory=dict)
    ecuacion_latex: str = ""
    covarianza: np.ndarray | None = field(default=None, repr=False)
    datos: DatosAjuste | None = field(default=None, repr=False)

    @property
    def parametros_simples(self) -> dict[str, float]:
        return {nombre: dato.valor for nombre, dato in self.parametros.items()}

    @property
    def resumen(self) -> str:
        if not self.exito:
            return f"{self.nombre}: ajuste fallido ({self.mensaje})."
        parametros = ", ".join(
            f"{nombre} = {dato.valor:.6g}" for nombre, dato in self.parametros.items()
        )
        return f"{self.nombre}: {parametros}. AIC = {self.aic:.3f}."


@dataclass(frozen=True)
class ModeloAjuste:
    """Metadatos de un modelo candidato."""

    id: str
    nombre: str
    descripcion: str
    ecuacion_latex: str
    parametros: tuple[str, ...]
    rhs: Callable[[float, float, dict[str, float]], float]

    def evaluar(self, t: float, y: float, parametros: dict[str, float]) -> float:
        try:
            return float(self.rhs(t, y, parametros))
        except Exception:
            return float("nan")


def _rhs_exponencial(t: float, y: float, p: dict[str, float]) -> float:
    del t
    return p["k"] * y


def _rhs_logistico(t: float, y: float, p: dict[str, float]) -> float:
    del t
    return p["r"] * y * (1.0 - y / p["K"])


def _rhs_gompertz(t: float, y: float, p: dict[str, float]) -> float:
    del t
    if y <= 0 or p["K"] <= 0:
        return 0.0
    return p["r"] * y * math.log(p["K"] / y)


def _rhs_newton(t: float, y: float, p: dict[str, float]) -> float:
    del t
    return -p["k"] * (y - p["Tenv"])


MODELOS: dict[str, ModeloAjuste] = {
    "exponencial": ModeloAjuste(
        id="exponencial",
        nombre="Crecimiento/decaimiento exponencial",
        descripcion="Cambio proporcional al valor actual: y' = k·y.",
        ecuacion_latex=r"y' = k\,y",
        parametros=("k",),
        rhs=_rhs_exponencial,
    ),
    "logistico": ModeloAjuste(
        id="logistico",
        nombre="Logístico",
        descripcion="Crecimiento con capacidad de carga K: y' = r·y·(1-y/K).",
        ecuacion_latex=r"y' = r\,y\left(1-\frac{y}{K}\right)",
        parametros=("r", "K"),
        rhs=_rhs_logistico,
    ),
    "gompertz": ModeloAjuste(
        id="gompertz",
        nombre="Gompertz",
        descripcion="Crecimiento asimétrico: y' = r·y·ln(K/y).",
        ecuacion_latex=r"y' = r\,y\ln\left(\frac{K}{y}\right)",
        parametros=("r", "K"),
        rhs=_rhs_gompertz,
    ),
    "newton": ModeloAjuste(
        id="newton",
        nombre="Enfriamiento de Newton",
        descripcion="La temperatura se acerca al ambiente: y' = -k·(y-Tenv).",
        ecuacion_latex=r"y' = -k\,(y-T_{\mathrm{env}})",
        parametros=("k", "Tenv"),
        rhs=_rhs_newton,
    ),
}


def listar_modelos() -> list[ModeloAjuste]:
    """Modelos candidatos disponibles para el ajuste."""

    return list(MODELOS.values())


def _leer_tabla(fuente: Any, nombre: str | None) -> pd.DataFrame:
    if isinstance(fuente, pd.DataFrame):
        return fuente.copy()
    if isinstance(fuente, (str, Path)):
        ruta = Path(fuente)
        if ruta.suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(ruta)
        return pd.read_csv(ruta)
    if isinstance(fuente, (bytes, bytearray)):
        datos = bytes(fuente)
        if nombre and Path(nombre).suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(io.BytesIO(datos))
        return pd.read_csv(io.BytesIO(datos))
    if hasattr(fuente, "read"):
        if nombre and Path(nombre).suffix.lower() in {".xlsx", ".xls"}:
            return pd.read_excel(fuente)
        return pd.read_csv(fuente)
    raise DatosInvalidos(
        "Formato de datos no reconocido. Usa un CSV, un Excel o un DataFrame."
    )


def _detectar_columnas(tabla: pd.DataFrame) -> tuple[str, str]:
    columnas = list(tabla.columns)
    normalizadas = {str(col).strip().lower(): col for col in columnas}
    candidatas_x = ("x", "t", "tiempo", "time", "hora", "fecha")
    candidatas_y = (
        "y",
        "valor",
        "value",
        "poblacion",
        "población",
        "temperatura",
        "temp",
        "concentracion",
        "concentración",
        "respuesta",
    )
    col_x = next((normalizadas[c] for c in candidatas_x if c in normalizadas), None)
    col_y = next((normalizadas[c] for c in candidatas_y if c in normalizadas), None)
    if col_x is not None and col_y is not None and col_x != col_y:
        return str(col_x), str(col_y)
    # Si no hay nombres conocidos, se usan las dos primeras columnas numéricas.
    numericas = [
        col
        for col in columnas
        if pd.api.types.is_numeric_dtype(tabla[col])
    ]
    if len(numericas) < 2:
        raise DatosInvalidos(
            "Se necesitan al menos dos columnas numéricas: una para el tiempo "
            "y otra para el valor."
        )
    return str(numericas[0]), str(numericas[1])


def cargar_datos(fuente: Any, *, nombre: str | None = None) -> DatosAjuste:
    """Carga CSV/Excel, detecta columnas, elimina NaN y valida el mínimo."""

    try:
        tabla = _leer_tabla(fuente, nombre)
    except DatosInvalidos:
        raise
    except Exception as exc:
        raise DatosInvalidos(
            f"No se pudo leer el archivo de datos: {exc}"
        ) from exc
    if tabla.empty:
        raise DatosInvalidos("El archivo no contiene filas.")
    col_x, col_y = _detectar_columnas(tabla)
    subconjunto = tabla[[col_x, col_y]].copy()
    subconjunto.columns = ["x", "y"]
    subconjunto = subconjunto.apply(pd.to_numeric, errors="coerce")
    subconjunto = subconjunto.replace([np.inf, -np.inf], np.nan).dropna()
    if len(subconjunto) < 5:
        raise DatosInvalidos(
            "Se necesitan al menos 5 puntos válidos después de eliminar NaN."
        )
    subconjunto = subconjunto.sort_values("x").drop_duplicates("x")
    x = subconjunto["x"].to_numpy(dtype=float)
    y = subconjunto["y"].to_numpy(dtype=float)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise DatosInvalidos("Los datos contienen valores no finitos.")
    if np.ptp(x) <= 0:
        raise DatosInvalidos("La columna de tiempo debe tener variación.")
    return DatosAjuste(
        x=x,
        y=y,
        nombres=(col_x, col_y),
        fuente=nombre or "datos cargados",
    )


def _valoraciones_iniciales(
    modelo: ModeloAjuste,
    datos: DatosAjuste,
) -> tuple[np.ndarray, tuple[np.ndarray, np.ndarray]]:
    x, y = datos.x, datos.y
    y0 = float(y[0])
    max_y = float(np.max(y))
    min_y = float(np.min(y))
    rango = max(max_y - min_y, 1e-6)
    if modelo.id == "exponencial":
        p0 = [0.1]
        limites = ([1e-6], [10.0])
    elif modelo.id == "logistico":
        p0 = [0.2, max(max_y * 1.2, y0 + 0.1)]
        limites = ([1e-6, max_y * 1.001], [10.0, max_y * 100 + 1.0])
    elif modelo.id == "gompertz":
        p0 = [0.2, max(max_y * 1.2, y0 + 0.1)]
        limites = ([1e-6, max_y * 1.001], [10.0, max_y * 100 + 1.0])
    else:  # newton
        temperatura_final = float(np.median(y[-max(2, len(y) // 5):]))
        p0 = [0.1, temperatura_final]
        limites = (
            [1e-6, min_y - 10 * rango - 1],
            [10.0, max_y + 10 * rango + 1],
        )
    p0_array = np.asarray(p0, dtype=float)
    p0_array = np.clip(
        p0_array,
        np.asarray(limites[0], dtype=float) + 1e-8,
        np.asarray(limites[1], dtype=float) - 1e-8,
    )
    return p0_array, (
        np.asarray(limites[0], dtype=float),
        np.asarray(limites[1], dtype=float),
    )


def _integrar(
    modelo: ModeloAjuste,
    parametros: dict[str, float],
    x: np.ndarray,
    y0: float,
) -> np.ndarray | None:
    def f(t: float, estado: np.ndarray) -> list[float]:
        return [modelo.evaluar(t, float(estado[0]), parametros)]

    try:
        solucion = solve_ivp(
            f,
            (float(x[0]), float(x[-1])),
            [float(y0)],
            t_eval=x,
            method="RK45",
            rtol=1e-7,
            atol=1e-9,
        )
    except Exception:
        return None
    if not solucion.success or solucion.y.shape[1] != x.size:
        return None
    valores = np.asarray(solucion.y[0], dtype=float)
    if not np.all(np.isfinite(valores)):
        return None
    return valores


def _ajustar_modelo(modelo: ModeloAjuste, datos: DatosAjuste) -> ResultadoAjuste:
    p0, (lim_inf, lim_sup) = _valoraciones_iniciales(modelo, datos)
    y0 = float(datos.y[0])

    def residuos(p: np.ndarray) -> np.ndarray:
        parametros = dict(zip(modelo.parametros, p.tolist()))
        valores = _integrar(modelo, parametros, datos.x, y0)
        if valores is None:
            return np.full_like(datos.y, 1e6)
        return valores - datos.y

    try:
        ajuste = least_squares(
            residuos,
            p0,
            bounds=(lim_inf, lim_sup),
            x_scale="jac",
            max_nfev=2500,
            ftol=1e-12,
            xtol=1e-12,
            gtol=1e-12,
        )
    except Exception as exc:
        return ResultadoAjuste(
            modelo=modelo.id,
            nombre=modelo.nombre,
            parametros={},
            y0=y0,
            aic=float("inf"),
            bic=float("inf"),
            rmse=float("inf"),
            r2=float("-inf"),
            exito=False,
            mensaje=f"No se pudo ajustar: {exc}",
            ecuacion_latex=modelo.ecuacion_latex,
            datos=datos,
        )

    parametros = dict(zip(modelo.parametros, ajuste.x.tolist()))
    valores = _integrar(modelo, parametros, datos.x, y0)
    if valores is None:
        return ResultadoAjuste(
            modelo=modelo.id,
            nombre=modelo.nombre,
            parametros={},
            y0=y0,
            aic=float("inf"),
            bic=float("inf"),
            rmse=float("inf"),
            r2=float("-inf"),
            exito=False,
            mensaje="El modelo no pudo integrarse con los parámetros ajustados.",
            ecuacion_latex=modelo.ecuacion_latex,
            datos=datos,
        )

    residuales = valores - datos.y
    rss = float(np.sum(residuales**2))
    n = datos.n
    k = len(parametros)
    varianza = rss / max(n - k, 1)
    tss = float(np.sum((datos.y - np.mean(datos.y)) ** 2))
    r2 = 1.0 - rss / tss if tss > 0 else float("nan")
    rmse = math.sqrt(rss / n)
    termino = max(rss / n, 1e-300)
    aic = n * math.log(termino) + 2 * k
    bic = n * math.log(termino) + k * math.log(n)

    try:
        jacobiano = np.asarray(ajuste.jac, dtype=float)
        matriz = jacobiano.T @ jacobiano
        covarianza = np.linalg.pinv(matriz) * varianza
    except Exception:
        covarianza = None
    errores = (
        np.sqrt(np.clip(np.diag(covarianza), 0, None))
        if covarianza is not None
        else np.full(k, np.nan)
    )

    parametros_con_ic: dict[str, ParametroAjustado] = {}
    for indice, nombre in enumerate(modelo.parametros):
        valor = float(ajuste.x[indice])
        error = float(errores[indice]) if np.isfinite(errores[indice]) else None
        parametros_con_ic[nombre] = ParametroAjustado(
            nombre=nombre,
            valor=valor,
            error_estandar=error,
            ic_inf=valor - 1.96 * error if error is not None else None,
            ic_sup=valor + 1.96 * error if error is not None else None,
        )

    resultado = ResultadoAjuste(
        modelo=modelo.id,
        nombre=modelo.nombre,
        parametros=parametros_con_ic,
        y0=y0,
        aic=aic,
        bic=bic,
        rmse=rmse,
        r2=r2,
        exito=True,
        mensaje="Ajuste convergente.",
        residuales=residuales,
        ecuacion_latex=modelo.ecuacion_latex,
        covarianza=covarianza,
        datos=datos,
    )
    resultado.sensibilidad = sensibilidad_local(resultado)
    return resultado


def ajustar(
    datos: DatosAjuste,
    *,
    modelos: Iterable[str] | None = None,
) -> list[ResultadoAjuste]:
    """Ajusta todos los modelos candidatos y los ordena por AIC."""

    ids = list(modelos) if modelos is not None else list(MODELOS)
    resultados: list[ResultadoAjuste] = []
    for id_modelo in ids:
        modelo = MODELOS.get(id_modelo)
        if modelo is None:
            continue
        resultados.append(_ajustar_modelo(modelo, datos))
    return sorted(resultados, key=lambda item: item.aic)


def seleccionar_mejor_modelo(resultados: Iterable[ResultadoAjuste]) -> ResultadoAjuste | None:
    """Devuelve el modelo con menor AIC entre los ajustes exitosos."""

    exitosos = [resultado for resultado in resultados if resultado.exito]
    if not exitosos:
        return None
    return min(exitosos, key=lambda item: item.aic)


def sensibilidad_local(
    resultado: ResultadoAjuste,
    *,
    delta_relativo: float = 1e-3,
) -> dict[str, float]:
    """Sensibilidad relativa de y(x_final) a cada parámetro."""

    if not resultado.exito or resultado.datos is None:
        return {}
    modelo = MODELOS.get(resultado.modelo)
    if modelo is None:
        return {}
    datos = resultado.datos
    base = resultado.parametros_simples
    valores_base = _integrar(modelo, base, datos.x, resultado.y0)
    if valores_base is None:
        return {}
    y_base = float(valores_base[-1])
    sensibilidades: dict[str, float] = {}
    for nombre, valor in base.items():
        paso = max(abs(valor) * delta_relativo, 1e-8)
        mas = dict(base)
        menos = dict(base)
        mas[nombre] = valor + paso
        menos[nombre] = valor - paso
        y_mas = _integrar(modelo, mas, datos.x, resultado.y0)
        y_menos = _integrar(modelo, menos, datos.x, resultado.y0)
        if y_mas is None or y_menos is None:
            continue
        derivada = (float(y_mas[-1]) - float(y_menos[-1])) / (2 * paso)
        escala = abs(y_base) if abs(y_base) > 1e-12 else 1.0
        sensibilidades[nombre] = (derivada * valor / escala) if abs(valor) > 1e-12 else derivada / escala
    return sensibilidades


def predecir(
    resultado: ResultadoAjuste,
    x_nuevo: Iterable[float],
    *,
    nivel: float = 0.95,
    n_muestras: int = 600,
    semilla: int = 42,
) -> Prediccion | None:
    """Predice con banda de confianza por Monte Carlo sobre los parámetros."""

    if not resultado.exito or resultado.datos is None:
        return None
    modelo = MODELOS.get(resultado.modelo)
    if modelo is None:
        return None
    x_pred = np.asarray(sorted(float(v) for v in x_nuevo), dtype=float)
    if x_pred.size == 0:
        return None
    datos = resultado.datos
    base = resultado.parametros_simples
    y0 = resultado.y0

    def trayectoria(parametros: dict[str, float]) -> np.ndarray | None:
        def f(t: float, estado: np.ndarray) -> list[float]:
            return [modelo.evaluar(t, float(estado[0]), parametros)]

        try:
            solucion = solve_ivp(
                f,
                (float(datos.x[0]), float(x_pred[-1])),
                [float(y0)],
                t_eval=x_pred,
                method="RK45",
                rtol=1e-7,
                atol=1e-9,
            )
        except Exception:
            return None
        if not solucion.success or solucion.y.shape[1] != x_pred.size:
            return None
        valores = np.asarray(solucion.y[0], dtype=float)
        return valores if np.all(np.isfinite(valores)) else None

    media = trayectoria(base)
    if media is None:
        return None
    rng = np.random.default_rng(semilla)
    nombres = list(base)
    if resultado.covarianza is not None and resultado.covarianza.shape == (len(nombres), len(nombres)):
        muestras_p = rng.multivariate_normal(
            np.asarray([base[n] for n in nombres]),
            resultado.covarianza,
            size=int(n_muestras),
        )
    else:
        muestras_p = np.tile(np.asarray([base[n] for n in nombres]), (int(n_muestras), 1))
    trayectorias: list[np.ndarray] = []
    for fila in muestras_p:
        parametros = {nombre: float(valor) for nombre, valor in zip(nombres, fila)}
        if any(not math.isfinite(valor) for valor in parametros.values()):
            continue
        valores = trayectoria(parametros)
        if valores is not None:
            trayectorias.append(valores)
    if len(trayectorias) < 10:
        trayectorias = [media]
    matriz = np.vstack(trayectorias)
    alfa = (1.0 - nivel) / 2.0
    ic_inf = np.quantile(matriz, alfa, axis=0)
    ic_sup = np.quantile(matriz, 1.0 - alfa, axis=0)
    prediccion = Prediccion(
        x=x_pred,
        y=media,
        ic_inf=ic_inf,
        ic_sup=ic_sup,
        nivel=nivel,
    )
    resultado.prediccion = prediccion
    return prediccion


def cargar_ejemplo(nombre: str = "logistico") -> DatosAjuste:
    """Carga un CSV de ejemplo incluido en ``data/ejemplos``."""

    ruta = Path(__file__).resolve().parent.parent / "data" / "ejemplos" / f"{nombre}.csv"
    if not ruta.exists():
        raise DatosInvalidos(f"No existe el ejemplo de datos: {ruta.name}.")
    return cargar_datos(ruta, nombre=ruta.name)


__all__ = [
    "DatosAjuste",
    "ParametroAjustado",
    "Prediccion",
    "ResultadoAjuste",
    "ModeloAjuste",
    "MODELOS",
    "listar_modelos",
    "cargar_datos",
    "cargar_ejemplo",
    "ajustar",
    "seleccionar_mejor_modelo",
    "sensibilidad_local",
    "predecir",
]
