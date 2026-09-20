"""
Tests for the first CBC knowledge pattern.
"""

from pathlib import Path

from knowledge_engine.models.pattern import Pattern
from knowledge_engine.services.registry import KnowledgeRegistry

from tests.utils import (
    print_header,
    passed,
    finished,
)


PATTERN_PATH = Path(
    "knowledge_engine/knowledge/cbc/patterns/"
    "microcytic_pattern.yaml"
)


def load_pattern():

    registry = KnowledgeRegistry()

    pattern = registry.load_file(
        PATTERN_PATH
    )

    return pattern


def test_pattern_loaded():

    print_header("TEST 1 — PATTERN LOADED")

    pattern = load_pattern()

    assert isinstance(
        pattern,
        Pattern,
    )

    assert (
        pattern.id
        == "microcytic_cbc_pattern"
    )

    passed()


def test_pattern_identity():

    print_header("TEST 2 — PATTERN IDENTITY")

    pattern = load_pattern()

    assert (
        pattern.name
        == "Microcytic CBC Pattern"
    )

    assert (
        pattern.category.value
        == "cbc"
    )

    passed()


def test_required_findings():

    print_header("TEST 3 — REQUIRED FINDINGS")

    pattern = load_pattern()

    assert len(
        pattern.required
    ) == 2

    required_names = {
        requirement.test_name
        for requirement in pattern.required
    }

    assert required_names == {
        "mcv",
        "mch",
    }

    passed()


def test_supportive_findings():

    print_header("TEST 4 — SUPPORTIVE FINDINGS")

    pattern = load_pattern()

    assert len(
        pattern.supportive
    ) == 2

    supportive_names = {
        requirement.test_name
        for requirement in pattern.supportive
    }

    assert supportive_names == {
        "hemoglobin",
        "rdw",
    }

    passed()


def test_contradictory_findings():

    print_header("TEST 5 — CONTRADICTORY FINDINGS")

    pattern = load_pattern()

    assert len(
        pattern.contradictory
    ) == 1

    assert (
        pattern.contradictory[0].test_name
        == "mcv"
    )

    passed()


def test_explanations():

    print_header("TEST 6 — EXPLANATIONS")

    pattern = load_pattern()

    assert len(
        pattern.possible_explanations
    ) == 3

    passed()


if __name__ == "__main__":

    test_pattern_loaded()
    test_pattern_identity()
    test_required_findings()
    test_supportive_findings()
    test_contradictory_findings()
    test_explanations()

    finished(
        "ALL MICROCYTIC PATTERN TESTS PASSED"
    )