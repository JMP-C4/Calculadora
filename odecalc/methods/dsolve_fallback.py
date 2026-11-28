"""Respaldo basado en ``sympy.dsolve`` (siempre marcado como tal)."""

from __future__ import annotations

import sympy as sp

from odecalc.methods.atomic_steps import StepBuilder
from odecalc.methods.common import (
    explicit_solution,
    implicit_solution,
    safe_simplify,
)
from odecalc.models import ParsedODE, Solution, Step
from odecalc.symbols import C, DY, X, Y

_ORIGINAL_DSOLVE = sp.dsolve
_UNSAFE_ONLY_HINTS = frozenset({"factorable", "lie_group"})


def _has_safe_dsolve_path(
    ode: sp.Eq,
    y_func: sp.Expr,
    derivative: sp.Expr,
) -> bool:
    """Evita cuelgues de ``sympy.dsolve`` en ecuaciones implícitas no lineales en ``y'``.

    En SymPy 1.14, ecuaciones implícitas cuadráticas en ``y'`` (como algunas de
    Lagrange) producen ramas con radicales cuyo único hint es ``lie_group``, cuya
    heurística combinatoria puede bloquearse indefinidamente.  Las ecuaciones
    explícitas ``y' = f(x, y)`` no se bloquean: ``lie_group`` es con frecuencia
    el único hint y ``dsolve`` las resuelve sin problema.
    """

    # Las EDOs explícitas y' = f(x, y) pueden tener sólo el hint ``lie_group``
    # y aun así resolverse con dsolve (p. ej. y' = exp(y) + log(x)).
    # El bloqueo se reserva a ecuaciones implícitas no lineales en y'.
    if ode.lhs == derivative:
        return True
    try:
        hints = set(sp.classify_ode(ode, y_func))
    except Exception:
        return True
    if not hints or not hints.issubset(_UNSAFE_ONLY_HINTS):
        return True
    try:
        roots = sp.solve(ode, derivative)
    except Exception:
        return True
    if not roots:
        return False
    for root in roots:
        try:
            sub_hints = set(sp.classify_ode(sp.Eq(derivative, root), y_func))
        except Exception:
            return True
        if sub_hints - _UNSAFE_ONLY_HINTS:
            return True
    return False


def solve(parsed: ParsedODE) -> tuple[Solution, list[Step], list[Solution]]:
    y_func = sp.Function("y")(X)
    derivative = sp.Derivative(y_func, X)

    if parsed.rhs is not None:
        ode = sp.Eq(derivative, parsed.rhs.subs(Y, y_func))
    elif parsed.F is not None:
        implicit = parsed.F.subs({DY: derivative, Y: y_func})
        ode = sp.Eq(implicit, 0)
    else:
        raise ValueError("No hay una ecuación utilizable para dsolve.")

    if sp.dsolve is _ORIGINAL_DSOLVE and not _has_safe_dsolve_path(
        ode, y_func, derivative
    ):
        raise ValueError(
            "sympy.dsolve no dispone de un método cerrado aplicable sin bloqueo heurístico."
        )

    raw = sp.dsolve(ode, y_func)
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    if not isinstance(raw, sp.Eq):
        raise ValueError("dsolve no devolvió una ecuación utilizable.")

    builder = StepBuilder()
    builder.add(
        "Preparar la EDO para el respaldo simbólico general",
        sp.latex(ode),
        "Los métodos elementales clasificados no produjeron una solución verificable, por lo que "
        r"formulamos la ecuación en forma funcional para integrarla con $\mathrm{sympy.dsolve}$ "
        "(por ejemplo, mediante transformaciones generales de Lie o funciones especiales).",
    )

    if raw.lhs == y_func:
        solution = explicit_solution(raw.rhs)
    elif raw.rhs == y_func:
        solution = explicit_solution(raw.lhs)
    else:
        # Forma implícita (A-04): no descartar rhs cuando mezcla constante y términos en x.
        diff_expr = safe_simplify((raw.lhs - raw.rhs).subs(y_func, Y))
        consts = sorted(
            (sym for sym in diff_expr.free_symbols if sym not in {X, Y}),
            key=lambda s: s.name,
        )
        potential: sp.Expr | None = None
        if len(consts) == 1:
            c_sym = consts[0]
            try:
                solved_c = sp.solve(sp.Eq(diff_expr, 0), c_sym)
            except Exception:
                solved_c = []
            for cand in solved_c:
                if not cand.has(c_sym):
                    potential = safe_simplify(cand)
                    break
        if potential is None:
            lhs = raw.lhs
            rhs = raw.rhs
            if lhs.has(y_func) and not rhs.has(y_func):
                non_const = rhs.subs({c: 0 for c in rhs.free_symbols if c not in {X, Y}})
                potential = safe_simplify((lhs - non_const).subs(y_func, Y))
            elif rhs.has(y_func) and not lhs.has(y_func):
                non_const = lhs.subs({c: 0 for c in lhs.free_symbols if c not in {X, Y}})
                potential = safe_simplify((rhs - non_const).subs(y_func, Y))
            else:
                raise ValueError("La forma devuelta por dsolve no es reconocible.")
        solution = implicit_solution(potential)

    builder.add(
        "Extraer la solución simbólica propuesta",
        solution.latex,
        "Aislamos la constante de integración o expresamos la relación en variables $(x, y)$; "
        "a continuación verificaremos simbólicamente y/o numéricamente que anule el residuo.",
    )

    return solution, builder.steps, []


__all__ = ["solve"]
