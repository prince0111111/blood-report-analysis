"""
Unit tests for Report model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.models.patient import Patient
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import ReferenceInterval
from knowledge_engine.models.report import Report

from knowledge_engine.core.enums import Sex, AgeUnit

from tests.utils import print_header, passed, finished


def build_patient():

    return Patient(
        sex=Sex.MALE,
        age_value=34,
        age_unit=AgeUnit.YEARS,
    )


def build_result():

    return LabResult(
        test_name="hemoglobin",
        raw_name="Hb",
        value=15.9,
        unit="g/dL",
        reference=ReferenceInterval(13.0, 17.0),
        raw_reference="13.0-17.0",
    )


def test_empty_report():
    print_header("TEST 1 — EMPTY REPORT")

    report = Report(patient=build_patient())

    assert report.lab_result_count == 0

    passed()


def test_report_results():
    print_header("TEST 2 — ONE RESULT")

    report = Report(
        patient=build_patient(),
        lab_results=(build_result(),),
    )

    assert report.lab_result_count == 1

    passed()


def test_tuple_storage():
    print_header("TEST 3 — TUPLE")

    report = Report(
        patient=build_patient(),
        lab_results=(build_result(),),
    )

    assert isinstance(report.lab_results, tuple)

    passed()


def test_immutable():
    print_header("TEST 4 — IMMUTABLE")

    report = Report(patient=build_patient())

    try:

        report.patient = None

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_empty_report()
    test_report_results()
    test_tuple_storage()
    test_immutable()

    finished("ALL REPORT TESTS PASSED")