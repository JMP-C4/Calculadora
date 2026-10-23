"""Generación del procedimiento paso a paso para EDOs de primer orden.

Cada paso incluye la operación realizada, la expresión resultante en LaTeX,
la justificación matemática y, cuando aporta claridad, un detalle atómico.
El resultado también contiene una representación ASCII para el portapapeles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import sympy as sp

if TYPE_CHECKING:  # pragma: no cover - solo para anotaciones
    from math_engine.numeric_solver import NumericResult
    from math_engine.symbolic_solver import SymbolicResult

x = sp.Symbol("x", real=True)
y = sp.Function("y")(x)
_Y = sp.Symbol("y", real=True)
_U = sp.Symbol("u", real=True)
_C = sp.Symbol("C", real=True)


@dataclass
class SolutionStep:
    """Un paso atómico del procedimiento de resolución."""

    number: int
    operation: str
    latex_expr: str
    justification: str
    detail: str | None = None
    ascii_expr: str | None = None


@dataclass
class StepByStepResult:
    """Resultado completo del generador de pasos."""

    steps: list[SolutionStep]
    ode_type: str
    ascii_text: str


class _StepBuilder:
    def __init__(self) -> None:
        self.steps: list[SolutionStep] = []

    def add(
        self,
        operation: str,
        latex_expr: str,
        justification: str,
        detail: str | None = None,
        ascii_expr: str | None = None,
    ) -> None:
        self.steps.append(
            SolutionStep(
                number=len(self.steps) + 1,
                operation=operation,
                latex_expr=latex_expr,
                justification=justification,
                detail=detail,
                ascii_expr=ascii_expr,
            )
        )


def _safe_integrate(expression: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    try:
        return sp.integrate(expression, variable)
    except Exception:  # pragma: no cover - integrales no elementales
        return sp.Integral(expression, variable)


def _separable_parts(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """Devuelve ``(g(x), h(y))`` si ``rhs = g(x) * h(y)``."""

    try:
        plain = sp.factor(rhs).subs(y, _Y)
        independent, dependent = plain.as_independent(_Y)
    except Exception:  # pragma: no cover - expresiones patológicas
        return None

    if dependent.has(x) or independent.has(_Y):
        return None
    if sp.simplify(independent * dependent - plain) != 0:
        return None
    return independent, dependent.subs(_Y, y)


def _bernoulli_power(rhs: sp.Expr) -> int | None:
    """Devuelve ``n`` si la EDO tiene forma Bernoulli ``y' + P y = Q y^n``."""

    try:
        polynomial = sp.Poly(sp.expand(rhs), y)
        degrees = {term[0][0] for term in polynomial.terms()}
    except (sp.PolynomialError, TypeError, ValueError):
        return None

    nontrivial = {degree for degree in degrees if degree not in (0, 1)}
    if len(nontrivial) != 1:
        return None
    degree = nontrivial.pop()
    if not (isinstance(degree, int) and degree > 1):
        return None
    if 0 in degrees or degrees - {1, degree}:
        return None
    return int(degree)


