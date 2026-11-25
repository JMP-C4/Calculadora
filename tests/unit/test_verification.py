"""Pruebas de verificación simbólica, numérica y del PVI."""

from __future__ import annotations

import sympy as sp

from odecalc.models import Solution
from odecalc.symbols import C, DY, X, Y
from odecalc.verify import apply_initial_conditions, verify_solution
from odecalc.verify.verifier import (
    _numeric_check_explicit,
    _numeric_check_implicit,
    _solve_for_constant,
    _with_definite_integrals,
    simplify_residual,
)


def test_explicit_solution_verifies() -> None:
    solution = Solution(form="explicit", expr=C * sp.exp(X))
    result = verify_solution(solution, rhs=Y)
    assert result.status == "ok"
    assert result.simplified_residual == "0"


def test_wrong_explicit_solution_fails() -> None:
    solution = Solution(form="explicit", expr=X**2)
    result = verify_solution(solution, rhs=sp.Integer(1))
    assert result.status == "fail"


def test_implicit_solution_verifies_by_implicit_differentiation() -> None:
    solution = Solution(form="implicit", expr=X * Y, value=C)
    result = verify_solution(solution, rhs=-Y / X)
    assert result.status == "ok"


def test_wrong_implicit_solution_fails() -> None:
    solution = Solution(form="implicit", expr=X + Y, value=C)
    result = verify_solution(solution, rhs=sp.Integer(0))
    assert result.status == "fail"


def test_unverified_without_equation() -> None:
    solution = Solution(form="explicit", expr=X)
    assert verify_solution(solution).status == "unverified"


def test_numeric_residual_checker_accepts_zero_residual() -> None:
    residual = sp.sin(X) ** 2 + sp.cos(X) ** 2 - 1
    passed, points, message = _numeric_check_explicit(
        residual, Solution(form="explicit", expr=sp.Integer(0)), None
    )
    assert passed
    assert points >= 3
    assert "Verificación numérica" in message


def test_numeric_implicit_checker_accepts_zero_residual() -> None:
    residual = sp.sin(X) ** 2 + sp.cos(Y) ** 2 - sp.cos(Y) ** 2 - sp.sin(X) ** 2
    passed, points, _ = _numeric_check_implicit(residual, None)
    assert passed
    assert points > 0


def test_apply_initial_conditions_explicit() -> None:
    solution = Solution(form="explicit", expr=C * sp.exp(X))
    particular, warnings = apply_initial_conditions(solution, 0.0, 2.0, rhs=Y)
    assert particular is not None
    assert warnings == []
    assert abs(complex(sp.N(particular.expr.subs(X, 0))) - 2.0) < 1e-9


def test_apply_initial_conditions_implicit() -> None:
    solution = Solution(form="implicit", expr=X * Y, value=C)
    particular, _ = apply_initial_conditions(solution, 1.0, 2.0)
    assert particular is not None
    assert particular.is_implicit
    assert float(particular.value) == 2.0


def test_apply_initial_conditions_with_nonelementary_integral() -> None:
    integral = sp.Integral(sp.exp(-X**2), X)
    rhs = Y + sp.exp(X - X**2)
    solution = Solution(form="explicit", expr=(C + integral) * sp.exp(X))
    particular, warnings = apply_initial_conditions(solution, 0.0, 1.0, rhs=rhs)
    assert particular is not None
    assert warnings == []
    assert not particular.expr.has(Y)
    value = complex(sp.N(particular.expr.subs(X, 0)))
    assert abs(value - 1.0) < 1e-6
    assert verify_solution(particular, rhs=rhs).status == "ok"


def test_apply_initial_conditions_incompatible_without_constant() -> None:
    solution = Solution(form="explicit", expr=sp.Integer(1))
    particular, warnings = apply_initial_conditions(solution, 0.0, 2.0)
    assert particular is None
    assert warnings


def test_unverified_implicit_without_equation() -> None:
    solution = Solution(form="implicit", expr=X * Y, value=C)
    assert verify_solution(solution).status == "unverified"


def test_implicit_solution_without_dependence_on_y_fails() -> None:
    solution = Solution(form="implicit", expr=X, value=C)
    result = verify_solution(solution, original_F=DY - Y)
    assert result.status == "fail"
    assert "no define y" in result.message


def test_explicit_and_implicit_verification_from_implicit_form() -> None:
    explicit = Solution(form="explicit", expr=sp.exp(X))
    assert verify_solution(explicit, original_F=DY - Y).status == "ok"

    implicit = Solution(form="implicit", expr=X * Y, value=C)
    assert verify_solution(implicit, original_F=DY + Y / X).status == "ok"


def test_numeric_checkers_reject_unevaluated_integrals() -> None:
    integral = sp.Integral(sp.exp(-X**2), X)
    passed, points, message = _numeric_check_explicit(
        integral, Solution(form="explicit", expr=sp.Integer(0)), None
    )
    assert not passed and points == 0
    assert "integral" in message.lower()

    passed, points, message = _numeric_check_implicit(integral, None)
    assert not passed and points == 0
    assert "integral" in message.lower()


def test_with_definite_integrals_converts_each_occurrence() -> None:
    expression = sp.Integral(sp.exp(-X**2), X) + sp.Integral(sp.exp(-X**3), X)
    adapted = _with_definite_integrals(expression, 0.0)
    integrals = list(adapted.atoms(sp.Integral))
    assert len(integrals) == 2
    assert all(len(atom.args[1]) == 3 for atom in integrals)
    assert all(atom.args[1][0].name.startswith("_tau") for atom in integrals)


def test_with_definite_integrals_ignores_other_forms() -> None:
    expression = X + 1
    assert _with_definite_integrals(expression, 0.0) == expression

    definite = sp.Integral(sp.exp(-X**2), (X, 0, 1))
    assert _with_definite_integrals(definite, 0.0) == definite


def test_solve_for_constant_uses_numeric_fallback() -> None:
    roots = _solve_for_constant(sp.Eq(C + sp.cos(C), 0), C)
    assert any(abs(float(sp.N(root)) + 0.739085) < 1e-4 for root in roots)


def test_simplify_residual_returns_zero_for_identity() -> None:
    residual = sp.sin(X) ** 2 + sp.cos(X) ** 2 - 1
    assert simplify_residual(residual) == 0


def test_apply_initial_conditions_rejects_nonfinite_implicit_point() -> None:
    solution = Solution(form="implicit", expr=Y / X, value=C)
    particular, warnings = apply_initial_conditions(solution, 0.0, 1.0)
    assert particular is None
    assert any("no es finita" in warning for warning in warnings)


def test_apply_initial_conditions_accepts_matching_constant_solution() -> None:
    solution = Solution(form="explicit", expr=sp.Integer(1))
    particular, warnings = apply_initial_conditions(solution, 0.0, 1.0)
    assert particular is solution
    assert warnings == []


def test_apply_initial_conditions_reports_multiple_branches() -> None:
    solution = Solution(form="explicit", expr=C**2 + X)
    particular, warnings = apply_initial_conditions(solution, 0.0, 1.0)
    assert particular is not None
    assert any("más de una rama" in warning for warning in warnings)


def test_apply_initial_conditions_reports_impossible_branch() -> None:
    solution = Solution(form="explicit", expr=C**2 + X)
    particular, warnings = apply_initial_conditions(solution, 0.0, -1.0)
    assert particular is None
    assert any("no permitió determinar" in warning for warning in warnings)
