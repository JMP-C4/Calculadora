"""Constructores compartidos de pasos atómicos, reglas de signos y fórmulas.

Genera explicaciones detalladas desde operaciones elementales (ley de signos
como menos por menos = más, transposición de términos, cancelación de factores,
propiedad distributiva) hasta reglas de derivación e integración, selección del
método y comprobación final del residuo.
"""

from __future__ import annotations

import math

import sympy as sp

from odecalc.methods.common import make_step, safe_simplify
from odecalc.models import Solution, Step, Verification
from odecalc.symbols import C, DY, X, Y, lambdify_modules


class StepBuilder:
    """Acumulador secuencial de objetos :class:`Step` numerados desde 1."""

    def __init__(self) -> None:
        self._steps: list[Step] = []

    @property
    def steps(self) -> list[Step]:
        return list(self._steps)

    def add(
        self,
        title: str,
        latex: str,
        explanation: str,
        ascii_expr: str | None = None,
    ) -> Step:
        step = make_step(
            len(self._steps) + 1,
            title,
            latex,
            explanation,
            ascii_expr=ascii_expr,
        )
        self._steps.append(step)
        return step

    def extend_renumbered(self, extra_steps: list[Step]) -> None:
        for step in extra_steps:
            self.add(
                step.title,
                step.latex,
                step.explanation,
                ascii_expr=step.ascii,
            )


_EXPENSIVE_ATOMS = (sp.Integral, sp.Si, sp.Ci, sp.Ei, sp.erf, sp.erfi, sp.Piecewise)


def _fast_simplify(expr: sp.Expr) -> sp.Expr:
    """Simplifica expresiones ligeras sin disparar simplificaciones costosas en funciones especiales."""

    if expr.has(*_EXPENSIVE_ATOMS):
        return expr
    return safe_simplify(expr)


def _has_minus_sign(expr: sp.Expr) -> bool:
    """Detecta si la representación principal de ``expr`` lleva signo negativo."""

    expr = _fast_simplify(expr)
    if expr == 0:
        return False
    if expr.is_number:
        try:
            val = complex(sp.N(expr))
            if abs(val.imag) < 1e-12 and val.real < 0:
                return True
        except Exception:
            pass
    tex = sp.latex(expr).lstrip()
    return tex.startswith("-")


def _wrap_factor_latex(expr: sp.Expr) -> str:
    tex = sp.latex(expr)
    if isinstance(expr, sp.Add) or tex.lstrip().startswith("-"):
        return rf"\left({tex}\right)"
    return tex


def _abs_part_latex(expr: sp.Expr) -> str:
    neg = _fast_simplify(-expr)
    tex = sp.latex(neg)
    return rf"\left({tex}\right)" if isinstance(neg, sp.Add) else tex


def describe_sign_product(left: sp.Expr, right: sp.Expr) -> str | None:
    """Explica la ley de signos aplicada al multiplicar ``left * right``."""

    left_s = _fast_simplify(left)
    right_s = _fast_simplify(right)
    if left_s == 0 or right_s == 0:
        return "Cualquier factor multiplicado por $0$ da $0$ ($a \\cdot 0 = 0$)."
    left_neg = _has_minus_sign(left_s)
    right_neg = _has_minus_sign(right_s)
    if left_neg and right_neg:
        a_pos = _fast_simplify(-left_s)
        b_pos = _fast_simplify(-right_s)
        prod_pos = _fast_simplify(left_s * right_s)
        return (
            "Se aplica la regla de los signos (menos por menos da más: "
            f"$(-) \\cdot (-) = +$): "
            rf"$\left({sp.latex(left_s)}\right)\cdot\left({sp.latex(right_s)}\right)"
            rf" = +\left({sp.latex(a_pos)}\right)\cdot\left({sp.latex(b_pos)}\right)"
            rf" = {sp.latex(prod_pos)}$."
        )
    if left_neg or right_neg:
        prod = _fast_simplify(left_s * right_s)
        return (
            "Por la regla de los signos (menos por más o más por menos da menos: "
            "$(-) \\cdot (+) = -$), el producto conserva el signo negativo resultante: "
            rf"$\left({sp.latex(left_s)}\right)\cdot\left({sp.latex(right_s)}\right) = {sp.latex(prod)}$."
        )
    return None