def _exact_parts(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """Extrae ``M`` y ``N`` de ``dy/dx = -M/N`` si la EDO es exacta."""

    try:
        numerator, denominator = sp.fraction(sp.together(rhs))
    except Exception:  # pragma: no cover
        return None

    if denominator == 0:
        return None

    big_m = sp.simplify(-numerator)
    big_n = sp.simplify(denominator)
    d_m_dy = sp.simplify(sp.diff(big_m.subs(y, _Y), _Y))
    d_n_dx = sp.simplify(sp.diff(big_n.subs(y, _Y), x))

    if sp.simplify(d_m_dy - d_n_dx) != 0:
        return None
    if d_m_dy == 0 and d_n_dx == 0:
        return None
    return big_m, big_n


def _is_homogeneous(rhs: sp.Expr) -> bool:
    try:
        substituted = sp.simplify(rhs.subs(y, _U * x))
    except Exception:  # pragma: no cover
        return False
    return bool(substituted.has(_U) and not substituted.has(x))


def _is_linear(rhs: sp.Expr) -> bool:
    coefficient = sp.simplify(sp.diff(rhs, y))
    if coefficient.has(y):
        return False
    remainder = sp.simplify(rhs - coefficient * y)
    return not remainder.has(y)


def classify_ode(rhs: sp.Expr) -> str:
    """Clasifica la EDO en separable, lineal, exacta, homogénea o Bernoulli."""

    if not rhs.has(y):
        return "linear"
    if _bernoulli_power(rhs) is not None:
        return "bernoulli"
    if _exact_parts(rhs) is not None:
        return "exact"
    if _is_homogeneous(rhs):
        return "homogeneous"
    if _separable_parts(rhs) is not None:
        return "separable"
    if _is_linear(rhs):
        return "linear"
    return "otro"


def _solution_rhs(symbolic_result: "SymbolicResult | None", attribute: str) -> sp.Expr | None:
    if symbolic_result is None:
        return None
    solution = getattr(symbolic_result, attribute, None)
    if isinstance(solution, (list, tuple)):
        solution = solution[0] if solution else None
    if isinstance(solution, sp.Eq):
        return solution.rhs
    return None


def _particular_values(conditions: Any) -> tuple[Any, Any] | None:
    if conditions is None:
        return None
    x0 = getattr(conditions, "x0", None)
    y0 = getattr(conditions, "y0", None)
    if x0 is None or y0 is None:
        return None
    return x0, y0


def _add_identification(builder: _StepBuilder, rhs: sp.Expr, ode_type: str) -> None:
    names = {
        "separable": "separable",
        "linear": "lineal de primer orden",
        "exact": "exacta",
        "homogeneous": "homogénea",
        "bernoulli": "de Bernoulli",
        "otro": "no clasificada en un método elemental",
    }
    builder.add(
        "Identificar el tipo de EDO",
        sp.latex(sp.Eq(sp.Derivative(y, x), rhs)),
        f"La ecuación se clasifica como EDO {names.get(ode_type, ode_type)}.",
        ascii_expr=f"dy/dx = {sp.pretty(rhs)}",
    )


def _add_condition_step(
    builder: _StepBuilder,
    general_rhs: sp.Expr | None,
    conditions: Any,
) -> None:
    values = _particular_values(conditions)
    if values is None or general_rhs is None:
        return
    x0, y0 = values
    substituted = general_rhs.subs(x, x0)
    builder.add(
        "Aplicar la condición inicial",
        sp.latex(sp.Eq(substituted, y0)),
        "Se sustituye x = x₀ y y = y₀ en la solución general para determinar la constante.",
        detail=f"Sustitución: x₀ = {x0}, y₀ = {y0}.",
        ascii_expr=f"{sp.pretty(substituted)} = {y0}",
    )


def _add_particular_step(
    builder: _StepBuilder,
    symbolic_result: "SymbolicResult | None",
) -> None:
    particular = _solution_rhs(symbolic_result, "particular_solution")
    if particular is None:
        return
    builder.add(
        "Obtener la solución particular",
        sp.latex(sp.Eq(y, sp.simplify(particular))),
        "Al reemplazar la constante por su valor se obtiene la solución que cumple la condición inicial.",
        ascii_expr=f"y = {sp.pretty(sp.simplify(particular))}",
    )


def _add_separable_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None",
    conditions: Any,
) -> None:
    _add_identification(builder, rhs, "separable")
    parts = _separable_parts(rhs)
    if parts is None:
        generic = _solution_rhs(symbolic_result, "general_solution")
        if generic is not None:
            builder.add(
                "Resolver con dsolve",
                sp.latex(sp.Eq(y, generic)),
                "SymPy aplicó separación de variables y devolvió la solución general.",
            )
        return

    g_x, h_y = parts
    builder.add(
        "Separar variables",
        rf"\frac{{1}}{{{sp.latex(h_y)}}}\,dy = {sp.latex(g_x)}\,dx",
        "Se dividen ambos lados entre h(y) y se multiplica por dx para dejar cada variable en un miembro.",
        detail="Forma separable: f(y) dy = g(x) dx.",
        ascii_expr=f"dy/({sp.pretty(h_y)}) = ({sp.pretty(g_x)}) dx",
    )

    h_y_plain = h_y.subs(y, _Y)
    left_integral = _safe_integrate(1 / h_y_plain, _Y).subs(_Y, y)
    right_integral = _safe_integrate(g_x, x)
    builder.add(
        "Integrar ambos lados",
        f"{sp.latex(left_integral)} = {sp.latex(right_integral)} + C",
        "Se integra cada miembro por separado; la constante de integración se añade una sola vez.",
        detail="Regla aplicada término a término.",
        ascii_expr=f"{sp.pretty(left_integral)} = {sp.pretty(right_integral)} + C",
    )

    general = _solution_rhs(symbolic_result, "general_solution")
    if general is not None:
        builder.add(
            "Despejar y",
            sp.latex(sp.Eq(y, general)),
            "Se resuelve la ecuación implícita para expresar y en función de x.",
            ascii_expr=f"y = {sp.pretty(general)}",
        )
    _add_condition_step(builder, general, conditions)
    _add_particular_step(builder, symbolic_result)


