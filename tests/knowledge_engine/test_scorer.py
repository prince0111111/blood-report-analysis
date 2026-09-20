"""
Tests for KnowledgeScorer.
"""

from knowledge_engine.core.enums import (
    LabStatus,
    PatternCategory,
)
from knowledge_engine.models.evidence import Evidence
from knowledge_engine.models.finding_requirement import (
    FindingRequirement,
)
from knowledge_engine.models.match_result import (
    MatchResult,
)
from knowledge_engine.models.pattern import Pattern
from knowledge_engine.services.scorer import (
    KnowledgeScorer,
)

from tests.utils import (
    print_header,
    passed,
    finished,
)


def pattern(
    required=(),
    supportive=(),
    contradictory=(),
):
    return Pattern(
        id="test_pattern",
        name="Test Pattern",
        category=PatternCategory.CBC,
        description="Synthetic scoring pattern.",
        priority=100,
        required=tuple(required),
        supportive=tuple(supportive),
        contradictory=tuple(contradictory),
    )


def requirement(
    test_name,
    status=LabStatus.LOW,
):
    return FindingRequirement(
        test_name=test_name,
        status=status,
    )


def result(
    pattern,
    matched_required=(),
    matched_supportive=(),
    missing_required=(),
    contradictory=(),
):
    evidence = Evidence(
        matched_required=tuple(
            matched_required
        ),
        matched_supportive=tuple(
            matched_supportive
        ),
        missing_required=tuple(
            missing_required
        ),
        contradictory=tuple(
            contradictory
        ),
    )

    return MatchResult(
        pattern=pattern,
        evidence=evidence,
        score=0.0,
        matched=(
            len(missing_required) == 0
            and len(contradictory) == 0
        ),
    )


def test_complete_required_match():

    print_header(
        "TEST 1 — COMPLETE REQUIRED MATCH"
    )

    pattern_obj = pattern(
        required=(
            requirement("mcv"),
            requirement("mch"),
        )
    )

    match = result(
        pattern_obj,
        matched_required=(
            object(),
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 70.0

    passed()


def test_partial_required_match():

    print_header(
        "TEST 2 — PARTIAL REQUIRED MATCH"
    )

    pattern_obj = pattern(
        required=(
            requirement("mcv"),
            requirement("mch"),
        )
    )

    match = result(
        pattern_obj,
        matched_required=(
            object(),
        ),
        missing_required=(
            "mch",
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 35.0

    passed()


def test_complete_supportive_match():

    print_header(
        "TEST 3 — COMPLETE SUPPORTIVE MATCH"
    )

    pattern_obj = pattern(
        supportive=(
            requirement("hemoglobin"),
            requirement("rdw"),
        )
    )

    match = result(
        pattern_obj,
        matched_supportive=(
            object(),
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 30.0

    passed()


def test_partial_supportive_match():

    print_header(
        "TEST 4 — PARTIAL SUPPORTIVE MATCH"
    )

    pattern_obj = pattern(
        supportive=(
            requirement("hemoglobin"),
            requirement("rdw"),
        )
    )

    match = result(
        pattern_obj,
        matched_supportive=(
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 15.0

    passed()


def test_required_and_supportive():

    print_header(
        "TEST 5 — REQUIRED AND SUPPORTIVE"
    )

    pattern_obj = pattern(
        required=(
            requirement("mcv"),
            requirement("mch"),
        ),
        supportive=(
            requirement("hemoglobin"),
            requirement("rdw"),
        ),
    )

    match = result(
        pattern_obj,
        matched_required=(
            object(),
            object(),
        ),
        matched_supportive=(
            object(),
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 100.0

    passed()


def test_contradictory_penalty():

    print_header(
        "TEST 6 — CONTRADICTORY PENALTY"
    )

    pattern_obj = pattern(
        required=(
            requirement("mcv"),
        ),
        contradictory=(
            requirement(
                "mcv",
                LabStatus.HIGH,
            ),
        ),
    )

    match = result(
        pattern_obj,
        matched_required=(
            object(),
        ),
        contradictory=(
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score == 45.0

    passed()


def test_score_never_above_100():

    print_header(
        "TEST 7 — SCORE UPPER BOUND"
    )

    pattern_obj = pattern(
        required=(
            requirement("mcv"),
        ),
        supportive=(
            requirement("rdw"),
        ),
    )

    match = result(
        pattern_obj,
        matched_required=(
            object(),
        ),
        matched_supportive=(
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score <= 100.0

    passed()


def test_score_never_below_zero():

    print_header(
        "TEST 8 — SCORE LOWER BOUND"
    )

    pattern_obj = pattern(
        contradictory=(
            requirement(
                "mcv",
                LabStatus.HIGH,
            ),
        )
    )

    match = result(
        pattern_obj,
        contradictory=(
            object(),
        ),
    )

    score = KnowledgeScorer().score(match)

    assert score >= 0.0

    passed()


def test_empty_pattern():

    print_header(
        "TEST 9 — EMPTY PATTERN"
    )

    pattern_obj = pattern()

    match = result(
        pattern_obj
    )

    score = KnowledgeScorer().score(match)

    assert score == 0.0

    passed()


if __name__ == "__main__":

    test_complete_required_match()
    test_partial_required_match()
    test_complete_supportive_match()
    test_partial_supportive_match()
    test_required_and_supportive()
    test_contradictory_penalty()
    test_score_never_above_100()
    test_score_never_below_zero()
    test_empty_pattern()

    finished(
        "ALL SCORER TESTS PASSED"
    )