def describe_double_negative(base_expr: sp.Expr, sub_expr: sp.Expr) -> str | None:
    """Explica ``base - (-B) = base + B`` cuando ``sub_expr`` es negativo."""

    sub_s = _fast_simplify(sub_expr)
    if not _has_minus_sign(sub_s):
        return None
    pos_b = _fast_simplify(-sub_s)
    total = _fast_simplify(base_expr - sub_s)
    return (
        "Aparece un doble signo negativo ($-(-B)$): por la regla menos por menos "
        "da más, restar una expresión negativa equivale a sumarla: "
        rf"${sp.latex(base_expr)} - \left({sp.latex(sub_s)}\right) = "
        rf"{sp.latex(base_expr)} + {sp.latex(pos_b)} = {sp.latex(total)}$."
    )


def add_product_atomic_steps(
    builder: StepBuilder,
    left: sp.Expr,
    right: sp.Expr,
    result: sp.Expr,
    *,
    title: str,
    lhs_latex: str,
    intro_explanation: str,
) -> None:
    """Añade paso(s) detallando producto, regla de signos, distribución y cancelaciones."""

    left_s = _fast_simplify(left)
    right_s = _fast_simplify(right)
    res_s = _fast_simplify(result)
    raw_tex = rf"{_wrap_factor_latex(left_s)} \cdot {_wrap_factor_latex(right_s)}"
    has_special = left_s.has(*_EXPENSIVE_ATOMS) or right_s.has(*_EXPENSIVE_ATOMS) or res_s.has(*_EXPENSIVE_ATOMS)
    expanded = left_s * right_s if has_special else sp.expand(left_s * right_s)

    notes: list[str] = [intro_explanation]
    sign_note = describe_sign_product(left_s, right_s)
    if sign_note:
        notes.append(sign_note)

    chain = [lhs_latex, raw_tex]
    if not has_special and (left_s.is_Add or right_s.is_Add) and sp.latex(expanded) != sp.latex(res_s):
        notes.append(
            "Se distribuye el factor sobre cada sumando usando $A(B + C) = AB + AC$."
        )
        chain.append(sp.latex(expanded))
    elif (left_s.is_Add or right_s.is_Add) and res_s != 0:
        notes.append(
            "Se distribuye el factor sobre cada término ($A(B + C) = AB + AC$) y se simplifica."
        )

    cancelled = False
    if not has_special:
        num_l, den_l = sp.fraction(sp.together(left_s))
        num_r, den_r = sp.fraction(sp.together(right_s))
        if den_l != 1 or den_r != 1:
            raw_den = _fast_simplify(den_l * den_r)
            res_den = sp.fraction(sp.together(res_s))[1]
            cancelled = _fast_simplify(raw_den - res_den) != 0
    if cancelled and left_s != 0 and right_s != 0:
        notes.append(
            "Al multiplicar fracciones $\\frac{a}{b}\\cdot\\frac{c}{d} = \\frac{ac}{bd}$, "
            "se simplifican los factores comunes entre numerador y denominador usando "
            "la ley de exponentes $\\frac{u^m}{u^n} = u^{m-n}$."
        )

    final_tex = sp.latex(res_s)
    if chain[-1] != final_tex:
        chain.append(final_tex)
    latex_eq = " = ".join(chain)
    builder.add(title, latex_eq, " ".join(notes))


