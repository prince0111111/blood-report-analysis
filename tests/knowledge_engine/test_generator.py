"""
Tests for FindingGenerator.
"""

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

from tests.utils import (
    print_header,
    passed,
    finished,
)


def make_lab_result(
    value: float,
    minimum: float = 13.0,
    maximum: float = 17.0,
) -> LabResult:

    reference = ReferenceInterval(
        minimum=minimum,
        maximum=maximum,
    )

    return LabResult(
        test_name="hemoglobin",
        raw_name="Hemoglobin",
        value=value,
        unit="g/dL",
        reference=reference,
        raw_reference="13.0-17.0",
    )


def test_low():

    print_header("TEST 1 — LOW")

    result = make_lab_result(11.0)

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.LOW

    passed()


def test_normal():

    print_header("TEST 2 — NORMAL")

    result = make_lab_result(15.0)

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.NORMAL

    passed()


def test_high():

    print_header("TEST 3 — HIGH")

    result = make_lab_result(19.0)

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.HIGH

    passed()


def test_lower_boundary():

    print_header("TEST 4 — LOWER BOUNDARY")

    result = make_lab_result(13.0)

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.NORMAL

    passed()


def test_upper_boundary():

    print_header("TEST 5 — UPPER BOUNDARY")

    result = make_lab_result(17.0)

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.NORMAL

    passed()


def test_default_severity():

    print_header("TEST 6 — DEFAULT SEVERITY")

    result = make_lab_result(11.0)

    finding = FindingGenerator().generate(result)

    assert finding.severity is Severity.UNKNOWN

    passed()


def test_low_reason():

    print_header("TEST 7 — LOW REASON")

    result = make_lab_result(11.0)

    finding = FindingGenerator().generate(result)

    assert finding.reason is not None
    assert "below" in finding.reason
    assert "13.0-17.0" in finding.reason

    passed()


def test_normal_reason():

    print_header("TEST 8 — NORMAL REASON")

    result = make_lab_result(15.0)

    finding = FindingGenerator().generate(result)

    assert finding.reason is not None
    assert "within" in finding.reason

    passed()


def test_high_reason():

    print_header("TEST 9 — HIGH REASON")

    result = make_lab_result(19.0)

    finding = FindingGenerator().generate(result)

    assert finding.reason is not None
    assert "above" in finding.reason

    passed()


def test_original_result_preserved():

    print_header("TEST 10 — ORIGINAL RESULT")

    result = make_lab_result(11.0)

    finding = FindingGenerator().generate(result)

    assert finding.result is result
    assert finding.test_name == "hemoglobin"
    assert finding.value == 11.0
    assert finding.unit == "g/dL"

    passed()


def test_actual_reference_interval_is_used():

    print_header(
        "TEST 11 — ACTUAL REFERENCE INTERVAL USED"
    )

    result = make_lab_result(
        value=11.0,
        minimum=12.0,
        maximum=16.0,
    )

    finding = FindingGenerator().generate(result)

    assert finding.status is LabStatus.LOW

    passed()


if __name__ == "__main__":

    test_low()
    test_normal()
    test_high()
    test_lower_boundary()
    test_upper_boundary()
    test_default_severity()
    test_low_reason()
    test_normal_reason()
    test_high_reason()
    test_original_result_preserved()
    test_actual_reference_interval_is_used()

    finished(
        "ALL FINDING GENERATOR TESTS PASSED"
    )