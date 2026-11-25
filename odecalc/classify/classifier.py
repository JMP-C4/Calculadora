"""Clasificador multi-método para EDOs de primer orden.

Cada detector devuelve :class:`odecalc.models.Match` con la evidencia que
justifica su aplicación.  El clasificador no elige un único tipo: enumera
todos los métodos aplicables y asigna una prioridad de resolución.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

import sympy as sp

from odecalc.models import Match, ParsedODE
from odecalc.symbols import DX, DY, DY_DIFF, U, X, Y

_T = sp.Symbol("t", positive=True)
_X0 = sp.Symbol("_x0", real=True)
_Y0 = sp.Symbol("_y0", real=True)

_PRIORITY = {
    "clairaut": 5,
    "lagrange": 6,
    "exact": 10,
    "linear": 12,
    "substitution_linear_combo": 14,
    "integrating_factor_x": 15,
    "integrating_factor_y": 16,
    "integrating_factor_xy": 17,
    "integrating_factor_x_plus_y": 18,
    "integrating_factor_x2_plus_y2": 19,
    "separable": 20,
    "bernoulli": 40,
    "homogeneous": 50,
    "reducible_homogeneous": 55,
    "riccati": 70,
}


def _match(method: str, name: str, evidence: str, **data: object) -> Match:
    return Match(
        method=method,
        name=name,
        evidence=evidence,
        priority=_PRIORITY.get(method, 100),
        data=dict(data),
    )


# ---------------------------------------------------------------------------
# Detección de estructuras
# ---------------------------------------------------------------------------
def separable_parts(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """Devuelve ``(g(x), h(y))`` si ``rhs = g(x) h(y)``."""

    if not rhs.has(Y):
        return sp.simplify(rhs), sp.Integer(1)
    try:
        factored = sp.factor(rhs)
        independent, dependent = factored.as_independent(Y)
    except Exception:
        return None
    if independent.has(Y) or dependent.has(X):
        return None
    if sp.simplify(independent * dependent - factored) != 0:
        return None
    return sp.simplify(independent), sp.simplify(dependent)


def linear_coeffs(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """Devuelve ``(P, Q)`` si ``rhs = -P y + Q`` (forma lineal)."""

    try:
        coefficient = sp.simplify(sp.diff(rhs, Y))
        remainder = sp.simplify(rhs - coefficient * Y)
    except Exception:
        return None
    if coefficient.has(Y) or remainder.has(Y):
        return None
    return sp.simplify(-coefficient), sp.simplify(remainder)


def _term_y_power(term: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    """Separa un término en ``coeficiente(x) * y**n``."""

    try:
        coefficient, rest = term.as_independent(Y, as_Add=False)
    except Exception:
        return None
    if coefficient.has(Y):
        return None
    if rest == 1:
        return coefficient, sp.Integer(0)
    if not rest.has(Y):
        return None
    if rest == Y:
        return coefficient, sp.Integer(1)
    base, exponent = rest.as_base_exp()
    if base != Y or exponent.has(Y):
        return None
    return coefficient, exponent


def bernoulli_coeffs(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Devuelve ``(P, Q, n)`` para ``y' + P y = Q y**n`` con n real != 0, 1."""

    terms = sp.Add.make_args(sp.expand(rhs))
    powers: dict[sp.Expr, sp.Expr] = {}
    for term in terms:
        parsed = _term_y_power(term)
        if parsed is None:
            return None
        coefficient, exponent = parsed
        if exponent.has(Y):
            return None
        powers[exponent] = sp.simplify(powers.get(exponent, 0) + coefficient)

    nonlinear = [exponent for exponent in powers if exponent not in (0, 1)]
    if len(nonlinear) != 1:
        return None
    n = sp.nsimplify(nonlinear[0])
    if n in (0, 1) or n.has(Y):
        return None
    if powers.get(0, 0) != 0:
        # Un término independiente convierte la ecuación en Riccati, no en
        # Bernoulli, salvo que sea idénticamente nulo.
        return None
    if set(powers) - {0, 1, n}:
        return None
    p_expr = sp.simplify(-powers.get(1, 0))
    q_expr = sp.simplify(powers.get(n, 0))
    if q_expr == 0 or p_expr.has(Y) or q_expr.has(Y):
        return None
    return p_expr, q_expr, n


