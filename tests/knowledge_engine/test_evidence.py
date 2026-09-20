"""
Unit tests for Evidence model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.core.enums import (
    LabStatus,
)

from knowledge_engine.models.reference_interval import ReferenceInterval
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.evidence import Evidence

from tests.utils import print_header, passed, finished


def build_finding():

    result = LabResult(
        test_name="hemoglobin",
        raw_name="Hb",
        value=11.2,
        unit="g/dL",
        reference=ReferenceInterval(13, 17),
        raw_reference="13-17",
    )

    return Finding(
        result=result,
        status=LabStatus.LOW,
    )


def test_creation():

    print_header("TEST 1 — CREATION")

    evidence = Evidence()

    assert len(evidence.matched_required) == 0

    passed()


def test_required():

    print_header("TEST 2 — REQUIRED")

    evidence = Evidence(
        matched_required=(build_finding(),),
    )

    assert len(evidence.matched_required) == 1

    passed()


def test_missing():

    print_header("TEST 3 — MISSING")

    evidence = Evidence(
        missing_required=("platelets",),
    )

    assert evidence.missing_required[0] == "platelets"

    passed()


def test_contradictory():

    print_header("TEST 4 — CONTRADICTORY")

    evidence = Evidence(
        contradictory=(build_finding(),),
    )

    assert len(evidence.contradictory) == 1

    passed()


def test_immutable():

    print_header("TEST 5 — IMMUTABLE")

    evidence = Evidence()

    try:

        evidence.missing_required = ()

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_required()
    test_missing()
    test_contradictory()
    test_immutable()

    finished("ALL EVIDENCE TESTS PASSED")