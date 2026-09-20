"""
Tests for knowledge schema validation.
"""

from knowledge_engine.knowledge.schema import (
    KnowledgeSchemaError,
    KnowledgeSchemaValidator,
)

from tests.utils import print_header, passed, finished


def valid_pattern():
    return {
        "id": "example_cbc_pattern",
        "name": "Example CBC Pattern",
        "category": "cbc",
        "description": "Synthetic test pattern.",
        "priority": 100,
        "required": [
            {
                "test_name": "hemoglobin",
                "status": "low",
            },
            {
                "test_name": "mcv",
                "status": "low",
            },
        ],
        "supportive": [
            {
                "test_name": "rdw",
                "status": "high",
            },
        ],
        "contradictory": [
            {
                "test_name": "mcv",
                "status": "high",
            },
        ],
        "possible_explanations": [
            "Synthetic explanation.",
        ],
    }


def test_valid_pattern():

    print_header("TEST 1 — VALID PATTERN")

    KnowledgeSchemaValidator.validate(
        valid_pattern()
    )

    passed()


def test_missing_id():

    print_header("TEST 2 — MISSING ID")

    document = valid_pattern()
    del document["id"]

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_invalid_status():

    print_header("TEST 3 — INVALID STATUS")

    document = valid_pattern()

    document["required"][0]["status"] = "maybe"

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_missing_test_name():

    print_header("TEST 4 — MISSING TEST NAME")

    document = valid_pattern()

    del document["required"][0]["test_name"]

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_invalid_priority():

    print_header("TEST 5 — INVALID PRIORITY")

    document = valid_pattern()

    document["priority"] = "high"

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_invalid_requirement():

    print_header("TEST 6 — INVALID REQUIREMENT")

    document = valid_pattern()

    document["required"] = [
        "hemoglobin"
    ]

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_unknown_field():

    print_header("TEST 7 — UNKNOWN FIELD")

    document = valid_pattern()

    document["something_random"] = True

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_invalid_category():

    print_header("TEST 8 — INVALID CATEGORY")

    document = valid_pattern()

    document["category"] = "not_a_real_category"

    try:
        KnowledgeSchemaValidator.validate(document)
        assert False

    except KnowledgeSchemaError:
        passed()


def test_invalid_document():

    print_header("TEST 9 — INVALID DOCUMENT TYPE")

    try:
        KnowledgeSchemaValidator.validate(
            ["this", "is", "wrong"]
        )

        assert False

    except KnowledgeSchemaError:
        passed()


if __name__ == "__main__":

    test_valid_pattern()
    test_missing_id()
    test_invalid_status()
    test_missing_test_name()
    test_invalid_priority()
    test_invalid_requirement()
    test_unknown_field()
    test_invalid_category()
    test_invalid_document()

    finished(
        "ALL KNOWLEDGE SCHEMA TESTS PASSED"
    )