def _add_linear_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None",
    conditions: Any,
) -> None:
    _add_identification(builder, rhs, "linear")

    coefficient = sp.simplify(sp.diff(rhs, y))
    p_x = sp.simplify(-coefficient)
    q_x = sp.simplify(rhs - coefficient * y)

    builder.add(
        "Escribir en forma estándar",
        f"{sp.latex(sp.Derivative(y, x))} + {sp.latex(p_x)}\\,y = {sp.latex(q_x)}",
        "La EDO lineal se escribe como y' + P(x)y = Q(x) para identificar P y Q.",
        detail=f"P(x) = {sp.latex(p_x)}, Q(x) = {sp.latex(q_x)}.",
        ascii_expr=f"y' + ({sp.pretty(p_x)})y = {sp.pretty(q_x)}",
    )

    integral_p = _safe_integrate(p_x, x)
    mu = sp.simplify(sp.exp(integral_p))
    builder.add(
        "Calcular el factor integrante μ(x)",
        rf"\mu(x) = e^{{{sp.latex(integral_p)}}} = {sp.latex(mu)}",
        "El factor integrante se obtiene con μ(x) = e^(∫P(x)dx) y convierte el lado izquierdo en una derivada exacta.",
        detail=f"∫P(x)dx = {sp.latex(integral_p)}.",
        ascii_expr=f"mu(x) = exp({sp.pretty(integral_p)}) = {sp.pretty(mu)}",
    )

    builder.add(
        "Multiplicar por μ(x)",
        rf"{sp.latex(mu)}\,{sp.latex(sp.Derivative(y, x))} + {sp.latex(sp.simplify(mu * p_x))}\,y = {sp.latex(sp.simplify(mu * q_x))}",
        "Al multiplicar toda la ecuación por μ(x), el lado izquierdo se reconoce como la derivada del producto μ(x)y.",
        detail="(μ(x) y)' = μ(x) Q(x).",
        ascii_expr=f"({sp.pretty(mu)} y)' = {sp.pretty(sp.simplify(mu * q_x))}",
    )

    integral_muq = _safe_integrate(sp.simplify(mu * q_x), x)
    builder.add(
        "Integrar ambos lados",
        rf"{sp.latex(mu)}\,y = {sp.latex(integral_muq)} + C",
        "Se integra la derivada del producto y se añade la constante de integración.",
        ascii_expr=f"{sp.pretty(mu)} y = {sp.pretty(integral_muq)} + C",
    )

    general = _solution_rhs(symbolic_result, "general_solution")
    if general is not None:
        builder.add(
            "Despejar y",
            sp.latex(sp.Eq(y, general)),
            "Se divide entre μ(x) para obtener la solución general.",
            ascii_expr=f"y = {sp.pretty(general)}",
        )
    _add_condition_step(builder, general, conditions)
    _add_particular_step(builder, symbolic_result)