def exact_parts(parsed: ParsedODE) -> tuple[sp.Expr, sp.Expr] | None:
    """Extrae ``M, N`` de la forma diferencial o de ``dy/dx = -M/N``."""

    if parsed.kind == "differential" and parsed.M is not None and parsed.N is not None:
        return sp.simplify(parsed.M), sp.simplify(parsed.N)
    if parsed.rhs is None:
        return None
    try:
        numerator, denominator = sp.fraction(sp.together(parsed.rhs))
    except Exception:
        return None
    if denominator == 0:
        return None
    big_m = sp.simplify(-numerator)
    big_n = sp.simplify(denominator)
    if big_m == 0 or big_n == 0:
        return None
    return big_m, big_n


def is_exact(m_expr: sp.Expr, n_expr: sp.Expr) -> bool:
    try:
        return sp.simplify(sp.diff(m_expr, Y) - sp.diff(n_expr, X)) == 0
    except Exception:
        return False


def homogeneous_degree_zero(rhs: sp.Expr) -> bool:
    if not rhs.has(Y):
        return False
    f = rhs.subs({X: _X0, Y: _Y0})
    try:
        scaled = sp.simplify(f.subs({_X0: _T * _X0, _Y0: _T * _Y0}))
        return sp.simplify(scaled - f) == 0
    except Exception:
        return False


