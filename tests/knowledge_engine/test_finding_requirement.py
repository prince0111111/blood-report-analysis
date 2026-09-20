"""
Unit tests for FindingRequirement model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.core.enums import LabStatus, Severity
from knowledge_engine.models.finding_requirement import FindingRequirement

from tests.utils import print_header, passed, finished


def test_creation():

    print_header("TEST 1 — CREATION")

    requirement = FindingRequirement(
        test_name="hemoglobin",
        status=LabStatus.LOW,
    )

    assert requirement.test_name == "hemoglobin"
    assert requirement.status is LabStatus.LOW

    passed()


def test_optional_severity():

    print_header("TEST 2 — OPTIONAL SEVERITY")

    requirement = FindingRequirement(
        test_name="platelets",
        status=LabStatus.LOW,
        severity=Severity.SEVERE,
    )

    assert requirement.severity is Severity.SEVERE

    passed()


def test_default_severity():

    print_header("TEST 3 — DEFAULT SEVERITY")

    requirement = FindingRequirement(
        test_name="mcv",
        status=LabStatus.LOW,
    )

    assert requirement.severity is None

    passed()


def test_immutable():

    print_header("TEST 4 — IMMUTABLE")

    requirement = FindingRequirement(
        test_name="hemoglobin",
        status=LabStatus.LOW,
    )

    try:

        requirement.test_name = "rbc"

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_optional_severity()
    test_default_severity()
    test_immutable()

    finished("ALL FINDING REQUIREMENT TESTS PASSED")