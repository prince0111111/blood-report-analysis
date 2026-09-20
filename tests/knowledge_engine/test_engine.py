"""
Tests for KnowledgeEngine.

These tests verify orchestration of:

    Registry
        ↓
    Matcher
        ↓
    Scorer
        ↓
    MatchResult
"""

from pathlib import Path

from knowledge_engine.core.enums import (
    LabStatus,
    Severity,
)
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import (
    ReferenceInterval,
)
from knowledge_engine.services.engine import (
    KnowledgeEngine,
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


def create_registry():

    registry = KnowledgeRegistry()

    registry.load_file(
        PATTERN_PATH
    )

    return registry


def finding(
    test_name: str,
    status: LabStatus,
) -> Finding:

    reference = ReferenceInterval(
        minimum=10.0,
        maximum=20.0,
    )

    result = LabResult(
        test_name=test_name,
        raw_name=test_name,
        value=15.0,
        unit="test",
        reference=reference,
        raw_reference="10-20",
    )

    return Finding(
        result=result,
        status=status,
        severity=Severity.UNKNOWN,
    )


def create_engine():

    return KnowledgeEngine(
        registry=create_registry(),
        matcher=KnowledgeMatcher(),
        scorer=KnowledgeScorer(),
    )


def test_engine_creation():

    print_header(
        "TEST 1 — ENGINE CREATION"
    )

    engine = create_engine()

    assert isinstance(
        engine,
        KnowledgeEngine,
    )

    passed()


def test_evaluate_complete_match():

    print_header(
        "TEST 2 — COMPLETE MATCH"
    )

    engine = create_engine()

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

    results = engine.evaluate(
        findings
    )

    assert len(results) == 1

    result = results[0]

    assert result.pattern.id == (
        "microcytic_cbc_pattern"
    )

    assert result.matched is True

    assert result.score == 70.0

    passed()


def test_evaluate_partial_match():

    print_header(
        "TEST 3 — PARTIAL MATCH"
    )

    engine = create_engine()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
    )

    results = engine.evaluate(
        findings
    )

    assert len(results) == 1

    result = results[0]

    assert result.matched is False

    assert result.score == 35.0

    passed()


def test_evaluate_unrelated_findings():

    print_header(
        "TEST 4 — UNRELATED FINDINGS"
    )

    engine = create_engine()

    findings = (
        finding(
            "platelets",
            LabStatus.HIGH,
        ),
    )

    results = engine.evaluate(
        findings
    )

    assert len(results) == 1

    result = results[0]

    assert result.matched is False

    assert result.score == 0.0

    passed()


def test_evaluate_matched():

    print_header(
        "TEST 5 — MATCHED ONLY"
    )

    engine = create_engine()

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

    results = engine.evaluate_matched(
        findings
    )

    assert len(results) == 1

    assert results[0].matched is True

    passed()


def test_evaluate_matched_excludes_partial():

    print_header(
        "TEST 6 — MATCHED EXCLUDES PARTIAL"
    )

    engine = create_engine()

    findings = (
        finding(
            "mcv",
            LabStatus.LOW,
        ),
    )

    results = engine.evaluate_matched(
        findings
    )

    assert len(results) == 0

    passed()


def test_evaluate_ranked():

    print_header(
        "TEST 7 — RANKED RESULTS"
    )

    engine = create_engine()

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

    results = engine.evaluate_ranked(
        findings
    )

    assert len(results) == 1

    assert results[0].score == 70.0

    passed()


def test_engine_uses_supplied_services():

    print_header(
        "TEST 8 — SUPPLIED SERVICES"
    )

    registry = create_registry()

    matcher = KnowledgeMatcher()

    scorer = KnowledgeScorer()

    engine = KnowledgeEngine(
        registry=registry,
        matcher=matcher,
        scorer=scorer,
    )

    assert engine is not None

    passed()


if __name__ == "__main__":

    test_engine_creation()
    test_evaluate_complete_match()
    test_evaluate_partial_match()
    test_evaluate_unrelated_findings()
    test_evaluate_matched()
    test_evaluate_matched_excludes_partial()
    test_evaluate_ranked()
    test_engine_uses_supplied_services()

    finished(
        "ALL ENGINE TESTS PASSED"
    )