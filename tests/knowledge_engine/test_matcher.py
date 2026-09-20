"""
Tests for KnowledgeMatcher.
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
    Create a Finding using the existing
    LabResult domain model.
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


def test_complete_match():

    print_header(
        "TEST 1 — COMPLETE REQUIRED MATCH"
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

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is True

    assert len(
        result.evidence.matched_required
    ) == 2

    assert len(
        result.evidence.missing_required
    ) == 0

    assert len(
        result.evidence.contradictory
    ) == 0

    assert result.score == 0.0

    passed()


def test_missing_required():

    print_header(
        "TEST 2 — MISSING REQUIRED FINDING"
    )

    pattern = load_pattern()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
    )

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is False

    assert (
        "mch"
        in result.evidence.missing_required
    )

    passed()


def test_supportive_match():

    print_header(
        "TEST 3 — SUPPORTIVE FINDINGS"
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

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is True

    assert len(
        result.evidence.matched_required
    ) == 2

    assert len(
        result.evidence.matched_supportive
    ) == 2

    passed()


def test_contradictory_finding():

    print_header(
        "TEST 4 — CONTRADICTORY FINDING"
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
            "mcv",
            LabStatus.HIGH,
        ),
    )

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is False

    assert len(
        result.evidence.contradictory
    ) == 1

    passed()


def test_unrelated_findings():

    print_header(
        "TEST 5 — UNRELATED FINDINGS"
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

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is False

    assert len(
        result.evidence.matched_required
    ) == 0

    assert len(
        result.evidence.missing_required
    ) == 2

    passed()


def test_empty_findings():

    print_header(
        "TEST 6 — EMPTY FINDINGS"
    )

    pattern = load_pattern()

    result = KnowledgeMatcher().match(
        tuple(),
        pattern,
    )

    assert result.matched is False

    assert len(
        result.evidence.missing_required
    ) == 2

    passed()


def test_wrong_status():

    print_header(
        "TEST 7 — WRONG STATUS"
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

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is False

    assert (
        "mcv"
        in result.evidence.missing_required
    )

    passed()


def test_required_and_supportive_separation():

    print_header(
        "TEST 8 — EVIDENCE SEPARATION"
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
    )

    result = KnowledgeMatcher().match(
        findings,
        pattern,
    )

    assert result.matched is True

    assert len(
        result.evidence.matched_required
    ) == 2

    assert len(
        result.evidence.matched_supportive
    ) == 1

    assert len(
        result.evidence.contradictory
    ) == 0

    passed()


if __name__ == "__main__":

    test_complete_match()
    test_missing_required()
    test_supportive_match()
    test_contradictory_finding()
    test_unrelated_findings()
    test_empty_findings()
    test_wrong_status()
    test_required_and_supportive_separation()

    finished(
        "ALL MATCHER TESTS PASSED"
    )