def _add_bernoulli_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None",
    conditions: Any,
) -> None:
    n = _bernoulli_power(rhs)
    _add_identification(builder, rhs, "bernoulli")
    if n is None:
        return

    polynomial = sp.Poly(sp.expand(rhs), y)
    q_x = sp.simplify(polynomial.coeff_monomial(y**n))
    p_x = sp.simplify(-polynomial.coeff_monomial(y))

    builder.add(
        "Aplicar la sustitución de Bernoulli",
        rf"v = y^{{{1 - n}}}",
        "Para una EDO de Bernoulli y' + P(x)y = Q(x)yⁿ se usa v = y^(1-n), que la transforma en una EDO lineal.",
        detail=f"n = {n}; 1 - n = {1 - n}.",
        ascii_expr=f"v = y**({1 - n})",
    )

    p_transformed = sp.simplify((1 - n) * p_x)
    q_transformed = sp.simplify((1 - n) * q_x)
    builder.add(
        "Transformar en EDO lineal",
        f"{sp.latex(sp.Derivative(sp.Function('v')(x), x))} + {sp.latex(p_transformed)}\\,v = {sp.latex(q_transformed)}",
        "Al derivar v = y^(1-n) y sustituir en la ecuación original se obtiene una EDO lineal en v.",
        ascii_expr=f"v' + ({sp.pretty(p_transformed)})v = {sp.pretty(q_transformed)}",
    )

    integral_p = _safe_integrate(p_transformed, x)
    mu = sp.simplify(sp.exp(integral_p))
    builder.add(
        "Calcular el factor integrante μ(x)",
        rf"\mu(x) = e^{{{sp.latex(integral_p)}}} = {sp.latex(mu)}",
        "Se aplica el método del factor integrante a la EDO lineal resultante.",
        ascii_expr=f"mu(x) = {sp.pretty(mu)}",
    )

    integral_muq = _safe_integrate(sp.simplify(mu * q_transformed), x)
    builder.add(
        "Integrar y despejar v",
        rf"v = \frac{{{sp.latex(integral_muq)} + C}}{{{sp.latex(mu)}}}",
        "Se integra (μv)' = μQ y se divide entre μ(x) para obtener v.",
        ascii_expr=f"v = ({sp.pretty(integral_muq)} + C)/({sp.pretty(mu)})",
    )

    general = _solution_rhs(symbolic_result, "general_solution")
    if general is not None:
        builder.add(
            "Volver a la variable original",
            sp.latex(sp.Eq(y, general)),
            "Se sustituye v = y^(1-n) y se despeja y para obtener la solución general.",
            ascii_expr=f"y = {sp.pretty(general)}",
        )
    _add_condition_step(builder, general, conditions)
    _add_particular_step(builder, symbolic_result)


def _add_exact_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None",
    conditions: Any,
) -> None:
    _add_identification(builder, rhs, "exact")
    parts = _exact_parts(rhs)
    if parts is None:
        return
    big_m, big_n = parts
    d_m_dy = sp.simplify(sp.diff(big_m.subs(y, _Y), _Y))
    d_n_dx = sp.simplify(sp.diff(big_n.subs(y, _Y), x))

    builder.add(
        "Verificar la condición de exactitud",
        rf"\frac{{\partial M}}{{\partial y}} = {sp.latex(d_m_dy)}, \quad \frac{{\partial N}}{{\partial x}} = {sp.latex(d_n_dx)}",
        "La EDO M(x,y)dx + N(x,y)dy = 0 es exacta porque ∂M/∂y = ∂N/∂x.",
        detail="M = " + sp.pretty(big_m) + "; N = " + sp.pretty(big_n),
        ascii_expr=f"dM/dy = {sp.pretty(d_m_dy)}, dN/dx = {sp.pretty(d_n_dx)}",
    )

    potential = _safe_integrate(big_m.subs(y, _Y), x).subs(_Y, y)
    builder.add(
        "Integrar M respecto a x",
        rf"F(x,y) = {sp.latex(potential)} + g(y)",
        "Se integra M(x,y) respecto a x; la constante de integración puede depender de y.",
        ascii_expr=f"F = {sp.pretty(potential)} + g(y)",
    )

    g_prime = sp.simplify(
        big_n.subs(y, _Y) - sp.diff(potential.subs(y, _Y), _Y)
    )
    g_y = _safe_integrate(g_prime, _Y).subs(_Y, y)
    builder.add(
        "Determinar g(y)",
        rf"g'(y) = {sp.latex(g_prime)} \quad\Rightarrow\quad g(y) = {sp.latex(g_y)}",
        "Se deriva F respecto a y, se iguala con N(x,y) y se integra para encontrar g(y).",
        ascii_expr=f"g'(y) = {sp.pretty(g_prime)}, g(y) = {sp.pretty(g_y)}",
    )

    potential_full = sp.simplify(potential + g_y)
    builder.add(
        "Escribir la función potencial",
        rf"F(x,y) = {sp.latex(potential_full)} = C",
        "La solución general de una EDO exacta es F(x,y) = C.",
        ascii_expr=f"{sp.pretty(potential_full)} = C",
    )

    values = _particular_values(conditions)
    if values is not None:
        x0, y0 = values
        constant = sp.simplify(potential_full.subs({x: x0, y: y0}))
        builder.add(
            "Aplicar la condición inicial",
            rf"C = F({sp.latex(x0)}, {sp.latex(y0)}) = {sp.latex(constant)}",
            "Se evalúa la función potencial en la condición inicial para obtener el valor de C.",
            ascii_expr=f"C = {sp.pretty(constant)}",
        )
    _add_particular_step(builder, symbolic_result)


