"""
Unit tests for Finding model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.core.enums import (
    AgeUnit,
    LabStatus,
    Severity,
    Sex,
)

from knowledge_engine.models.patient import Patient
from knowledge_engine.models.reference_interval import ReferenceInterval
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.report import Report
from knowledge_engine.models.finding import Finding

from tests.utils import print_header, passed, finished


def build_result():

    return LabResult(
        test_name="hemoglobin",
        raw_name="Hb",
        value=11.2,
        unit="g/dL",
        reference=ReferenceInterval(13.0, 17.0),
        raw_reference="13.0-17.0",
    )


def test_creation():

    print_header("TEST 1 — CREATION")

    finding = Finding(
        result=build_result(),
        status=LabStatus.LOW,
    )

    assert finding.status is LabStatus.LOW

    passed()


def test_properties():

    print_header("TEST 2 — PROPERTIES")

    finding = Finding(
        result=build_result(),
        status=LabStatus.LOW,
    )

    assert finding.test_name == "hemoglobin"
    assert finding.value == 11.2
    assert finding.unit == "g/dL"

    passed()


def test_reason():

    print_header("TEST 3 — REASON")

    finding = Finding(
        result=build_result(),
        status=LabStatus.LOW,
        reason="Below reference interval.",
    )

    assert finding.reason == "Below reference interval."

    passed()


def test_default_severity():

    print_header("TEST 4 — DEFAULT SEVERITY")

    finding = Finding(
        result=build_result(),
        status=LabStatus.LOW,
    )

    assert finding.severity is Severity.UNKNOWN

    passed()


def test_immutable():

    print_header("TEST 5 — IMMUTABLE")

    finding = Finding(
        result=build_result(),
        status=LabStatus.LOW,
    )

    try:

        finding.status = LabStatus.NORMAL

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_properties()
    test_reason()
    test_default_severity()
    test_immutable()

    finished("ALL FINDING TESTS PASSED")