def add_transposition_step(
    builder: StepBuilder,
    lhs_orig: sp.Expr | str,
    rhs_orig: sp.Expr,
    moved_term: sp.Expr,
    final_latex: str,
    *,
    title: str = "Reordenar términos (transposición de signo)",
    from_left: bool = False,
) -> None:
    """Explica por qué cambia el signo al pasar un término al otro lado de la igualdad."""

    moved_s = safe_simplify(moved_term)
    if moved_s == 0:
        return
    neg_moved = safe_simplify(-moved_s)
    lhs_tex = lhs_orig if isinstance(lhs_orig, str) else sp.latex(lhs_orig)
    lado_origen = "izquierdo" if from_left else "derecho"
    lado_destino = "derecho" if from_left else "izquierdo"
    if _has_minus_sign(moved_s):
        pos_tex = _abs_part_latex(moved_s)
        exp = (
            f"En ${lhs_tex} = {sp.latex(rhs_orig)}$, el término ${sp.latex(moved_s)}$ en el miembro {lado_origen} es "
            f"negativo. Sumamos su opuesto $+{pos_tex}$ a ambos lados de la igualdad; "
            f"por regla de signos ($-(-A) = +A$), al cruzar al miembro {lado_destino} cambia a signo $+$."
        )
    else:
        exp = (
            f"En ${lhs_tex} = {sp.latex(rhs_orig)}$, el término $+{sp.latex(moved_s)}$ es positivo en el "
            f"miembro {lado_origen}. Restamos ${sp.latex(moved_s)}$ en ambos lados de la igualdad "
            f"(${sp.latex(moved_s)} - {sp.latex(moved_s)} = 0$), de modo que pasa al miembro {lado_destino} "
            f"con signo negativo (${sp.latex(neg_moved)}$)."
        )
    builder.add(title, final_latex, exp)


def explain_derivative_rules(expr: sp.Expr, var: sp.Symbol, label: str = "f") -> str:
    """Describe las reglas de derivación empleadas al derivar ``expr`` respecto a ``var``."""

    expr_s = _fast_simplify(expr)
    if expr_s == 0 or not expr_s.has(var):
        return (
            f"Al derivar respecto a ${sp.latex(var)}$, los términos que no contienen "
            f"${sp.latex(var)}$ actúan como constantes y su derivada es $0$."
        )

    rules: list[str] = []
    terms = sp.Add.make_args(expr_s)
    if len(terms) > 1:
        rules.append(
            "Por linealidad de la derivada, se deriva término a término: "
            "$(f \\pm g)' = f' \\pm g'$."
        )
    for term in terms:
        if not term.has(var):
            rules.append(
                f"El término constante ${sp.latex(term)}$ respecto a ${sp.latex(var)}$ tiene derivada $0$."
            )
            continue
        coeff, rest = term.as_independent(var, as_Add=False)
        if coeff != 1 and rest != 1 and _has_minus_sign(coeff):
            if rest.has(sp.cos):
                rules.append(
                    "Al derivar el término con factor negativo y $\\cos$, aparecen dos signos menos "
                    "($-\\sin$ por coeficiente negativo) y menos por menos da más."
                )
        if rest == var:
            rules.append(
                f"En ${sp.latex(term)}$, se usa $\\frac{{d}}{{d{sp.latex(var)}}}(k\\,{sp.latex(var)}) = k$."
            )
        elif rest.is_Pow and rest.base == var:
            exp_val = rest.exp
            if _has_minus_sign(exp_val):
                rules.append(
                    f"Para exponente negativo ${sp.latex(rest)}$, se aplica la regla de la potencia "
                    f"$\\frac{{d}}{{du}}(u^n) = n u^{{n-1}}$ (el signo negativo de $n = {sp.latex(exp_val)}$ multiplica al coeficiente)."
                )
            else:
                rules.append(
                    f"Para ${sp.latex(rest)}$, se aplica la regla de la potencia $\\frac{{d}}{{du}}(u^n) = n u^{{n-1}}$."
                )
        elif term.has(sp.exp):
            rules.append("Para la exponencial se usa $\\frac{d}{du}(e^{g(u)}) = g'(u)\\,e^{g(u)}$ (regla de la cadena).")
        elif term.has(sp.log):
            rules.append("Para el logaritmo se usa $\\frac{d}{du}(\\ln g(u)) = \\frac{g'(u)}{g(u)}$.")
        elif term.has(sp.sin):
            rules.append("Se usa $\\frac{d}{du}(\\sin g(u)) = g'(u)\\cos g(u)$.")
        elif term.has(sp.cos):
            rules.append("Se usa $\\frac{d}{du}(\\cos g(u)) = -g'(u)\\sin g(u)$ (nótese el signo negativo).")
        elif term.has(sp.atan):
            rules.append("Se usa $\\frac{d}{du}(\\arctan u) = \\frac{1}{1+u^2}$ y regla de la cadena.")
        elif rest.is_Mul:
            rules.append("Se aplica regla del producto $(uv)' = u'v + uv'$ o regla de la cadena.")

    if not rules:
        rules.append(
            f"Se aplica la regla de la cadena y derivación elemental respecto a ${sp.latex(var)}$."
        )
    # Preservar el orden eliminando repeticiones.
    unique = list(dict.fromkeys(rules))
    return f"Derivación de ${label}$ respecto a ${sp.latex(var)}$: " + " ".join(unique[:4])


