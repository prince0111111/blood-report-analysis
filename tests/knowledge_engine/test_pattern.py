"""
Unit tests for Pattern model.
"""

from dataclasses import FrozenInstanceError

from knowledge_engine.core.enums import LabStatus, PatternCategory
from knowledge_engine.models.finding_requirement import FindingRequirement
from knowledge_engine.models.pattern import Pattern

from tests.utils import print_header, passed, finished


def requirement():

    return FindingRequirement(
        test_name="hemoglobin",
        status=LabStatus.LOW,
    )


def test_creation():

    print_header("TEST 1 — CREATION")

    pattern = Pattern(
        id="microcytic_anemia",
        name="Microcytic Anemia",
        category=PatternCategory.CBC,
        description="Pattern of microcytic anemia.",
    )

    assert pattern.id == "microcytic_anemia"

    passed()


def test_required():

    print_header("TEST 2 — REQUIRED FINDINGS")

    pattern = Pattern(
        id="x",
        name="X",
        category=PatternCategory.CBC,
        description="Test",
        required=(requirement(),),
    )

    assert len(pattern.required) == 1

    passed()


def test_supportive():

    print_header("TEST 3 — SUPPORTIVE")

    pattern = Pattern(
        id="x",
        name="X",
        category=PatternCategory.CBC,
        description="Test",
        supportive=(requirement(),),
    )

    assert len(pattern.supportive) == 1

    passed()


def test_priority():

    print_header("TEST 4 — PRIORITY")

    pattern = Pattern(
        id="x",
        name="X",
        category=PatternCategory.CBC,
        description="Test",
        priority=250,
    )

    assert pattern.priority == 250

    passed()


def test_immutable():

    print_header("TEST 5 — IMMUTABLE")

    pattern = Pattern(
        id="x",
        name="X",
        category=PatternCategory.CBC,
        description="Test",
    )

    try:

        pattern.priority = 10

        assert False

    except FrozenInstanceError:

        passed()


if __name__ == "__main__":

    test_creation()
    test_required()
    test_supportive()
    test_priority()
    test_immutable()

    finished("ALL PATTERN TESTS PASSED")