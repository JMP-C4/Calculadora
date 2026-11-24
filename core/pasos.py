"""Explicaciones paso a paso en LaTeX para la pestaña Resolver y Aprender."""

from __future__ import annotations

import sympy as sp

from odecalc.classify.classifier import bernoulli_coeffs, exact_parts, linear_coeffs, separable_parts
from odecalc.models import SolveResult
from odecalc.symbols import DY, X, Y

from core.clasificador import clasificar
from core.parser import parsear
from core.tipos import Paso, ResultadoNumerico


def pasos_desde_motor(motor: SolveResult) -> list[Paso]:
    """Convierte los pasos del motor en :class:`core.tipos.Paso`."""

    pasos: list[Paso] = []
    for paso in motor.steps:
        pasos.append(
            Paso(
                titulo=paso.title,
                explicacion=paso.explanation,
                latex=paso.latex,
            )
        )
    return pasos


def pasos_numericos(resultado: ResultadoNumerico) -> list[Paso]:
    """Explica el procedimiento numérico cuando no hay forma cerrada."""

    return [
        Paso(
            titulo="No hay forma cerrada verificable",
            explicacion=(
                "El motor simbólico no obtuvo una expresión que pudiera "
                "certificarse. Se integra la EDO numéricamente para estudiar "
                "su comportamiento."
            ),
            latex=r"\frac{dy}{dx} = f(x,y), \qquad y(x_0)=y_0",
        ),
        Paso(
            titulo="Discretización",
            explicacion=(
                "Se elige una malla de puntos y se avanza con el método "
                f"{resultado.metodo or 'RK45'}. Un paso menor reduce el error "
                "de truncamiento, a costa de más evaluaciones de f."
            ),
            latex=(
                r"y_{n+1} = y_n + \int_{x_n}^{x_{n+1}} f(t,y(t))\,dt"
            ),
        ),
        Paso(
            titulo="Control del error",
            explicacion=(
                "Los integradores adaptativos comparan dos estimaciones y "
                "ajustan el paso. Si aparece rigidez, se cambia a BDF o Radau."
            ),
            latex=(
                r"\left|y_{n+1}^{(p)} - y_{n+1}^{(c)}\right| < \mathrm{tol}"
            ),
        ),
        Paso(
            titulo="Resultado numérico",
            explicacion=resultado.mensaje or "Integración finalizada.",
            latex=(
                rf"x \in [{resultado.x[0]:.6g}, {resultado.x[-1]:.6g}]"
                if resultado.x.size
                else r"\text{sin puntos}"
            ),
        ),
    ]


def _pasos_separables(rhs: sp.Expr, solucion_latex: str) -> list[Paso]:
    partes = separable_parts(rhs)
    if partes is None:
        return _pasos_genericos(rhs, solucion_latex)
    g_expr, h_expr = partes
    return [
        Paso(
            titulo="Identificar la estructura separable",
            explicacion=(
                "El lado derecho se factoriza como un producto de una función "
                "de x por una función de y. Esto permite separar las variables."
            ),
            latex=rf"y' = {sp.latex(g_expr)} \cdot {sp.latex(h_expr)}",
        ),
        Paso(
            titulo="Separar las variables",
            explicacion=(
                "Dividimos entre h(y) y multiplicamos por dx. Cada lado queda "
                "con una sola variable."
            ),
            latex=(
                rf"\frac{{dy}}{{{sp.latex(h_expr)}}} = "
                rf"{sp.latex(g_expr)}\,dx"
            ),
        ),
        Paso(
            titulo="Integrar ambos lados",
            explicacion=(
                "Integramos respecto de su variable e incorporamos una única "
                "constante de integración C."
            ),
            latex=(
                rf"\int \frac{{dy}}{{{sp.latex(h_expr)}}} = "
                rf"\int {sp.latex(g_expr)}\,dx + C"
            ),
        ),
        Paso(
            titulo="Despejar la solución",
            explicacion=(
                "Si es posible, se despeja y. Si no, se conserva la solución "
                "implícita F(x,y)=C, que también es una respuesta válida."
            ),
            latex=solucion_latex or r"F(x,y) = C",
        ),
    ]


