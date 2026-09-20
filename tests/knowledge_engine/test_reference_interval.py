"""
Unit tests for ReferenceInterval.
"""

from knowledge_engine.models.reference_interval import ReferenceInterval
from knowledge_engine.core.enums import LabStatus


def print_header(title):
    print("\n" + "=" * 40)
    print(title)
    print("=" * 40)


def test_contains():
    print_header("TEST 1 — CONTAINS")

    interval = ReferenceInterval(13.0, 17.0)

    assert interval.contains(13.0)
    assert interval.contains(15.0)
    assert interval.contains(17.0)

    assert not interval.contains(12.9)
    assert not interval.contains(17.1)

    print("✓ PASSED")


def test_status():
    print_header("TEST 2 — STATUS")

    interval = ReferenceInterval(13.0, 17.0)

    assert interval.status_of(10) == LabStatus.LOW
    assert interval.status_of(13) == LabStatus.NORMAL
    assert interval.status_of(15) == LabStatus.NORMAL
    assert interval.status_of(17) == LabStatus.NORMAL
    assert interval.status_of(20) == LabStatus.HIGH

    print("✓ PASSED")


def test_width():
    print_header("TEST 3 — WIDTH")

    interval = ReferenceInterval(13.0, 17.0)

    assert interval.width == 4.0

    print(interval.width)

    print("✓ PASSED")


def test_distance_lower():
    print_header("TEST 4 — DISTANCE FROM LOWER")

    interval = ReferenceInterval(13.0, 17.0)

    assert interval.distance_from_lower(15.0) == 2.0
    assert interval.distance_from_lower(13.0) == 0.0
    assert interval.distance_from_lower(10.0) == -3.0

    print("✓ PASSED")


def test_distance_upper():
    print_header("TEST 5 — DISTANCE FROM UPPER")

    interval = ReferenceInterval(13.0, 17.0)

    assert interval.distance_from_upper(15.0) == -2.0
    assert interval.distance_from_upper(17.0) == 0.0
    assert interval.distance_from_upper(20.0) == 3.0

    print("✓ PASSED")


def test_invalid_interval():
    print_header("TEST 6 — INVALID INTERVAL")

    try:
        ReferenceInterval(17.0, 13.0)

        assert False

    except ValueError:

        print("✓ PASSED")


def test_zero_width():
    print_header("TEST 7 — ZERO WIDTH")

    interval = ReferenceInterval(13.0, 13.0)

    assert interval.contains(13.0)

    assert interval.status_of(13.0) == LabStatus.NORMAL

    assert interval.width == 0

    print("✓ PASSED")


def test_immutability():
    print_header("TEST 8 — IMMUTABLE")

    interval = ReferenceInterval(13.0, 17.0)

    try:

        interval.minimum = 15

        assert False

    except Exception:

        print("✓ PASSED")


if __name__ == "__main__":

    test_contains()

    test_status()

    test_width()

    test_distance_lower()

    test_distance_upper()

    test_invalid_interval()

    test_zero_width()

    test_immutability()

    print("\n" + "=" * 40)
    print("ALL REFERENCE INTERVAL TESTS PASSED")
    print("=" * 40)