def explain_integration_rules(
    integrand: sp.Expr,
    var: sp.Symbol,
    integral_result: sp.Expr,
) -> str:
    """Describe las fórmulas de integración aplicadas término a término."""

    expr_s = _fast_simplify(integrand)
    v_tex = sp.latex(var)
    if integral_result.has(sp.Integral):
        return (
            f"La integral $\\int {sp.latex(expr_s)}\\,d{v_tex}$ no admite una primitiva elemental "
            f"en funciones básicas, por lo que se conserva explícitamente en ${v_tex}$."
        )
    if expr_s == 0:
        return f"La integral de cero es una constante: $\\int 0\\,d{v_tex} = C$."

    rules: list[str] = []
    terms = sp.Add.make_args(sp.expand(expr_s) if expr_s.is_Add else expr_s)
    if len(terms) > 1:
        rules.append(
            "Por linealidad de la integral, se integra suma a suma: $\\int(f + g) = \\int f + \\int g$."
        )

    for term in terms:
        coeff, rest = term.as_independent(var, as_Add=False)
        if rest == 1:
            rules.append(
                f"Para una constante $k = {sp.latex(coeff)}$, se usa $\\int k\\,d{v_tex} = k\\,{v_tex}$."
            )
            continue
        if rest == var:
            rules.append(
                f"Para potencia lineal ${v_tex}^1$, $\\int {v_tex}\\,d{v_tex} = \\frac{{{v_tex}^2}}{{2}}$."
            )
            continue
        if rest == 1 / var:
            rules.append(
                f"Para el recíproco $\\frac{{1}}{{{v_tex}}} = {v_tex}^{{-1}}$, se usa la fórmula logarítmica "
                f"$\\int \\frac{{1}}{{{v_tex}}}\\,d{v_tex} = \\ln|{v_tex}|$."
            )
            continue
        if rest.is_Pow and rest.base == var and rest.exp.is_number:
            n_val = rest.exp
            rules.append(
                f"Para potencia ${sp.latex(rest)}$, se aplica $\\int u^n\\,du = \\frac{{u^{{n+1}}}}{{n+1}}$ "
                f"con $n = {sp.latex(n_val)}$ (sumar $1$ al exponente y dividir por $n+1 = {sp.latex(safe_simplify(n_val + 1))}$)."
            )
            continue
        if rest.has(sp.exp):
            rules.append(
                "Para la exponencial se usa $\\int e^{a u}\\,du = \\frac{1}{a}e^{a u}$ "
                "(dividir entre un exponente negativo cambia o cancela el signo por regla de signos)."
            )
        elif rest.has(sp.sin):
            rules.append(
                "Para el seno se usa $\\int \\sin(au)\\,du = -\\frac{1}{a}\\cos(au)$ "
                "(si el coeficiente previo también es negativo, $-\\cdot- = +$)."
            )
        elif rest.has(sp.cos):
            rules.append("Para el coseno se usa $\\int \\cos(au)\\,du = \\frac{1}{a}\\sin(au)$.")
        elif any(isinstance(arg, sp.Pow) and arg.exp == -1 and arg.base.is_Add for arg in sp.preorder_traversal(rest)):
            rules.append(
                "Para denominadores cuadráticos o lineales se aplica sustitución logarítmica "
                "($\\int \\frac{du}{u} = \\ln|u|$) o arcotangente ($\\int \\frac{du}{u^2+a^2} = \\frac{1}{a}\\arctan(u/a)$)."
            )

    if integral_result.has(sp.erf, sp.erfi, sp.Ei, sp.Si, sp.Ci):
        rules.append(
            "La primitiva se expresa mediante una función especial estándar ($\\operatorname{erf}$, "
            "$\\operatorname{Ei}$, $\\operatorname{Si}$ o $\\operatorname{Ci}$)."
        )

    if not rules:
        rules.append(
            "Se aplican reglas de sustitución o integración por partes $\\int u\\,dv = uv - \\int v\\,du$."
        )
    unique = list(dict.fromkeys(rules))
    return "Fórmula(s) de integración aplicadas: " + " ".join(unique[:4])


