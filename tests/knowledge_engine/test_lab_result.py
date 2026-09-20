"""
Unit tests for LabResult model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import ReferenceInterval

from tests.utils import print_header, passed, finished


def build_result():

    return LabResult(
        test_name="hemoglobin",
        raw_name="Hb",
        value=15.9,
        unit="g/dL",
        reference=ReferenceInterval(13.0, 17.0),
        raw_reference="13.0 - 17.0",
    )


def test_creation():
    print_header("TEST 1 — CREATION")

    result = build_result()

    assert result.test_name == "hemoglobin"
    assert result.raw_name == "Hb"

    passed()


def test_reference():
    print_header("TEST 2 — REFERENCE")

    result = build_result()

    assert result.reference.contains(15.9)

    passed()


def test_raw_reference():
    print_header("TEST 3 — RAW REFERENCE")

    result = build_result()

    assert result.raw_reference == "13.0 - 17.0"

    passed()


def test_immutable():
    print_header("TEST 4 — IMMUTABLE")

    result = build_result()

    try:

        result.value = 20

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_reference()
    test_raw_reference()
    test_immutable()

    finished("ALL LAB RESULT TESTS PASSED")