def _add_homogeneous_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None",
    conditions: Any,
) -> None:
    _add_identification(builder, rhs, "homogeneous")
    transformed = sp.simplify(rhs.subs(y, _U * x))
    builder.add(
        "Aplicar la sustitución y = ux",
        rf"u + x\frac{{du}}{{dx}} = {sp.latex(transformed)}",
        "En una EDO homogénea se sustituye y = ux; entonces dy/dx = u + x du/dx.",
        ascii_expr=f"u + x du/dx = {sp.pretty(transformed)}",
    )

    separable_rhs = sp.simplify(transformed - _U)
    builder.add(
        "Separar variables en u y x",
        rf"\frac{{du}}{{{sp.latex(separable_rhs)}}} = \frac{{dx}}{{x}}",
        "Se agrupan los términos en u y en x para integrar cada lado por separado.",
        ascii_expr=f"du/({sp.pretty(separable_rhs)}) = dx/x",
    )

    left = _safe_integrate(1 / separable_rhs, _U)
    right = _safe_integrate(1 / x, x)
    builder.add(
        "Integrar ambos lados",
        f"{sp.latex(left)} = {sp.latex(right)} + C",
        "Se integra respecto a u y respecto a x, añadiendo la constante de integración.",
        ascii_expr=f"{sp.pretty(left)} = {sp.pretty(right)} + C",
    )

    general = _solution_rhs(symbolic_result, "general_solution")
    if general is not None:
        builder.add(
            "Volver a las variables originales",
            sp.latex(sp.Eq(y, general)),
            "Se sustituye u = y/x y se despeja y para obtener la solución general.",
            ascii_expr=f"y = {sp.pretty(general)}",
        )
    _add_condition_step(builder, general, conditions)
    _add_particular_step(builder, symbolic_result)