def _pasos_lineales(rhs: sp.Expr, solucion_latex: str) -> list[Paso]:
    coeficientes = linear_coeffs(rhs)
    if coeficientes is None:
        return _pasos_genericos(rhs, solucion_latex)
    p_expr, q_expr = coeficientes
    return [
        Paso(
            titulo="Escribir la forma lineal estándar",
            explicacion=(
                "Toda EDO lineal de primer orden se escribe como "
                "y' + P(x)y = Q(x). Identificamos P y Q."
            ),
            latex=(
                rf"y' + \left({sp.latex(p_expr)}\right)y = "
                rf"{sp.latex(q_expr)}"
            ),
        ),
        Paso(
            titulo="Calcular el factor integrante",
            explicacion=(
                "El factor integrante μ(x) = exp(∫P dx) convierte el lado "
                "izquierdo en la derivada de un producto."
            ),
            latex=rf"\mu(x) = e^{{\int {sp.latex(p_expr)}\,dx}}",
        ),
        Paso(
            titulo="Multiplicar por μ(x)",
            explicacion=(
                "Al multiplicar toda la ecuación por μ, el miembro izquierdo "
                "es exactamente (μy)'."
            ),
            latex=rf"\left(\mu(x)\,y\right)' = \mu(x)\,{sp.latex(q_expr)}",
        ),
        Paso(
            titulo="Integrar y despejar y",
            explicacion=(
                "Integramos ambos lados respecto de x y dividimos entre μ(x), "
                "que no se anula en el dominio real."
            ),
            latex=solucion_latex or r"y = \frac{1}{\mu(x)}\left(\int \mu Q\,dx + C\right)",
        ),
    ]


def _pasos_exactas(ecuacion, solucion_latex: str) -> list[Paso]:
    partes = exact_parts(ecuacion.parsed)
    if partes is None:
        return _pasos_genericos(ecuacion.rhs, solucion_latex)
    m_expr, n_expr = partes
    return [
        Paso(
            titulo="Escribir en forma diferencial",
            explicacion=(
                "Identificamos M(x,y) como el coeficiente de dx y N(x,y) como "
                "el coeficiente de dy."
            ),
            latex=rf"{sp.latex(m_expr)}\,dx + {sp.latex(n_expr)}\,dy = 0",
        ),
        Paso(
            titulo="Comprobar la exactitud",
            explicacion=(
                "La ecuación es exacta si las derivadas cruzadas coinciden. "
                "En ese caso existe una función potencial F(x,y)."
            ),
            latex=(
                rf"\frac{{\partial M}}{{\partial y}} = "
                rf"\frac{{\partial N}}{{\partial x}}"
            ),
        ),
        Paso(
            titulo="Integrar M respecto de x",
            explicacion=(
                "La constante de integración puede depender de y: se escribe "
                "como g(y)."
            ),
            latex=rf"F(x,y) = \int {sp.latex(m_expr)}\,dx + g(y)",
        ),
        Paso(
            titulo="Determinar g(y)",
            explicacion=(
                "Derivamos F respecto de y, igualamos con N y despejamos g'(y)."
            ),
            latex=rf"\frac{{\partial F}}{{\partial y}} = {sp.latex(n_expr)}",
        ),
        Paso(
            titulo="Escribir la solución general",
            explicacion=(
                "Las soluciones son las curvas de nivel del potencial: F(x,y)=C."
            ),
            latex=solucion_latex or r"F(x,y) = C",
        ),
    ]