def _format_num_latex(value: float) -> str:
    if isinstance(value, (int, sp.Integer)) or (isinstance(value, float) and value.is_integer()):
        return str(int(round(value)))
    return sp.latex(sp.nsimplify(value, rational=False)) if abs(value) <= 1e6 else f"{value:g}"


def _constante_en_particular(
    expr_general: sp.Expr,
    particular: sp.Expr,
    const_sym: sp.Symbol,
    candidatas: list[sp.Expr],
    x0: float,
) -> sp.Expr | None:
    """Devuelve la constante que reproduce la rama particular seleccionada.

    ``apply_initial_conditions`` elige entre las ramas reales la que satisface
    también la EDO; resolver la condición inicial de forma aislada puede dar
    otra raíz válida en el punto inicial pero inválida en la ecuación.  Por
    eso se comparan las candidatas con la solución particular ya verificada.
    """

    evaluadas: list[tuple[sp.Expr, sp.Expr]] = []
    for valor in candidatas:
        try:
            if valor.has(X) or valor.has(Y):
                continue
            substituida = _fast_simplify(expr_general.subs(const_sym, valor))
        except Exception:
            continue
        evaluadas.append((valor, substituida))
        try:
            if _fast_simplify(substituida - particular) == 0:
                return valor
        except Exception:
            pass

    # Las soluciones con integrales o reparameterizaciones exponenciales no
    # siempre se simplifican a la misma forma; se comparan en unos puntos.
    try:
        f_particular = sp.lambdify(X, particular, modules=lambdify_modules())
    except Exception:
        return None
    muestras = [x0 + desplazamiento for desplazamiento in (0.25, 0.75, 1.5, 3.0)]
    for valor, substituida in evaluadas:
        try:
            f_candidata = sp.lambdify(X, substituida, modules=lambdify_modules())
            if all(
                abs(complex(f_candidata(punto)) - complex(f_particular(punto))) < 1e-7
                for punto in muestras
            ):
                return valor
        except Exception:
            continue
    return None


