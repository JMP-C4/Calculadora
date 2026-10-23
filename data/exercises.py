"""Catálogo de ejercicios de EDOs de primer orden."""

from __future__ import annotations

from dataclasses import dataclass

from ui.condition_panel import SolverConditions


@dataclass
class Exercise:
    """Ejercicio precargado de la biblioteca."""

    id: str
    ode_type: str
    name: str
    equation_text: str
    latex_str: str
    description: str
    initial_conditions: SolverConditions | None


_EXERCISES: tuple[Exercise, ...] = (
    # --- Separables ---------------------------------------------------------
    Exercise(
        id="sep-01",
        ode_type="separable",
        name="Crecimiento exponencial",
        equation_text="dy/dx = y",
        latex_str=r"\frac{dy}{dx} = y",
        description=(
            "La tasa de cambio es proporcional a la cantidad presente; "
            "modela crecimiento poblacional sin restricciones."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -2.0, 2.0),
    ),
    Exercise(
        id="sep-02",
        ode_type="separable",
        name="Decaimiento exponencial",
        equation_text="dy/dx = -2*y",
        latex_str=r"\frac{dy}{dx} = -2y",
        description=(
            "La cantidad disminuye a una tasa proporcional a su valor actual, "
            "como en el decaimiento radiactivo."
        ),
        initial_conditions=SolverConditions(0.0, 100.0, 0.0, 5.0),
    ),
    Exercise(
        id="sep-03",
        ode_type="separable",
        name="Separable con seno",
        equation_text="dy/dx = sin(x)*y",
        latex_str=r"\frac{dy}{dx} = \sin(x)\,y",
        description=(
            "Ejemplo clásico de variables separables con un factor periódico "
            "en la variable independiente."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -3.0, 3.0),
    ),
    Exercise(
        id="sep-04",
        ode_type="separable",
        name="Separable cuadrática",
        equation_text="dy/dx = x*y**2",
        latex_str=r"\frac{dy}{dx} = x\,y^2",
        description=(
            "Variables separables donde el lado derecho es producto de una "
            "función de x y una función cuadrática de y."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -2.0, 2.0),
    ),
    # --- Lineales -----------------------------------------------------------
    Exercise(
        id="lin-01",
        ode_type="linear",
        name="Lineal con término independiente",
        equation_text="dy/dx = x + y",
        latex_str=r"\frac{dy}{dx} = x + y",
        description=(
            "EDO lineal de primer orden que se resuelve con el factor "
            "integrante μ(x) = e^(-x)."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -3.0, 3.0),
    ),
    Exercise(
        id="lin-02",
        ode_type="linear",
        name="Lineal con exponencial",
        equation_text="dy/dx = exp(x) - y",
        latex_str=r"\frac{dy}{dx} = e^x - y",
        description=(
            "La incógnita aparece linealmente y el término forzante es una "
            "exponencial."
        ),
        initial_conditions=SolverConditions(0.0, 0.0, -3.0, 3.0),
    ),
    Exercise(
        id="lin-03",
        ode_type="linear",
        name="Lineal forzada por coseno",
        equation_text="dy/dx = cos(x) + y",
        latex_str=r"\frac{dy}{dx} = \cos(x) + y",
        description=(
            "EDO lineal con coeficiente unitario y forzamiento oscilatorio; "
            "útil para practicar el factor integrante."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -3.0, 3.0),
    ),
    # --- Exactas ------------------------------------------------------------
    Exercise(
        id="exa-01",
        ode_type="exact",
        name="Exacta racional",
        equation_text="dy/dx = -(2*x + y)/(x + 2*y)",
        latex_str=r"\frac{dy}{dx} = -\frac{2x+y}{x+2y}",
        description=(
            "EDO exacta porque ∂M/∂y = ∂N/∂x; se resuelve encontrando la "
            "función potencial F(x, y)."
        ),
        initial_conditions=SolverConditions(1.0, 1.0, 0.5, 3.0),
    ),
    Exercise(
        id="exa-02",
        ode_type="exact",
        name="Exacta trigonométrica",
        equation_text="dy/dx = -(y*cos(x) + 2*x)/(sin(x) + 2*y)",
        latex_str=r"\frac{dy}{dx} = -\frac{y\cos(x)+2x}{\sin(x)+2y}",
        description=(
            "La condición de exactitud se satisface gracias a las derivadas "
            "cruzadas de las funciones seno y coseno."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -3.0, 3.0),
    ),
    Exercise(
        id="exa-03",
        ode_type="exact",
        name="Exacta con exponencial",
        equation_text="dy/dx = -(exp(x)*sin(y) + y)/(exp(x)*cos(y) + x)",
        latex_str=r"\frac{dy}{dx} = -\frac{e^x\sin(y)+y}{e^x\cos(y)+x}",
        description=(
            "Ejercicio de exactitud con funciones exponenciales y "
            "trigonométricas combinadas."
        ),
        initial_conditions=SolverConditions(0.0, 0.0, -2.0, 2.0),
    ),
    # --- Homogéneas ---------------------------------------------------------
    Exercise(
        id="hom-01",
        ode_type="homogeneous",
        name="Homogénea simple",
        equation_text="dy/dx = y/x",
        latex_str=r"\frac{dy}{dx} = \frac{y}{x}",
        description=(
            "EDO homogénea de grado cero; con y = ux se reduce a una ecuación "
            "separable en u y x."
        ),
        initial_conditions=SolverConditions(1.0, 1.0, 0.1, 4.0),
    ),
    Exercise(
        id="hom-02",
        ode_type="homogeneous",
        name="Homogénea con suma",
        equation_text="dy/dx = (x + y)/x",
        latex_str=r"\frac{dy}{dx} = \frac{x+y}{x}",
        description=(
            "La sustitución y = ux transforma la ecuación en u + x u' = 1 + u."
        ),
        initial_conditions=SolverConditions(1.0, 2.0, 0.1, 4.0),
    ),
    # --- Bernoulli ----------------------------------------------------------
    Exercise(
        id="ber-01",
        ode_type="bernoulli",
        name="Bernoulli logística",
        equation_text="dy/dx = y**2 - y",
        latex_str=r"\frac{dy}{dx} = y^2 - y",
        description=(
            "EDO de Bernoulli con n = 2 relacionada con el modelo logístico de "
            "crecimiento poblacional."
        ),
        initial_conditions=SolverConditions(0.0, 2.0, -2.0, 2.0),
    ),
    Exercise(
        id="ber-02",
        ode_type="bernoulli",
        name="Bernoulli con exponencial",
        equation_text="dy/dx = exp(-x)*y**2",
        latex_str=r"\frac{dy}{dx} = e^{-x}y^2",
        description=(
            "Ecuación de Bernoulli con n = 2 y coeficiente variable; se "
            "linealiza con v = 1/y."
        ),
        initial_conditions=SolverConditions(0.0, 1.0, -2.0, 2.0),
    ),
    Exercise(
        id="ber-03",
        ode_type="bernoulli",
        name="Bernoulli con término lineal",
        equation_text="dy/dx = y + y**2",
        latex_str=r"\frac{dy}{dx} = y + y^2",
        description=(
            "Ejemplo de Bernoulli donde coexisten el término lineal y el "
            "término cuadrático."
        ),
        initial_conditions=SolverConditions(0.0, 0.5, -2.0, 2.0),
    ),
    # --- Aplicaciones -------------------------------------------------------
    Exercise(
        id="app-01",
        ode_type="application",
        name="Aplicación: decaimiento radiactivo",
        equation_text="dy/dx = -0.5*y",
        latex_str=r"\frac{dy}{dx} = -0.5y",
        description=(
            "Modelo de decaimiento radiactivo: la masa restante disminuye a una "
            "tasa proporcional a la masa presente."
        ),
        initial_conditions=SolverConditions(0.0, 100.0, 0.0, 10.0),
    ),
    Exercise(
        id="app-02",
        ode_type="application",
        name="Aplicación: mezcla en un tanque",
        equation_text="dy/dx = 0.1 - y/50",
        latex_str=r"\frac{dy}{dx} = 0.1 - \frac{y}{50}",
        description=(
            "Balance de sal en un tanque con entrada y salida de solución; la "
            "concentración tiende a un valor de equilibrio."
        ),
        initial_conditions=SolverConditions(0.0, 0.0, 0.0, 200.0),
    ),
    Exercise(
        id="app-03",
        ode_type="application",
        name="Aplicación: circuito RC",
        equation_text="dy/dx = (12 - y)/2",
        latex_str=r"\frac{dy}{dx} = \frac{12-y}{2}",
        description=(
            "Carga de un capacitor en un circuito RC alimentado por una fuente "
            "de 12 V; la respuesta se aproxima al voltaje de la fuente."
        ),
        initial_conditions=SolverConditions(0.0, 0.0, 0.0, 10.0),
    ),
)


def load_exercises() -> list[Exercise]:
    """Devuelve el catálogo completo de ejercicios."""

    return list(_EXERCISES)


__all__ = ["Exercise", "load_exercises"]
