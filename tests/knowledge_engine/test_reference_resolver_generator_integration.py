"""
Integration test:

report reference text
        ↓
resolve_reference_range()
        ↓
ReferenceInterval
        ↓
LabResult
        ↓
FindingGenerator
        ↓
Finding
        ↓
KnowledgeEngine
"""

from pathlib import Path

from knowledge_engine.core.enums import LabStatus

from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import ReferenceInterval

from knowledge_engine.services.generator import FindingGenerator
from knowledge_engine.services.engine import KnowledgeEngine
from knowledge_engine.services.matcher import KnowledgeMatcher
from knowledge_engine.services.registry import KnowledgeRegistry
from knowledge_engine.services.scorer import KnowledgeScorer

from interpretation.reference_resolver import (
    resolve_reference_range,
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


def resolve_interval(
    reference_text,
    age_value=34,
    age_unit="years",
    sex="male",
):

    resolved = resolve_reference_range(
        reference_text,
        {
            "age_value": age_value,
            "age_unit": age_unit,
            "sex": sex,
        },
    )

    assert resolved["resolved"] is True

    return ReferenceInterval(
        minimum=resolved["min"],
        maximum=resolved["max"],
    )


def test_reference_resolver_returns_interval():

    print_header(
        "TEST 1 — RESOLVER → REFERENCE INTERVAL"
    )

    interval = resolve_interval(
        "13.0-17.0"
    )

    assert isinstance(
        interval,
        ReferenceInterval,
    )

    assert interval.minimum == 13.0
    assert interval.maximum == 17.0

    passed()


def test_sex_specific_reference_is_resolved():

    print_header(
        "TEST 2 — SEX SPECIFIC REFERENCE"
    )

    reference = """
    Male: 13.0 - 17.0
    Female: 12.0 - 15.0
    """

    interval = resolve_interval(
        reference,
        sex="male",
    )

    assert interval.minimum == 13.0
    assert interval.maximum == 17.0

    female_interval = resolve_interval(
        reference,
        sex="female",
    )

    assert female_interval.minimum == 12.0
    assert female_interval.maximum == 15.0

    passed()


def test_resolved_interval_generates_low_finding():

    print_header(
        "TEST 3 — RESOLVED INTERVAL → LOW FINDING"
    )

    interval = resolve_interval(
        "80.0-100.0"
    )

    result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=75.0,
        unit="fL",
        reference=interval,
        raw_reference="80.0-100.0",
    )

    finding = FindingGenerator().generate(
        result
    )

    assert finding.status is LabStatus.LOW

    assert finding.result is result

    assert (
        finding.result.reference
        is interval
    )

    passed()


def test_resolved_interval_generates_normal_finding():

    print_header(
        "TEST 4 — RESOLVED INTERVAL → NORMAL FINDING"
    )

    interval = resolve_interval(
        "80.0-100.0"
    )

    result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=90.0,
        unit="fL",
        reference=interval,
        raw_reference="80.0-100.0",
    )

    finding = FindingGenerator().generate(
        result
    )

    assert finding.status is LabStatus.NORMAL

    passed()


def test_resolved_interval_generates_high_finding():

    print_header(
        "TEST 5 — RESOLVED INTERVAL → HIGH FINDING"
    )

    interval = resolve_interval(
        "80.0-100.0"
    )

    result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=105.0,
        unit="fL",
        reference=interval,
        raw_reference="80.0-100.0",
    )

    finding = FindingGenerator().generate(
        result
    )

    assert finding.status is LabStatus.HIGH

    passed()


def test_resolved_findings_reach_engine():

    print_header(
        "TEST 6 — RESOLVED FINDINGS → KNOWLEDGE ENGINE"
    )

    # These are report reference intervals.
    # They are resolved first, then supplied to
    # LabResult and FindingGenerator.

    mcv_interval = resolve_interval(
        "80.0-100.0"
    )

    mch_interval = resolve_interval(
        "27.0-33.0"
    )

    mcv_result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=75.0,
        unit="fL",
        reference=mcv_interval,
        raw_reference="80.0-100.0",
    )

    mch_result = LabResult(
        test_name="mch",
        raw_name="MCH",
        value=24.0,
        unit="pg",
        reference=mch_interval,
        raw_reference="27.0-33.0",
    )

    generator = FindingGenerator()

    mcv_finding = generator.generate(
        mcv_result
    )

    mch_finding = generator.generate(
        mch_result
    )

    assert mcv_finding.status is LabStatus.LOW
    assert mch_finding.status is LabStatus.LOW

    engine = create_engine()

    results = engine.evaluate(
        (
            mcv_finding,
            mch_finding,
        )
    )

    assert len(results) >= 1

    microcytic = next(
        result
        for result in results
        if result.pattern.id
        == "microcytic_cbc_pattern"
    )

    assert microcytic.matched is True

    assert len(
        microcytic.evidence.matched_required
    ) == 2

    passed()


def test_reference_is_preserved_end_to_end():

    print_header(
        "TEST 7 — REFERENCE PRESERVED END-TO-END"
    )

    reference_text = "80.0-100.0"

    interval = resolve_interval(
        reference_text
    )

    result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=75.0,
        unit="fL",
        reference=interval,
        raw_reference=reference_text,
    )

    finding = FindingGenerator().generate(
        result
    )

    assert (
        finding.result.reference.minimum
        == 80.0
    )

    assert (
        finding.result.reference.maximum
        == 100.0
    )

    assert (
        finding.result.reference
        is result.reference
    )

    passed()


def test_engine_does_not_resolve_reference():

    print_header(
        "TEST 8 — ENGINE RECEIVES FINDINGS"
    )

    interval = resolve_interval(
        "80.0-100.0"
    )

    result = LabResult(
        test_name="mcv",
        raw_name="MCV",
        value=75.0,
        unit="fL",
        reference=interval,
        raw_reference="80.0-100.0",
    )

    finding = FindingGenerator().generate(
        result
    )

    assert finding.status is LabStatus.LOW

    assert finding.result.reference is interval

    engine = create_engine()

    engine.evaluate(
        (finding,)
    )

    # The Knowledge Engine receives an already
    # interpreted Finding.
    #
    # The reference interval belongs to the
    # LabResult and is preserved by the Finding.
    #
    # The engine does not need to create,
    # resolve, or replace the reference interval.

    assert finding.result.reference.minimum == 80.0
    assert finding.result.reference.maximum == 100.0

    passed()

if __name__ == "__main__":

    test_reference_resolver_returns_interval()
    test_sex_specific_reference_is_resolved()
    test_resolved_interval_generates_low_finding()
    test_resolved_interval_generates_normal_finding()
    test_resolved_interval_generates_high_finding()
    test_resolved_findings_reach_engine()
    test_reference_is_preserved_end_to_end()
    test_engine_does_not_resolve_reference()

    finished(
        "ALL REFERENCE → GENERATOR → ENGINE "
        "INTEGRATION TESTS PASSED"
    )