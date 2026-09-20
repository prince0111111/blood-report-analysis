"""
Integration tests for:

LabResult
    ↓
FindingGenerator
    ↓
Finding
    ↓
KnowledgeEngine
    ↓
MatchResult
"""

from pathlib import Path

from knowledge_engine.core.enums import (
    LabStatus,
    Severity,
)

from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import (
    ReferenceInterval,
)

from knowledge_engine.services.generator import (
    FindingGenerator,
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


def create_engine():

    return KnowledgeEngine(
        registry=create_registry(),
        matcher=KnowledgeMatcher(),
        scorer=KnowledgeScorer(),
    )


def create_lab_result(
    test_name: str,
    value: float,
) -> LabResult:

    reference = ReferenceInterval(
        minimum=10.0,
        maximum=20.0,
    )

    return LabResult(
        test_name=test_name,
        raw_name=test_name,
        value=value,
        unit="test",
        reference=reference,
        raw_reference="10-20",
    )


def generate_finding(
    test_name: str,
    value: float,
):

    generator = FindingGenerator()

    result = create_lab_result(
        test_name,
        value,
    )

    return generator.generate(
        result
    )


def test_low_finding_reaches_engine():

    print_header(
        "TEST 1 — LOW FINDING → ENGINE"
    )

    mcv = generate_finding(
        "mcv",
        8.0,
    )

    assert mcv.status is LabStatus.LOW

    engine = create_engine()

    results = engine.evaluate(
        (mcv,)
    )

    assert len(results) == 1

    result = results[0]

    assert result.pattern.id == (
        "microcytic_cbc_pattern"
    )

    assert result.matched is False

    assert result.evidence.missing_required == (
        "mch",
    )

    passed()


def test_complete_generated_findings_match():

    print_header(
        "TEST 2 — GENERATED FINDINGS → COMPLETE MATCH"
    )

    mcv = generate_finding(
        "mcv",
        8.0,
    )

    mch = generate_finding(
        "mch",
        8.0,
    )

    assert mcv.status is LabStatus.LOW
    assert mch.status is LabStatus.LOW

    engine = create_engine()

    results = engine.evaluate(
        (
            mcv,
            mch,
        )
    )

    assert len(results) == 1

    result = results[0]

    assert result.pattern.id == (
        "microcytic_cbc_pattern"
    )

    assert result.matched is True

    assert len(
        result.evidence.matched_required
    ) == 2

    passed()


def test_normal_value_does_not_match_low_requirement():

    print_header(
        "TEST 3 — NORMAL FINDING → NO MATCH"
    )

    mcv = generate_finding(
        "mcv",
        15.0,
    )

    assert mcv.status is LabStatus.NORMAL

    engine = create_engine()

    results = engine.evaluate(
        (mcv,)
    )

    assert len(results) == 1

    result = results[0]

    assert result.matched is False

    assert result.evidence.matched_required == ()

    passed()


def test_generated_finding_preserves_reference():

    print_header(
        "TEST 4 — REFERENCE PRESERVED"
    )

    result = create_lab_result(
        "mcv",
        8.0,
    )

    finding = FindingGenerator().generate(
        result
    )

    assert finding.result is result

    assert finding.result.reference is (
        result.reference
    )

    assert finding.result.reference.minimum == 10.0
    assert finding.result.reference.maximum == 20.0

    passed()


if __name__ == "__main__":

    test_low_finding_reaches_engine()
    test_complete_generated_findings_match()
    test_normal_value_does_not_match_low_requirement()
    test_generated_finding_preserves_reference()

    finished(
        "ALL GENERATOR → ENGINE INTEGRATION TESTS PASSED"
    )