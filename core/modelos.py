"""Biblioteca de modelos aplicados de EDO de primer orden.

Cada modelo describe un fenómeno real, sus parámetros con valores por defecto
y el intervalo recomendado.  La ecuación se entrega ya instanciada (sin
símbolos libres) para que pueda resolverse con :func:`core.hibrido.resolver`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import sympy as sp

from odecalc.symbols import X, Y

from core.tipos import EntradaInvalida


def _simbolo(nombre: str) -> sp.Symbol:
    return sp.Symbol(nombre, real=True)


@dataclass(frozen=True)
class ParametroModelo:
    """Parámetro de un modelo aplicado."""

    nombre: str
    etiqueta: str
    valor_defecto: float
    unidad: str = ""
    descripcion: str = ""
    minimo: float | None = None
    maximo: float | None = None


@dataclass(frozen=True)
class ModeloAplicado:
    """Metadatos de un modelo y su ecuación simbólica de referencia."""

    id: str
    nombre: str
    descripcion: str
    ecuacion: str
    ecuacion_latex: str
    parametros: tuple[ParametroModelo, ...]
    rhs_plantilla: sp.Expr
    x0: float
    y0: float
    x_min: float
    x_max: float
    contexto: str = ""
    solucion_conocida: str = ""
    unidad_y: str = ""
    unidad_x: str = ""

    @property
    def parametros_defecto(self) -> dict[str, float]:
        return {parametro.nombre: float(parametro.valor_defecto) for parametro in self.parametros}

    @property
    def simbolos(self) -> dict[str, sp.Symbol]:
        return {parametro.nombre: _simbolo(parametro.nombre) for parametro in self.parametros}

    def parametro(self, nombre: str) -> ParametroModelo:
        for parametro in self.parametros:
            if parametro.nombre == nombre:
                return parametro
        raise KeyError(nombre)


@dataclass
class ModeloInstanciado:
    """Modelo con valores numéricos listo para resolver o exportar."""

    id: str
    nombre: str
    descripcion: str
    ecuacion_texto: str
    ecuacion_latex: str
    parametros: dict[str, float]
    x0: float
    y0: float
    x_min: float
    x_max: float
    contexto: str = ""
    solucion_conocida: str = ""
    unidad_y: str = ""
    unidad_x: str = ""
    advertencias: list[str] = field(default_factory=list)

    @property
    def parametros_texto(self) -> str:
        if not self.parametros:
            return "sin parámetros"
        return ", ".join(f"{nombre} = {valor:g}" for nombre, valor in self.parametros.items())

    @property
    def condicion_inicial(self) -> str:
        return f"y({self.x0:g}) = {self.y0:g}"

    @property
    def intervalo(self) -> tuple[float, float]:
        return (self.x_min, self.x_max)


def _crear_modelos() -> dict[str, ModeloAplicado]:
    r, K = _simbolo("r"), _simbolo("K")
    k, Tenv = _simbolo("k"), _simbolo("Tenv")
    V, R, L = _simbolo("V"), _simbolo("R"), _simbolo("L")
    q, C_in = _simbolo("q"), _simbolo("C_in")
    lam = _simbolo("lambda")
    g, c, m = _simbolo("g"), _simbolo("c"), _simbolo("m")

    modelos = [
        ModeloAplicado(
            id="poblacion",
            nombre="Crecimiento poblacional logístico",
            descripcion=(
                "Una población crece a tasa r y se satura en la capacidad de "
                "carga K del medio. Es el modelo logístico clásico."
            ),
            ecuacion="y' = r*y*(1 - y/K)",
            ecuacion_latex=r"\frac{dy}{dx} = r\,y\left(1-\frac{y}{K}\right)",
            parametros=(
                ParametroModelo("r", "Tasa de crecimiento", 0.8, "1/tiempo", "Crecimiento intrínseco.", 0.01),
                ParametroModelo("K", "Capacidad de carga", 100.0, "individuos", "Población máxima sostenible.", 0.01),
            ),
            rhs_plantilla=r * Y * (1 - Y / K),
            x0=0.0,
            y0=5.0,
            x_min=0.0,
            x_max=20.0,
            contexto="Población inicial pequeña frente a la capacidad de carga.",
            solucion_conocida="y(x) = K / (1 + ((K-y0)/y0) e^{-r x})",
            unidad_y="individuos",
            unidad_x="tiempo",
        ),
        ModeloAplicado(
            id="newton",
            nombre="Ley de enfriamiento de Newton",
            descripcion=(
                "La temperatura de un cuerpo se acerca exponencialmente a la "
                "temperatura ambiente Tenv, con constante k."
            ),
            ecuacion="y' = -k*(y - Tenv)",
            ecuacion_latex=r"\frac{dy}{dx} = -k\,(y-T_{\mathrm{env}})",
            parametros=(
                ParametroModelo("k", "Constante de enfriamiento", 0.08, "1/tiempo", "Rapidez del intercambio térmico.", 0.001),
                ParametroModelo("Tenv", "Temperatura ambiente", 20.0, "°C", "Temperatura del entorno.", None),
            ),
            rhs_plantilla=-k * (Y - Tenv),
            x0=0.0,
            y0=90.0,
            x_min=0.0,
            x_max=60.0,
            contexto="Un café caliente se enfría en una habitación a 20 °C.",
            solucion_conocida="y(x) = Tenv + (y0-Tenv) e^{-k x}",
            unidad_y="°C",
            unidad_x="min",
        ),
        ModeloAplicado(
            id="circuito_rl",
            nombre="Circuito RL en serie",
            descripcion=(
                "La corriente en un circuito con resistencia R e inductancia L "
                "tiende a V/R al conectarse una fuente de tensión V."
            ),
            ecuacion="y' = (V - R*y)/L",
            ecuacion_latex=r"\frac{dy}{dx} = \frac{V-R\,y}{L}",
            parametros=(
                ParametroModelo("V", "Tensión de la fuente", 12.0, "V", "Voltaje aplicado.", None),
                ParametroModelo("R", "Resistencia", 10.0, "Ω", "Resistencia del circuito.", 0.01),
                ParametroModelo("L", "Inductancia", 1.0, "H", "Inductancia de la bobina.", 0.001),
            ),
            rhs_plantilla=(V - R * Y) / L,
            x0=0.0,
            y0=0.0,
            x_min=0.0,
            x_max=2.0,
            contexto="Interruptor que se cierra en x = 0 con corriente inicial nula.",
            solucion_conocida="y(x) = (V/R)(1 - e^{-R x/L})",
            unidad_y="A",
            unidad_x="s",
        ),
        ModeloAplicado(
            id="mezclas",
            nombre="Mezcla en un tanque",
            descripcion=(
                "Un tanque bien agitado recibe y descarga caudal q. La "
                "concentración y tiende a la concentración de entrada C_in."
            ),
            ecuacion="y' = (q/V)*(C_in - y)",
            ecuacion_latex=r"\frac{dy}{dx} = \frac{q}{V}\,(C_{\mathrm{in}}-y)",
            parametros=(
                ParametroModelo("q", "Caudal", 2.0, "L/min", "Flujo de entrada y salida.", 0.001),
                ParametroModelo("V", "Volumen del tanque", 100.0, "L", "Volumen constante de mezcla.", 0.001),
                ParametroModelo("C_in", "Concentración de entrada", 5.0, "g/L", "Concentración del influente.", 0.0),
            ),
            rhs_plantilla=(q / V) * (C_in - Y),
            x0=0.0,
            y0=0.0,
            x_min=0.0,
            x_max=200.0,
            contexto="Tanque inicialmente con agua limpia; entra salmuera a 5 g/L.",
            solucion_conocida="y(x) = C_in + (y0-C_in) e^{-q x/V}",
            unidad_y="g/L",
            unidad_x="min",
        ),
        ModeloAplicado(
            id="decaimiento",
            nombre="Decaimiento radiactivo",
            descripcion=(
                "La cantidad de sustancia radiactiva disminuye a una tasa "
                "proporcional a la cantidad presente."
            ),
            ecuacion="y' = -lambda*y",
            ecuacion_latex=r"\frac{dy}{dx} = -\lambda\,y",
            parametros=(
                ParametroModelo("lambda", "Constante de decaimiento", 0.1, "1/tiempo", "Relacionada con la vida media.", 1e-6),
            ),
            rhs_plantilla=-lam * Y,
            x0=0.0,
            y0=100.0,
            x_min=0.0,
            x_max=50.0,
            contexto="Muestra inicial de 100 unidades que decae con λ = 0.1.",
            solucion_conocida="y(x) = y0 e^{-λ x}",
            unidad_y="unidades",
            unidad_x="años",
        ),
        ModeloAplicado(
            id="resistencia_aire",
            nombre="Caída con resistencia del aire",
            descripcion=(
                "Un cuerpo que cae bajo la gravedad sufre una resistencia "
                "proporcional al cuadrado de la velocidad. La velocidad tiende "
                "a la velocidad terminal sqrt(m g / c)."
            ),
            ecuacion="y' = g - (c/m)*y^2",
            ecuacion_latex=r"\frac{dy}{dx} = g-\frac{c}{m}\,y^{2}",
            parametros=(
                ParametroModelo("g", "Gravedad", 9.81, "m/s²", "Aceleración gravitatoria.", 0.0),
                ParametroModelo("c", "Coeficiente de arrastre", 0.5, "kg/m", "Resistencia aerodinámica.", 0.0),
                ParametroModelo("m", "Masa", 2.0, "kg", "Masa del cuerpo.", 0.001),
            ),
            rhs_plantilla=g - (c / m) * Y**2,
            x0=0.0,
            y0=0.0,
            x_min=0.0,
            x_max=10.0,
            contexto="Velocidad vertical de un objeto que se suelta desde el reposo.",
            solucion_conocida="v(x) = v_t tanh(g x / v_t), con v_t = sqrt(m g / c)",
            unidad_y="m/s",
            unidad_x="s",
        ),
    ]
    return {modelo.id: modelo for modelo in modelos}


MODELOS: dict[str, ModeloAplicado] = _crear_modelos()


def listar_modelos() -> list[ModeloAplicado]:
    """Devuelve todos los modelos aplicados disponibles."""

    return list(MODELOS.values())


def obtener_modelo(id_modelo: str) -> ModeloAplicado:
    """Busca un modelo por identificador y falla con un mensaje claro."""

    modelo = MODELOS.get(str(id_modelo).strip().lower())
    if modelo is None:
        disponibles = ", ".join(sorted(MODELOS))
        raise EntradaInvalida(
            f"Modelo desconocido: {id_modelo}. Disponibles: {disponibles}."
        )
    return modelo


def instanciar_modelo(
    id_modelo: str,
    *,
    parametros: dict[str, float] | None = None,
    x0: float | None = None,
    y0: float | None = None,
    x_min: float | None = None,
    x_max: float | None = None,
) -> ModeloInstanciado:
    """Sustituye los parámetros y condiciones iniciales de un modelo."""

    modelo = obtener_modelo(id_modelo)
    valores = modelo.parametros_defecto
    if parametros:
        for nombre, valor in parametros.items():
            if nombre not in valores:
                raise EntradaInvalida(
                    f"El modelo {modelo.nombre} no tiene el parámetro «{nombre}». "
                    f"Parámetros válidos: {', '.join(valores)}."
                )
            try:
                valores[nombre] = float(valor)
            except (TypeError, ValueError) as exc:
                raise EntradaInvalida(
                    f"El parámetro «{nombre}» debe ser numérico."
                ) from exc

    for nombre, valor in valores.items():
        if not math.isfinite(valor):
            raise EntradaInvalida(f"El parámetro «{nombre}» debe ser finito.")
        parametro = modelo.parametro(nombre)
        if parametro.minimo is not None and valor < parametro.minimo:
            raise EntradaInvalida(
                f"El parámetro «{nombre}» debe ser mayor o igual que "
                f"{parametro.minimo:g}."
            )
        if parametro.maximo is not None and valor > parametro.maximo:
            raise EntradaInvalida(
                f"El parámetro «{nombre}» debe ser menor o igual que "
                f"{parametro.maximo:g}."
            )

    inicio_x = float(modelo.x0 if x0 is None else x0)
    inicio_y = float(modelo.y0 if y0 is None else y0)
    limite_inf = float(modelo.x_min if x_min is None else x_min)
    limite_sup = float(modelo.x_max if x_max is None else x_max)
    if not all(math.isfinite(v) for v in (inicio_x, inicio_y, limite_inf, limite_sup)):
        raise EntradaInvalida("La condición inicial y el intervalo deben ser finitos.")
    if limite_inf >= limite_sup:
        raise EntradaInvalida("El intervalo no es válido: x_min debe ser menor que x_max.")
    if not (limite_inf <= inicio_x <= limite_sup):
        raise EntradaInvalida("La condición inicial x₀ debe pertenecer al intervalo.")

    sustituciones = {
        modelo.simbolos[nombre]: valor for nombre, valor in valores.items()
    }
    rhs = sp.simplify(modelo.rhs_plantilla.subs(sustituciones))
    if rhs.free_symbols - {X, Y}:
        raise EntradaInvalida(
            "El modelo contiene símbolos sin sustituir; revisa sus parámetros."
        )
    texto = "y' = " + sp.sstr(rhs)
    latex = r"\frac{dy}{dx} = " + sp.latex(rhs)

    advertencias: list[str] = []
    if modelo.id == "resistencia_aire":
        velocidad_terminal = math.sqrt(
            valores["m"] * valores["g"] / valores["c"]
        )
        advertencias.append(
            f"Velocidad terminal aproximada: {velocidad_terminal:.4g} m/s."
        )

    return ModeloInstanciado(
        id=modelo.id,
        nombre=modelo.nombre,
        descripcion=modelo.descripcion,
        ecuacion_texto=texto,
        ecuacion_latex=latex,
        parametros=valores,
        x0=inicio_x,
        y0=inicio_y,
        x_min=limite_inf,
        x_max=limite_sup,
        contexto=modelo.contexto,
        solucion_conocida=modelo.solucion_conocida,
        unidad_y=modelo.unidad_y,
        unidad_x=modelo.unidad_x,
        advertencias=advertencias,
    )


def resolver_modelo(
    instancia: ModeloInstanciado,
    *,
    timeout: float | None = 10.0,
    metodo: str | None = None,
):
    """Resuelve un modelo instanciado con el orquestador híbrido."""

    from core.hibrido import resolver

    return resolver(
        instancia.ecuacion_texto,
        x0=instancia.x0,
        y0=instancia.y0,
        x_min=instancia.x_min,
        x_max=instancia.x_max,
        timeout=timeout,
        metodo=metodo,
    )


__all__ = [
    "ParametroModelo",
    "ModeloAplicado",
    "ModeloInstanciado",
    "MODELOS",
    "listar_modelos",
    "obtener_modelo",
    "instanciar_modelo",
    "resolver_modelo",
]