def _build_pvi_steps(
    builder: StepBuilder,
    general: Solution,
    particular: Solution,
    x0: float,
    y0: float,
    *,
    used_singular: bool = False,
) -> None:
    """Añade pasos detallados mostrando cómo se calcula $C$ a partir de $y(x_0) = y_0$."""

    x0_sym = sp.nsimplify(x0, rational=False)
    y0_sym = sp.nsimplify(y0, rational=False)
    x0_tex = sp.latex(x0_sym)
    y0_tex = sp.latex(y0_sym)

    if used_singular:
        builder.add(
            "Comprobar la condición inicial en la solución singular",
            particular.latex,
            f"Al evaluar la condición inicial $y({x0_tex}) = {y0_tex}$ en la solución general no se "
            "recupera este punto o pertenece a la solución singular/de equilibrio. "
            f"La solución singular ${particular.latex}$ satisface $y({x0_tex}) = {y0_tex}$.",
        )
        return

    if not general.expr.free_symbols - {X, Y}:
        builder.add(
            "Verificar la condición inicial",
            particular.latex,
            f"La solución no contiene constante libre $C$; se comprueba directamente que cumple "
            f"$y({x0_tex}) = {y0_tex}$.",
        )
        return

    const_sym = general.constant if general.constant is not None else C
    real_c: sp.Expr | None = None
    if general.is_explicit:
        sub_rhs = safe_simplify(general.expr.subs(X, x0_sym))
        eq_c_tex = rf"{y0_tex} = {sp.latex(sub_rhs)}"
        builder.add(
            f"Sustituir la condición inicial y({x0:g}) = {y0:g}",
            eq_c_tex,
            f"Para hallar la constante arbitraria ${sp.latex(const_sym)}$ imponemos el problema de valor "
            f"inicial (PVI): reemplazamos $x = {x0_tex}$ e $y = {y0_tex}$ en la solución general "
            f"${general.latex}$.",
        )
        c_vals = []
        try:
            c_vals = [safe_simplify(item) for item in sp.solve(sp.Eq(sub_rhs, y0_sym), const_sym)]
        except Exception:
            c_vals = []
        real_vals: list[sp.Expr] = []
        for val in c_vals:
            if not val.has(const_sym):
                try:
                    c_num = complex(sp.N(val))
                    if abs(c_num.imag) < 1e-9 and math.isfinite(c_num.real):
                        real_vals.append(val)
                except Exception:
                    pass
        real_c = _constante_en_particular(
            general.expr, particular.expr, const_sym, real_vals, x0
        )
        if real_c is None and len(real_vals) == 1:
            real_c = real_vals[0]
        if real_c is not None:
            sign_c_note = ""
            if _has_minus_sign(real_c):
                sign_c_note = (
                    " Observa que el signo negativo de la constante alterará los signos al sustituir "
                    "($+(-a) = -a$ o $(-a)\\cdot(-b) = +ab$)."
                )
            branch_note = ""
            if len(c_vals) > 1:
                branch_note = (
                    " Al haber más de una solución algebraica para la constante, se toma la que "
                    "reproduce la rama que también satisface la EDO."
                )
            builder.add(
                "Despejar la constante C",
                rf"{sp.latex(const_sym)} = {sp.latex(real_c)}",
                f"Aislamos ${sp.latex(const_sym)}$ de la ecuación ${eq_c_tex}$ aplicando operaciones inversas."
                + sign_c_note
                + branch_note,
            )
        else:
            builder.add(
                "Imponer la condición inicial en la rama verificada",
                particular.latex,
                "La condición inicial admite varias constantes reales aquí; se presenta la rama "
                "que además cumple la ecuación diferencial.",
            )
    else:
        sub_lhs = safe_simplify(general.expr.subs({X: x0_sym, Y: y0_sym}))
        val_sym = general.value if general.value is not None else const_sym
        eq_c_tex = rf"{sp.latex(sub_lhs)} = {sp.latex(val_sym)}"
        builder.add(
            f"Evaluar la relación implícita en ({x0:g}, {y0:g})",
            eq_c_tex,
            f"En la solución implícita ${general.latex}$, sustituimos $x = {x0_tex}$ e $y = {y0_tex}$ "
            f"para determinar el valor constante de nivel ${sp.latex(val_sym)}$.",
        )

    detalle_constante = (
        "Sustituimos el valor encontrado de la constante en la familia general y simplificamos "
        "los signos y coeficientes"
        if real_c is not None or not general.is_explicit
        else "Tomamos la rama de la familia general verificada en la EDO"
    )
    builder.add(
        "Escribir la solución particular del PVI",
        particular.latex,
        detalle_constante + " para obtener la curva que pasa por "
        f"$({x0_tex}, {y0_tex})$.",
    )