def _linear_2d(expr: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Devuelve ``(a, b, c)`` si ``expr = a x + b y + c``."""

    try:
        poly = sp.Poly(sp.expand(expr), X, Y)
    except (sp.PolynomialError, TypeError, ValueError):
        return None
    if poly.total_degree() > 1:
        return None
    return (
        sp.simplify(poly.coeff_monomial(X)),
        sp.simplify(poly.coeff_monomial(Y)),
        sp.simplify(poly.coeff_monomial(1)),
    )


def reducible_linear_coeffs(rhs: sp.Expr) -> tuple[sp.Expr, ...] | None:
    """Detecta ``(a1 x + b1 y + c1)/(a2 x + b2 y + c2)``."""

    try:
        numerator, denominator = sp.fraction(sp.together(rhs))
    except Exception:
        return None
    if denominator == 0:
        return None
    num = _linear_2d(numerator)
    den = _linear_2d(denominator)
    if num is None or den is None:
        return None
    a1, b1, c1 = num
    a2, b2, c2 = den
    if a2 == 0 and b2 == 0:
        return None
    if c1 == 0 and c2 == 0:
        return None
    return a1, b1, c1, a2, b2, c2


def _as_rational_pair(value: sp.Expr) -> tuple[sp.Expr, sp.Expr] | None:
    try:
        numerator, denominator = sp.fraction(sp.together(sp.nsimplify(value)))
    except Exception:
        return None
    if denominator == 0:
        return None
    return numerator, denominator


def substitution_linear_combo(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Detecta ``rhs = G(a x + b y)`` y devuelve ``(a, b, G(u))``."""

    if not rhs.has(Y):
        return None
    try:
        f_x = sp.simplify(sp.diff(rhs, X))
        f_y = sp.simplify(sp.diff(rhs, Y))
    except Exception:
        return None
    if f_y == 0:
        return None
    try:
        ratio = sp.simplify(f_x / f_y)
    except Exception:
        return None
    if ratio.has(X) or ratio.has(Y):
        return None
    pair = _as_rational_pair(ratio)
    if pair is None:
        return None
    a, b = pair
    if b == 0:
        a, b = sp.Integer(1), sp.Integer(0)
    if b == 0:
        return None
    # Normaliza el signo para que b sea positivo cuando sea numérico.
    if getattr(b, "is_number", False) and b.is_negative:
        a, b = -a, -b
    try:
        g_u = sp.simplify(rhs.subs({X: 0, Y: U / b}))
    except Exception:
        return None
    if g_u.has(X) or g_u.has(Y):
        return None
    try:
        if sp.simplify(rhs - g_u.subs(U, a * X + b * Y)) != 0:
            return None
    except Exception:
        return None
    return sp.simplify(a), sp.simplify(b), g_u


def riccati_coeffs(rhs: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr] | None:
    """Devuelve ``(q0, q1, q2)`` para ``y' = q0 + q1 y + q2 y²``."""

    try:
        poly = sp.Poly(sp.expand(rhs), Y)
    except (sp.PolynomialError, TypeError, ValueError):
        return None
    if poly.degree() != 2:
        return None
    q2 = sp.simplify(poly.coeff_monomial(Y**2))
    q1 = sp.simplify(poly.coeff_monomial(Y))
    q0 = sp.simplify(poly.coeff_monomial(1))
    if q2 == 0 or q0 == 0:
        return None
    if any(item.has(Y) for item in (q0, q1, q2)):
        return None
    return q0, q1, q2


def clairaut_or_lagrange(parsed: ParsedODE) -> tuple[str, sp.Expr, sp.Expr] | None:
    """Devuelve ``(tipo, phi(p), psi(p))`` para Clairaut o Lagrange."""

    if parsed.F is None or parsed.kind != "implicit" or DY not in parsed.F.free_symbols:
        return None
    try:
        solutions = sp.solve(sp.Eq(parsed.F, 0), Y)
    except Exception:
        return None
    if len(solutions) != 1:
        return None
    expr = sp.simplify(solutions[0])
    try:
        phi = sp.simplify(sp.diff(expr, X))
        psi = sp.simplify(expr - phi * X)
    except Exception:
        return None
    if phi.has(X, Y) or psi.has(X, Y):
        return None
    if not phi.has(DY):
        return None
    if sp.simplify(phi - DY) == 0:
        return "clairaut", sp.simplify(phi), psi
    if psi.has(DY):
        return "lagrange", phi, psi
    return None


def _depends_only_on(candidate: sp.Expr, u_expr: sp.Expr) -> sp.Expr | None:
    """Devuelve ``h(u)`` si ``candidate`` sólo depende de ``u_expr``."""

    try:
        if u_expr == X:
            if candidate.has(Y):
                return None
            return sp.simplify(candidate.subs(X, U))
        if u_expr == Y:
            if candidate.has(X):
                return None
            return sp.simplify(candidate.subs(Y, U))
        if u_expr == X * Y:
            substituted = sp.simplify(candidate.subs(Y, U / X))
        elif sp.simplify(u_expr - (X + Y)) == 0:
            substituted = sp.simplify(candidate.subs(Y, U - X))
        elif sp.simplify(u_expr - (X**2 + Y**2)) == 0:
            substituted = sp.simplify(candidate.subs(Y, sp.sqrt(U - X**2)))
        else:
            return None
    except Exception:
        return None
    if substituted.has(X) or substituted.has(Y):
        return None
    return substituted


def integrating_factor_candidates(
    m_expr: sp.Expr, n_expr: sp.Expr
) -> list[tuple[str, sp.Expr, sp.Expr]]:
    """Busca factores integrantes μ(x), μ(y), μ(xy), μ(x+y), μ(x²+y²).

    Devuelve una lista de ``(nombre, u, mu)``.  Sólo se aceptan candidatos
    que hacen exacta a la ecuación multiplicada.
    """

    candidates: list[tuple[str, sp.Expr, sp.Expr]] = []
    try:
        m_y = sp.simplify(sp.diff(m_expr, Y))
        n_x = sp.simplify(sp.diff(n_expr, X))
    except Exception:
        return candidates

    rules = (
        ("integrating_factor_x", X, n_expr, m_y - n_x),
        ("integrating_factor_y", Y, -m_expr, m_y - n_x),
        ("integrating_factor_xy", X * Y, n_expr * Y - m_expr * X, m_y - n_x),
        (
            "integrating_factor_x_plus_y",
            X + Y,
            n_expr - m_expr,
            m_y - n_x,
        ),
        (
            "integrating_factor_x2_plus_y2",
            X**2 + Y**2,
            2 * Y * n_expr - 2 * X * m_expr,
            m_y - n_x,
        ),
    )

    seen: set[str] = set()
    for name, u_expr, denominator, numerator in rules:
        denominator = sp.simplify(denominator)
        if denominator == 0:
            continue
        try:
            ratio = sp.simplify(numerator / denominator)
        except Exception:
            continue
        h_u = _depends_only_on(ratio, u_expr)
        if h_u is None or h_u == 0:
            continue
        try:
            integral = sp.integrate(h_u, U)
        except Exception:
            continue
        mu_u = sp.simplify(sp.exp(integral))
        mu = sp.simplify(mu_u.subs(U, u_expr))
        if mu == 0:
            continue
        try:
            if not is_exact(sp.simplify(mu * m_expr), sp.simplify(mu * n_expr)):
                continue
        except Exception:
            continue
        key = sp.sstr(mu)
        if key in seen:
            continue
        seen.add(key)
        candidates.append((name, u_expr, mu))
    return candidates


# ---------------------------------------------------------------------------
# Clasificación pública
# ---------------------------------------------------------------------------
def classify(parsed: ParsedODE) -> list[Match]:
    """Devuelve todos los métodos aplicables, ordenados por prioridad."""

    if parsed.error is not None:
        return []

    matches: list[Match] = []
    rhs = parsed.rhs

    cl = clairaut_or_lagrange(parsed)
    if cl is not None:
        kind, phi, psi = cl
        method = "clairaut" if kind == "clairaut" else "lagrange"
        label = "Clairaut" if kind == "clairaut" else "Lagrange"
        matches.append(
            _match(
                method,
                label,
                f"La ecuación se escribe como y = x·φ(y') + ψ(y') con "
                f"φ(y') = {sp.sstr(phi)} y ψ(y') = {sp.sstr(psi)}.",
                phi=phi,
                psi=psi,
            )
        )

    exact = exact_parts(parsed)
    if exact is not None and is_exact(*exact):
        m_expr, n_expr = exact
        matches.append(
            _match(
                "exact",
                "Exacta",
                f"∂M/∂y = ∂N/∂x = {sp.sstr(sp.simplify(sp.diff(m_expr, Y)))}.",
                M=m_expr,
                N=n_expr,
            )
        )

    if exact is not None and not is_exact(*exact):
        m_expr, n_expr = exact
        for name, u_expr, mu in integrating_factor_candidates(m_expr, n_expr):
            labels = {
                "integrating_factor_x": "Factor integrante μ(x)",
                "integrating_factor_y": "Factor integrante μ(y)",
                "integrating_factor_xy": "Factor integrante μ(xy)",
                "integrating_factor_x_plus_y": "Factor integrante μ(x+y)",
                "integrating_factor_x2_plus_y2": "Factor integrante μ(x²+y²)",
            }
            matches.append(
                _match(
                    name,
                    labels[name],
                    f"La razón que define μ depende sólo de u = {sp.sstr(u_expr)}; "
                    f"μ = {sp.sstr(mu)} hace exacta la ecuación.",
                    M=m_expr,
                    N=n_expr,
                    mu=mu,
                    u=u_expr,
                )
            )

    if rhs is not None:
        linear = linear_coeffs(rhs)
        if linear is not None:
            p_expr, q_expr = linear
            matches.append(
                _match(
                    "linear",
                    "Lineal de primer orden",
                    f"Se escribe como y' + P(x)y = Q(x) con P = {sp.sstr(p_expr)} "
                    f"y Q = {sp.sstr(q_expr)}.",
                    P=p_expr,
                    Q=q_expr,
                )
            )

        parts = separable_parts(rhs)
        if parts is not None:
            g_expr, h_expr = parts
            matches.append(
                _match(
                    "separable",
                    "Separable",
                    f"El lado derecho factoriza como g(x)·h(y) con "
                    f"g = {sp.sstr(g_expr)} y h = {sp.sstr(h_expr)}.",
                    g=g_expr,
                    h=h_expr,
                )
            )

        bernoulli = bernoulli_coeffs(rhs)
        if bernoulli is not None:
            p_expr, q_expr, n = bernoulli
            matches.append(
                _match(
                    "bernoulli",
                    "Bernoulli",
                    f"Tiene la forma y' + P(x)y = Q(x)yⁿ con P = {sp.sstr(p_expr)}, "
                    f"Q = {sp.sstr(q_expr)} y n = {sp.sstr(n)}.",
                    P=p_expr,
                    Q=q_expr,
                    n=n,
                )
            )

        if homogeneous_degree_zero(rhs):
            matches.append(
                _match(
                    "homogeneous",
                    "Homogénea de grado cero",
                    "f(tx, ty) = f(x, y): la sustitución y = u x reduce la EDO "
                    "a una separable en u y x.",
                )
            )

        reducible = reducible_linear_coeffs(rhs)
        if reducible is not None:
            a1, b1, c1, a2, b2, c2 = reducible
            determinant = sp.simplify(a1 * b2 - a2 * b1)
            kind = (
                "las rectas se cortan"
                if determinant != 0
                else "las rectas son paralelas"
            )
            matches.append(
                _match(
                    "reducible_homogeneous",
                    "Reducible a homogénea",
                    f"Es un cociente de rectas y {kind}; una traslación o la "
                    "sustitución u = a x + b y la vuelve homogénea/separable.",
                    a1=a1,
                    b1=b1,
                    c1=c1,
                    a2=a2,
                    b2=b2,
                    c2=c2,
                )
            )

        substitution = substitution_linear_combo(rhs)
        # Cuando a = 0 la sustitución es simplemente u = b y y la ecuación ya
        # es separable; no se duplica el método (y se evita elegir una rama
        # arbitraria antes que la solución separable completa).
        if substitution is not None and sp.simplify(substitution[0]) != 0:
            a, b, g_u = substitution
            matches.append(
                _match(
                    "substitution_linear_combo",
                    "Sustitución u = a x + b y",
                    f"El lado derecho depende sólo de u = {sp.sstr(a)}x + "
                    f"{sp.sstr(b)}y; entonces u' = {sp.sstr(a)} + "
                    f"{sp.sstr(b)}·G(u).",
                    a=a,
                    b=b,
                    G=g_u,
                )
            )

        riccati = riccati_coeffs(rhs)
        if riccati is not None:
            q0, q1, q2 = riccati
            matches.append(
                _match(
                    "riccati",
                    "Riccati",
                    f"Es de la forma y' = q₀ + q₁y + q₂y² con q₀ = {sp.sstr(q0)}, "
                    f"q₁ = {sp.sstr(q1)} y q₂ = {sp.sstr(q2)}.",
                    q0=q0,
                    q1=q1,
                    q2=q2,
                )
            )

    matches.sort(key=lambda item: (item.priority, item.method))
    return matches


__all__ = [
    "classify",
    "separable_parts",
    "linear_coeffs",
    "bernoulli_coeffs",
    "exact_parts",
    "is_exact",
    "homogeneous_degree_zero",
    "reducible_linear_coeffs",
    "substitution_linear_combo",
    "riccati_coeffs",
    "clairaut_or_lagrange",
    "integrating_factor_candidates",
]