def _pasos_bernoulli(rhs: sp.Expr, solucion_latex: str) -> list[Paso]:
    coeficientes = bernoulli_coeffs(rhs)
    if coeficientes is None:
        return _pasos_genericos(rhs, solucion_latex)
    p_expr, q_expr, n_expr = coeficientes
    return [
        Paso(
            titulo="Reconocer la ecuación de Bernoulli",
            explicacion=(
                "Tiene la forma y' + P(x)y = Q(x)yⁿ con n distinto de 0 y 1."
            ),
            latex=(
                rf"y' + \left({sp.latex(p_expr)}\right)y = "
                rf"\left({sp.latex(q_expr)}\right)y^{{{sp.latex(n_expr)}}}"
            ),
        ),
        Paso(
            titulo="Aplicar la sustitución",
            explicacion=(
                "El cambio v = y^(1-n) transforma la ecuación de Bernoulli en "
                "una ecuación lineal en v."
            ),
            latex=rf"v = y^{{1-{sp.latex(n_expr)}}}, \qquad v' = (1-n)y^{{-n}}y'",
        ),
        Paso(
            titulo="Resolver la ecuación lineal en v",
            explicacion=(
                "Se aplica el factor integrante a la ecuación lineal resultante."
            ),
            latex=rf"v' + (1-n)P(x)v = (1-n)Q(x)",
        ),
        Paso(
            titulo="Volver a la variable original",
            explicacion=(
                "Se despeja y a partir de v = y^(1-n). Hay que revisar la rama "
                "y el signo al tomar raíces."
            ),
            latex=solucion_latex or r"y^{1-n} = v(x)",
        ),
    ]


def _pasos_genericos(rhs: sp.Expr, solucion_latex: str) -> list[Paso]:
    return [
        Paso(
            titulo="Analizar la ecuación",
            explicacion=(
                "Se busca una estructura conocida (separable, lineal, exacta, "
                "homogénea o Bernoulli) antes de intentar un método general."
            ),
            latex=rf"y' = {sp.latex(rhs)}",
        ),
        Paso(
            titulo="Elegir una estrategia",
            explicacion=(
                "Si no hay una estructura elemental, se usa el resolvedor "
                "simbólico general y se verifica el residuo antes de mostrar "
                "la respuesta."
            ),
            latex=r"\text{clasificar} \rightarrow \text{resolver} \rightarrow \text{verificar}",
        ),
        Paso(
            titulo="Solución propuesta",
            explicacion=(
                "Toda solución se sustituye en la EDO original para comprobar "
                "que el residuo es nulo."
            ),
            latex=solucion_latex or r"F(x,y) = C",
        ),
    ]


def pasos_para_tipo(ecuacion, motor: SolveResult | None = None) -> list[Paso]:
    """Genera pasos didácticos según el tipo, usando la solución del motor."""

    if motor is not None:
        pasos = pasos_desde_motor(motor)
        if pasos:
            return pasos
    solucion = ""
    if motor is not None:
        solucion = (motor.particular or motor.general).latex if (motor.particular or motor.general) else ""
    tipos = {tipo.id for tipo in clasificar(ecuacion)}
    if "separable" in tipos:
        return _pasos_separables(ecuacion.rhs, solucion)
    if "linear" in tipos:
        return _pasos_lineales(ecuacion.rhs, solucion)
    if "exact" in tipos:
        return _pasos_exactas(ecuacion, solucion)
    if "bernoulli" in tipos:
        return _pasos_bernoulli(ecuacion.rhs, solucion)
    return _pasos_genericos(ecuacion.rhs, solucion)


def generar_pasos(
    texto: str,
    x0: float | None = None,
    y0: float | None = None,
    *,
    timeout: float | None = 10.0,
) -> list[Paso]:
    """API cómoda para obtener los pasos de una ecuación."""

    from core.solver_simbolico import resolver_motor

    ecuacion = parsear(texto)
    try:
        motor = resolver_motor(
            texto, x0=x0, y0=y0, timeout=timeout, calcular_numerico=False
        )
        return pasos_para_tipo(ecuacion, motor)
    except Exception:
        return pasos_para_tipo(ecuacion, None)


__all__ = [
    "pasos_desde_motor",
    "pasos_numericos",
    "pasos_para_tipo",
    "generar_pasos",
]
