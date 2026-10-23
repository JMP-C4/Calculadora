"""Tests unitarios del catálogo de ejercicios."""

from __future__ import annotations

from collections import Counter

from data.exercises import load_exercises
from math_engine.parser import parse_ode


def test_catalog_has_at_least_fifteen_exercises():
    assert len(load_exercises()) >= 15


def test_required_type_minimums():
    counts = Counter(exercise.ode_type for exercise in load_exercises())

    assert counts["separable"] >= 3
    assert counts["linear"] >= 3
    assert counts["exact"] >= 2
    assert counts["homogeneous"] >= 2
    assert counts["bernoulli"] >= 2
    assert counts["application"] >= 3


def test_exercise_fields_are_populated():
    for exercise in load_exercises():
        assert exercise.id
        assert exercise.name
        assert exercise.description
        assert exercise.latex_str
        assert exercise.equation_text


def test_exercise_ids_are_unique():
    exercises = load_exercises()
    assert len({exercise.id for exercise in exercises}) == len(exercises)


def test_every_equation_is_parseable():
    for exercise in load_exercises():
        result = parse_ode(exercise.equation_text)
        assert result.error is None, f"{exercise.id}: {result.error}"
        assert result.rhs is not None


def test_initial_conditions_are_consistent():
    for exercise in load_exercises():
        conditions = exercise.initial_conditions
        if conditions is None:
            continue
        assert conditions.x_min < conditions.x_max
        assert conditions.x0 is None or conditions.x_min <= conditions.x0 <= conditions.x_max
        assert conditions.y0 is None or isinstance(conditions.y0, float)