def _build_verification_step(
    builder: StepBuilder,
    solution: Solution,
    rhs: sp.Expr | None,
    original_F: sp.Expr | None,
    verification: Verification | None,
    *,
    is_particular: bool = False,
) -> None:
    """Añade el paso final que demuestra por qué el residuo es nulo."""

    if verification is None or verification.status != "ok":
        return

    titulo = (
        "Comprobar la solución particular en la EDO"
        if is_particular
        else "Verificar la solución por sustitución directa"
    )
    if solution.is_explicit and rhs is not None:
        deriv = sp.diff(solution.expr, X)
        rhs_sub = rhs.subs(Y, solution.expr)
        deriv_rules = explain_derivative_rules(solution.expr, X, label="y(x)")
        builder.add(
            titulo,
            rf"y'(x) = {sp.latex(deriv)}, \qquad y'(x) - f(x, y(x)) = {sp.latex(deriv)} - \left({sp.latex(rhs_sub)}\right) = 0",
            f"{deriv_rules} Al sustituir $y(x)$ y su derivada $y'(x)$ en la ecuación diferencial "
            "original, todos los términos se cancelan exactamente dando residuo $0$. Esto confirma "
            "que la solución cumple la EDO.",
        )
    elif solution.is_explicit and original_F is not None:
        deriv = _fast_simplify(sp.diff(solution.expr, X))
        builder.add(
            titulo,
            rf"y'(x) = {sp.latex(deriv)}, \qquad F(x, y(x), y'(x)) = 0",
            "Se sustituyen $y(x)$ y su derivada $y'(x)$ en la ecuación implícita $F(x, y, y') = 0$; "
            "los términos se anulan idénticamente (residuo $0$).",
        )
    elif solution.is_implicit:
        f_x = _fast_simplify(sp.diff(solution.expr, X))
        f_y = _fast_simplify(sp.diff(solution.expr, Y))
        if f_y != 0:
            y_prime_imp = _fast_simplify(-f_x / f_y)
            neg_note = ""
            if _has_minus_sign(f_x) and _has_minus_sign(f_y):
                neg_note = " Al dividir dos signos negativos en $-F_x / F_y$ se aplica menos entre menos."
            elif _has_minus_sign(f_x):
                neg_note = " Como $F_x$ es negativo, el signo menos delante de $-F_x$ produce $+|F_x|$ (menos por menos da más)."
            builder.add(
                titulo,
                rf"\frac{{dy}}{{dx}} = -\frac{{\partial F / \partial x}}{{\partial F / \partial y}} = -\frac{{{sp.latex(f_x)}}}{{{sp.latex(f_y)}}} = {sp.latex(y_prime_imp)}",
                "Por derivación implícita de $F(x, y) = C$ ($F_x\\,dx + F_y\\,dy = 0$), se despeja "
                r"$\frac{dy}{dx} = -\frac{F_x}{F_y}$."
                + neg_note
                + " Al comparar con la EDO original el residuo es $0$.",
            )


def enrich_solve_steps(
    base_steps: list[Step],
    *,
    general: Solution | None,
    particular: Solution | None,
    rhs: sp.Expr | None,
    original_F: sp.Expr | None,
    x0: float | None,
    y0: float | None,
    verification: Verification | None,
    particular_verification: Verification | None,
    used_singular: bool = False,
) -> list[Step]:
    """Agrega pasos de PVI y comprobación final numerando todo secuencialmente."""

    builder = StepBuilder()
    builder.extend_renumbered(base_steps)
    if general is not None and x0 is not None and y0 is not None and particular is not None:
        _build_pvi_steps(
            builder,
            general,
            particular,
            float(x0),
            float(y0),
            used_singular=used_singular,
        )
        if particular_verification is not None and particular_verification.status == "ok":
            _build_verification_step(
                builder,
                particular,
                rhs,
                original_F,
                particular_verification,
                is_particular=True,
            )
    elif general is not None and verification is not None and verification.status == "ok":
        _build_verification_step(
            builder,
            general,
            rhs,
            original_F,
            verification,
            is_particular=False,
        )
    return builder.steps


__all__ = [
    "StepBuilder",
    "add_product_atomic_steps",
    "add_transposition_step",
    "describe_double_negative",
    "describe_sign_product",
    "enrich_solve_steps",
    "explain_derivative_rules",
    "explain_integration_rules",
]
