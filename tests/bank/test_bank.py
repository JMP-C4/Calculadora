"""Prueba parametrizada del banco de 100+ ejercicios clásicos."""

from __future__ import annotations

import pytest

from odecalc.api import solve
from tests.bank.exercises import EXERCISES


pytestmark = pytest.mark.bank


def test_bank_has_at_least_100_exercises() -> None:
    assert len(EXERCISES) >= 100
    assert len({exercise["id"] for exercise in EXERCISES}) == len(EXERCISES)


@pytest.mark.parametrize("exercise", EXERCISES, ids=[item["id"] for item in EXERCISES])
def test_exercise_classification_and_verification(exercise: dict[str, object]) -> None:
    result = solve(
        str(exercise["equation"]),
        x0=float(exercise["x0"]),
        y0=float(exercise["y0"]),
        compute_numeric=False,
    )
    assert result.error is None, result.warnings
    assert result.general is not None
    assert result.verification is not None
    assert result.verification.status == "ok"
    methods = {match.method for match in result.classifications}
    assert exercise["expected_method"] in methods
    assert result.steps
    assert result.particular is not None
    assert result.particular_verification is not None
    assert result.particular_verification.status == "ok"
