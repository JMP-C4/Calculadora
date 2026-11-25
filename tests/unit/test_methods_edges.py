"""Casos límite y ramas de error de los solucionadores por método."""

from __future__ import annotations

import sympy as sp
import pytest

from odecalc.methods import common, dsolve_fallback, reducible, separable
from odecalc.models import ParsedODE
from odecalc.symbols import C, DY, X, Y


def test_separable_constant_solution() -> None:
    solution, steps, lost = separable.solve(sp.Integer(0))
    assert solution.is_explicit
    assert solution.expr == C
    assert steps
    assert lost == []


def test_separable_explicit_branch() -> None:
    solution, steps, lost = separable.solve(Y)
    assert solution.is_explicit
    assert sp.simplify(solution.expr - sp.exp(X + C)) == 0
    assert [item.expr for item in lost] == [sp.Integer(0)]


def test_separable_multiple_branches_are_kept_implicit() -> None:
    solution, steps, lost = separable.solve(Y**3 - Y)
    assert solution.is_implicit
    assert solution.branch_note
    assert {item.expr for item in lost} == {
        sp.Integer(-1),
        sp.Integer(0),
        sp.Integer(1),
    }
    assert any("varias ramas" in step.explanation for step in steps)


def test_separable_implicit_branch_without_elementary_integral() -> None:
    solution, steps, _ = separable.solve(sp.exp(-Y**2) / (1 + Y**4))
    assert solution.is_implicit
    assert not solution.expr.has(sp.Integral)
    assert any("implícita" in step.explanation for step in steps)


def test_separable_rejects_non_separable_rhs() -> None:
    with pytest.raises(ValueError):
        separable.solve(sp.sin(X * Y) + X**2 + Y)


def test_dsolve_fallback_explicit_and_implicit() -> None:
    explicit, steps, _ = dsolve_fallback.solve(
        ParsedODE(original="", kind="explicit", rhs=Y)
    )
    assert explicit.is_explicit
    assert sp.simplify(sp.diff(explicit.expr, X) - explicit.expr) == 0
    assert steps

    implicit, _, _ = dsolve_fallback.solve(
        ParsedODE(original="", kind="implicit", F=DY - Y)
    )
    assert implicit.is_explicit


def test_dsolve_fallback_requires_usable_equation() -> None:
    with pytest.raises(ValueError):
        dsolve_fallback.solve(ParsedODE(original="", kind="explicit"))


def test_dsolve_fallback_rejects_bad_results(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed = ParsedODE(original="", kind="explicit", rhs=Y)
    for bad in ([], 42, sp.Eq(X, Y)):
        monkeypatch.setattr(dsolve_fallback.sp, "dsolve", lambda *args, _bad=bad, **kwargs: _bad)
        with pytest.raises(ValueError):
            dsolve_fallback.solve(parsed)


def test_common_safe_helpers_fall_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(common.sp, "integrate", lambda *args, **kwargs: 1 / 0)
    result = common.safe_integrate(sp.exp(-X**2), X)
    assert result.has(sp.Integral)

    monkeypatch.setattr(common.sp, "simplify", lambda *args, **kwargs: 1 / 0)
    expression = X + 1
    assert common.safe_simplify(expression) == expression


def test_common_safe_solve_returns_empty_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*args, **kwargs):
        raise RuntimeError("sin solver")

    monkeypatch.setattr(common.sp, "solve", explode)
    assert common.safe_solve(sp.Eq(X, Y), Y) == []
    assert common.safe_solve_expr(X - Y, Y) == []


def test_common_standard_linear_and_explicit_solver() -> None:
    expression, mu, integral_p, integral_muq = common.standard_linear_solution(
        sp.Integer(2), sp.Integer(1)
    )
    assert sp.simplify(mu - sp.exp(2 * X)) == 0
    assert not integral_p.has(sp.Integral)
    assert not integral_muq.has(sp.Integral)
    assert sp.simplify(expression - (C * sp.exp(-2 * X) + sp.Rational(1, 2))) == 0

    assert sp.simplify(common.solve_explicit_for(X - Y, Y) - X) == 0
    assert common.solve_explicit_for(sp.Function("f")(Y) - X, Y) is None


def test_common_equilibrium_ignores_complex_roots() -> None:
    assert common.equilibrium_solutions(Y**2 + 1) == []
    solutions = common.equilibrium_solutions((Y - 2) * (Y + 3))
    assert {item.expr for item in solutions} == {sp.Integer(2), sp.Integer(-3)}


def test_reducible_parallel_lines() -> None:
    solution, steps, _ = reducible.solve((X + Y + 1) / (2 * X + 2 * Y + 3))
    assert solution.is_explicit
    assert any("paralelas" in step.explanation for step in steps)


def test_reducible_intersecting_lines() -> None:
    solution, steps, _ = reducible.solve((X + Y + 1) / (X - Y - 3))
    assert solution.is_implicit
    assert any("intersección" in step.title for step in steps)


def test_reducible_rejects_non_linear_quotient() -> None:
    with pytest.raises(ValueError):
        reducible.solve(sp.sin(X * Y))
