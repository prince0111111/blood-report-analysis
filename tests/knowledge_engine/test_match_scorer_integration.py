"""
Integration tests for KnowledgeMatcher + KnowledgeScorer.

These tests verify that:
    Findings
        ↓
    Matcher
        ↓
    Evidence
        ↓
    Scorer
        ↓
    Score

works correctly as one pipeline.
"""

from pathlib import Path

from knowledge_engine.core.enums import (
    LabStatus,
    Severity,
)
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.pattern import Pattern
from knowledge_engine.models.reference_interval import (
    ReferenceInterval,
)
from knowledge_engine.services.matcher import (
    KnowledgeMatcher,
)
from knowledge_engine.services.registry import (
    KnowledgeRegistry,
)
from knowledge_engine.services.scorer import (
    KnowledgeScorer,
)

from tests.utils import (
    print_header,
    passed,
    finished,
)


PATTERN_PATH = Path(
    "knowledge_engine/knowledge/cbc/patterns/"
    "microcytic_pattern.yaml"
)


def load_pattern() -> Pattern:

    registry = KnowledgeRegistry()

    return registry.load_file(
        PATTERN_PATH
    )


def finding(
    test_name: str,
    status: LabStatus,
) -> Finding:
    """
    Create a synthetic Finding for integration tests.

    The reference interval is only test fixture data.
    The Matcher does not use it.
    """

    reference = ReferenceInterval(
        minimum=10.0,
        maximum=20.0,
    )

    result = LabResult(
        test_name=test_name,
        value=15.0,
        unit="test",
        raw_name=test_name,
        reference=reference,
        raw_reference="10-20",
    )

    return Finding(
        result=result,
        status=status,
        severity=Severity.UNKNOWN,
    )


def match_and_score(
    findings: tuple[Finding, ...],
    pattern: Pattern,
):
    """
    Run the real Matcher followed by the real Scorer.
    """

    matcher = KnowledgeMatcher()
    scorer = KnowledgeScorer()

    match = matcher.match(
        findings,
        pattern,
    )

    score = scorer.score(
        match
    )

    return match, score


def test_complete_required_match():

    print_header(
        "TEST 1 — COMPLETE REQUIRED MATCH + SCORE"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
        finding(
            "mch",
            LabStatus.LOW,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is True

    assert len(
        match.evidence.matched_required
    ) == 2

    assert len(
        match.evidence.missing_required
    ) == 0

    assert len(
        match.evidence.contradictory
    ) == 0

    assert score == 70.0

    passed()


def test_partial_required_match():

    print_header(
        "TEST 2 — PARTIAL REQUIRED MATCH + SCORE"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is False

    assert len(
        match.evidence.matched_required
    ) == 1

    assert (
        "mch"
        in match.evidence.missing_required
    )

    assert score == 35.0

    passed()


def test_complete_required_and_supportive():

    print_header(
        "TEST 3 — REQUIRED + SUPPORTIVE + SCORE"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
        finding(
            "mch",
            LabStatus.LOW,
        ),
        finding(
            "hemoglobin",
            LabStatus.LOW,
        ),
        finding(
            "rdw",
            LabStatus.HIGH,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is True

    assert len(
        match.evidence.matched_required
    ) == 2

    assert len(
        match.evidence.matched_supportive
    ) == 2

    assert score == 100.0

    passed()


def test_contradictory_match():

    print_header(
        "TEST 4 — CONTRADICTORY + SCORE"
    )

    pattern = load_pattern()

    findings = (
    finding(
        "mcv",
        LabStatus.HIGH,
    ),
    finding(
        "mch",
        LabStatus.LOW,
    ),
)

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is False

    assert len(
        match.evidence.contradictory
    ) == 1

    assert score == 10.0

    passed()


def test_unrelated_findings():

    print_header(
        "TEST 5 — UNRELATED FINDINGS + SCORE"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "platelets",
            LabStatus.HIGH,
        ),
        finding(
            "wbc",
            LabStatus.NORMAL,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is False

    assert len(
        match.evidence.matched_required
    ) == 0

    assert len(
        match.evidence.missing_required
    ) == 2

    assert score == 0.0

    passed()


def test_empty_findings():

    print_header(
        "TEST 6 — EMPTY FINDINGS + SCORE"
    )

    pattern = load_pattern()

    match, score = match_and_score(
        tuple(),
        pattern,
    )

    assert match.matched is False

    assert len(
        match.evidence.missing_required
    ) == 2

    assert score == 0.0

    passed()


def test_wrong_status():

    print_header(
        "TEST 7 — WRONG STATUS + SCORE"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.HIGH,
        ),
        finding(
            "mch",
            LabStatus.LOW,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is False

    assert (
        "mcv"
        in match.evidence.missing_required
    )

    assert score == 10.0

    passed()


def test_score_is_independent_from_match_flag():

    print_header(
        "TEST 8 — SCORE INDEPENDENT FROM MATCH FLAG"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
    )

    match, score = match_and_score(
        findings,
        pattern,
    )

    assert match.matched is False

    assert score > 0.0

    passed()


if __name__ == "__main__":

    test_complete_required_match()
    test_partial_required_match()
    test_complete_required_and_supportive()
    test_contradictory_match()
    test_unrelated_findings()
    test_empty_findings()
    test_wrong_status()
    test_score_is_independent_from_match_flag()

    finished(
        "ALL MATCH + SCORER INTEGRATION TESTS PASSED"
    )