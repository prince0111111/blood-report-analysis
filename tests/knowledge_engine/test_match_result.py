"""
Unit tests for MatchResult model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.core.enums import PatternCategory

from knowledge_engine.models.pattern import Pattern
from knowledge_engine.models.evidence import Evidence
from knowledge_engine.models.match_result import MatchResult

from tests.utils import print_header, passed, finished


def build_pattern():

    return Pattern(
        id="iron_deficiency",
        name="Iron Deficiency Pattern",
        category=PatternCategory.CBC,
        description="Pattern",
    )


def test_creation():

    print_header("TEST 1 — CREATION")

    result = MatchResult(
        pattern=build_pattern(),
        evidence=Evidence(),
        score=91.5,
        matched=True,
    )

    assert result.score == 91.5

    passed()


def test_boolean():

    print_header("TEST 2 — MATCHED FLAG")

    result = MatchResult(
        pattern=build_pattern(),
        evidence=Evidence(),
        score=20,
        matched=False,
    )

    assert result.matched is False

    passed()


def test_pattern():

    print_header("TEST 3 — PATTERN")

    result = MatchResult(
        pattern=build_pattern(),
        evidence=Evidence(),
        score=80,
        matched=True,
    )

    assert result.pattern.name == "Iron Deficiency Pattern"

    passed()


def test_immutable():

    print_header("TEST 4 — IMMUTABLE")

    result = MatchResult(
        pattern=build_pattern(),
        evidence=Evidence(),
        score=80,
        matched=True,
    )

    try:

        result.score = 50

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_boolean()
    test_pattern()
    test_immutable()

    finished("ALL MATCH RESULT TESTS PASSED")