def _add_numeric_steps(
    builder: _StepBuilder,
    rhs: sp.Expr,
    conditions: Any,
    numeric_result: "NumericResult | None",
) -> None:
    values = _particular_values(conditions)
    x_min = getattr(conditions, "x_min", -5.0) if conditions is not None else -5.0
    x_max = getattr(conditions, "x_max", 5.0) if conditions is not None else 5.0
    n_points = 500
    if numeric_result is not None and getattr(numeric_result, "x_arr", None) is not None:
        n_points = max(n_points, len(numeric_result.x_arr))

    builder.add(
        "Método numérico: Runge-Kutta RK45",
        rf"\frac{{dy}}{{dx}} = {sp.latex(rhs)}",
        "Al no disponer de solución simbólica se resuelve la EDO con scipy.integrate.solve_ivp.",
        ascii_expr=f"dy/dx = {sp.pretty(rhs)}",
    )
    builder.add(
        "Discretizar el intervalo",
        rf"x \in [{sp.latex(x_min)}, {sp.latex(x_max)}], \quad N = {n_points}",
        "Se construye una malla de al menos 500 puntos para garantizar una curva suave.",
        ascii_expr=f"x in [{x_min}, {x_max}], N = {n_points}",
    )
    if values is not None:
        x0, y0 = values
        builder.add(
            "Establecer la condición inicial",
            rf"y({sp.latex(x0)}) = {sp.latex(y0)}",
            "El integrador parte del punto inicial indicado por el usuario.",
            ascii_expr=f"y({x0}) = {y0}",
        )
    builder.add(
        "Evaluar f(x, y) y avanzar el integrador",
        r"y_{n+1} = y_n + h\,\Phi(x_n, y_n, h)",
        "En cada paso RK45 evalúa f(x,y) varias veces y combina las pendientes para avanzar la solución.",
        detail="La evaluación de f se realiza en cada punto de la malla.",
    )
    if numeric_result is not None:
        status = "exitosa" if numeric_result.success else "fallida"
        builder.add(
            "Resultado del integrador",
            rf"\text{{Solución numérica {status}}}",
            numeric_result.message or "El integrador finalizó.",
            detail=f"Puntos calculados: {n_points}.",
            ascii_expr=f"Solución numérica {status}: {numeric_result.message}",
        )


def _render_ascii(steps: list[SolutionStep]) -> str:
    lines: list[str] = []
    for step in steps:
        lines.append(f"Paso {step.number}: {step.operation}")
        lines.append(f"  {step.ascii_expr or step.latex_expr}")
        lines.append(f"  Justificación: {step.justification}")
        if step.detail:
            lines.append(f"  Detalle: {step.detail}")
        lines.append("")
    return "\n".join(lines).strip()


def generate_steps(
    rhs: sp.Expr,
    symbolic_result: "SymbolicResult | None" = None,
    conditions: Any = None,
    ode_type: str | None = None,
    numeric_result: "NumericResult | None" = None,
) -> StepByStepResult:
    """Genera el procedimiento paso a paso para ``rhs``.

    Si ``symbolic_result`` falló y se proporciona ``numeric_result``, se
    generan los pasos del método numérico.
    """

    if ode_type is None:
        ode_type = classify_ode(rhs)

    builder = _StepBuilder()
    symbolic_failed = symbolic_result is not None and symbolic_result.error is not None

    if numeric_result is not None and (symbolic_result is None or symbolic_failed):
        _add_numeric_steps(builder, rhs, conditions, numeric_result)
        effective_type = "numeric"
    elif ode_type == "separable":
        _add_separable_steps(builder, rhs, symbolic_result, conditions)
        effective_type = ode_type
    elif ode_type == "linear":
        _add_linear_steps(builder, rhs, symbolic_result, conditions)
        effective_type = ode_type
    elif ode_type == "bernoulli":
        _add_bernoulli_steps(builder, rhs, symbolic_result, conditions)
        effective_type = ode_type
    elif ode_type == "exact":
        _add_exact_steps(builder, rhs, symbolic_result, conditions)
        effective_type = ode_type
    elif ode_type == "homogeneous":
        _add_homogeneous_steps(builder, rhs, symbolic_result, conditions)
        effective_type = ode_type
    else:
        _add_identification(builder, rhs, ode_type)
        general = _solution_rhs(symbolic_result, "general_solution")
        if general is not None:
            builder.add(
                "Resolver con dsolve",
                sp.latex(sp.Eq(y, general)),
                "SymPy encontró una solución simbólica mediante sus métodos generales.",
                ascii_expr=f"y = {sp.pretty(general)}",
            )
        else:
            builder.add(
                "Sin método elemental disponible",
                rf"\frac{{dy}}{{dx}} = {sp.latex(rhs)}",
                "No se reconoció un método elemental ni una solución simbólica; se recomienda usar la solución numérica.",
                ascii_expr=f"dy/dx = {sp.pretty(rhs)}",
            )
        effective_type = ode_type

    steps = builder.steps
    return StepByStepResult(
        steps=steps,
        ode_type=effective_type,
        ascii_text=_render_ascii(steps),
    )


__all__ = [
    "SolutionStep",
    "StepByStepResult",
    "classify_ode",
    "generate_steps",
]
