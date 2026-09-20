"""
Unit tests for Patient model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.models.patient import Patient
from knowledge_engine.core.enums import Sex, AgeUnit

from tests.utils import print_header, passed, finished


def test_adult_male():
    print_header("TEST 1 — ADULT MALE")

    patient = Patient(
        sex=Sex.MALE,
        age_value=34,
        age_unit=AgeUnit.YEARS,
    )

    assert patient.sex is Sex.MALE
    assert patient.age_unit is AgeUnit.YEARS

    passed()


def test_female_months():
    print_header("TEST 2 — FEMALE MONTHS")

    patient = Patient(
        sex=Sex.FEMALE,
        age_value=6,
        age_unit=AgeUnit.MONTHS,
    )

    assert patient.sex is Sex.FEMALE
    assert patient.age_unit is AgeUnit.MONTHS

    passed()


def test_unknown():
    print_header("TEST 3 — UNKNOWN SEX")

    patient = Patient(
        sex=Sex.UNKNOWN,
        age_value=10,
        age_unit=AgeUnit.YEARS,
    )

    assert patient.sex is Sex.UNKNOWN

    passed()


def test_immutable():
    print_header("TEST 4 — IMMUTABLE")

    patient = Patient(
        sex=Sex.MALE,
        age_value=20,
        age_unit=AgeUnit.YEARS,
    )

    try:
        patient.age_value = 30
        assert False, "Patient should be immutable."

    except FrozenInstanceError:
        passed()


if __name__ == "__main__":

    test_adult_male()
    test_female_months()
    test_unknown()
    test_immutable()

    finished("ALL PATIENT TESTS PASSED")