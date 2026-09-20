"""
Unit tests for Interpretation model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.models.interpretation import Interpretation
from knowledge_engine.models.match_result import MatchResult
from knowledge_engine.models.pattern import Pattern
from knowledge_engine.models.evidence import Evidence
from knowledge_engine.core.enums import PatternCategory

from tests.utils import print_header, passed, finished


def build_match():

    pattern = Pattern(
        id="iron_deficiency",
        name="Iron Deficiency Pattern",
        category=PatternCategory.CBC,
        description="Pattern",
    )

    return MatchResult(
        pattern=pattern,
        evidence=Evidence(),
        score=91.0,
        matched=True,
    )


def test_empty():

    print_header("TEST 1 — EMPTY")

    interpretation = Interpretation()

    assert len(interpretation.findings) == 0
    assert len(interpretation.matches) == 0
    assert interpretation.primary_match is None

    passed()


def test_primary_match():

    print_header("TEST 2 — PRIMARY MATCH")

    match = build_match()

    interpretation = Interpretation(
        matches=(match,),
        primary_match=match,
    )

    assert interpretation.primary_match is match

    passed()


def test_match_storage():

    print_header("TEST 3 — MATCH STORAGE")

    match = build_match()

    interpretation = Interpretation(
        matches=(match,),
    )

    assert len(interpretation.matches) == 1

    passed()


def test_immutable():

    print_header("TEST 4 — IMMUTABLE")

    interpretation = Interpretation()

    try:

        interpretation.primary_match = None

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_empty()
    test_primary_match()
    test_match_storage()
    test_immutable()

    finished("ALL INTERPRETATION TESTS PASSED")