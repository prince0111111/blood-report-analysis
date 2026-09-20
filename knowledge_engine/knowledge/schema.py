"""
Knowledge schema validation.

Validates the structure of YAML knowledge files before they
are converted into domain models.

This module performs structural validation only.
It does NOT determine whether medical knowledge is clinically correct.
"""

from __future__ import annotations

from typing import Any

from knowledge_engine.core.enums import LabStatus, PatternCategory, Severity


class KnowledgeSchemaError(ValueError):
    """Raised when a knowledge document violates the schema."""


class KnowledgeSchemaValidator:
    """
    Validates Version 1 clinical knowledge documents.
    """

    REQUIRED_PATTERN_FIELDS = {
        "id",
        "name",
        "category",
        "description",
    }

    OPTIONAL_PATTERN_FIELDS = {
        "priority",
        "required",
        "supportive",
        "contradictory",
        "possible_explanations",
    }

    REQUIREMENT_REQUIRED_FIELDS = {
        "test_name",
        "status",
    }

    REQUIREMENT_OPTIONAL_FIELDS = {
        "severity",
    }

    @classmethod
    def validate(cls, document: Any) -> None:
        """
        Validate a complete knowledge document.

        Raises
        ------
        KnowledgeSchemaError
            If the document is structurally invalid.
        """

        if not isinstance(document, dict):
            raise KnowledgeSchemaError(
                "Knowledge document must be a mapping/object."
            )

        cls._validate_pattern(document)

    @classmethod
    def _validate_pattern(cls, pattern: dict[str, Any]) -> None:
        """Validate the top-level pattern object."""

        missing = cls.REQUIRED_PATTERN_FIELDS - pattern.keys()

        if missing:
            raise KnowledgeSchemaError(
                f"Missing required pattern fields: "
                f"{sorted(missing)}"
            )

        unknown = (
            set(pattern.keys())
            - cls.REQUIRED_PATTERN_FIELDS
            - cls.OPTIONAL_PATTERN_FIELDS
        )

        if unknown:
            raise KnowledgeSchemaError(
                f"Unknown pattern fields: {sorted(unknown)}"
            )

        cls._require_string(pattern, "id")
        cls._require_string(pattern, "name")
        cls._require_string(pattern, "description")

        cls._validate_category(pattern["category"])

        if "priority" in pattern:
            cls._validate_priority(pattern["priority"])

        for field_name in (
            "required",
            "supportive",
            "contradictory",
        ):
            if field_name in pattern:
                cls._validate_requirements(
                    pattern[field_name],
                    field_name,
                )

        if "possible_explanations" in pattern:
            cls._validate_explanations(
                pattern["possible_explanations"]
            )

    @staticmethod
    def _require_string(
        mapping: dict[str, Any],
        field_name: str,
    ) -> None:
        """Require a non-empty string field."""

        value = mapping.get(field_name)

        if not isinstance(value, str) or not value.strip():
            raise KnowledgeSchemaError(
                f"'{field_name}' must be a non-empty string."
            )

    @staticmethod
    def _validate_category(value: Any) -> None:
        """Validate PatternCategory."""

        valid_values = {
            member.value for member in PatternCategory
        }

        if value not in valid_values:
            raise KnowledgeSchemaError(
                f"Invalid category '{value}'. "
                f"Expected one of: {sorted(valid_values)}."
            )

    @staticmethod
    def _validate_priority(value: Any) -> None:
        """Validate pattern priority."""

        if isinstance(value, bool) or not isinstance(value, int):
            raise KnowledgeSchemaError(
                "'priority' must be an integer."
            )

        if value < 0:
            raise KnowledgeSchemaError(
                "'priority' cannot be negative."
            )

    @classmethod
    def _validate_requirements(
        cls,
        requirements: Any,
        field_name: str,
    ) -> None:
        """Validate a list of finding requirements."""

        if not isinstance(requirements, list):
            raise KnowledgeSchemaError(
                f"'{field_name}' must be a list."
            )

        for index, requirement in enumerate(requirements):

            if not isinstance(requirement, dict):
                raise KnowledgeSchemaError(
                    f"'{field_name}[{index}]' must be an object."
                )

            missing = (
                cls.REQUIREMENT_REQUIRED_FIELDS
                - requirement.keys()
            )

            if missing:
                raise KnowledgeSchemaError(
                    f"'{field_name}[{index}]' is missing "
                    f"required fields: {sorted(missing)}."
                )

            unknown = (
                set(requirement.keys())
                - cls.REQUIREMENT_REQUIRED_FIELDS
                - cls.REQUIREMENT_OPTIONAL_FIELDS
            )

            if unknown:
                raise KnowledgeSchemaError(
                    f"'{field_name}[{index}]' contains "
                    f"unknown fields: {sorted(unknown)}."
                )

            test_name = requirement["test_name"]

            if (
                not isinstance(test_name, str)
                or not test_name.strip()
            ):
                raise KnowledgeSchemaError(
                    f"'{field_name}[{index}].test_name' "
                    f"must be a non-empty string."
                )

            cls._validate_status(
                requirement["status"],
                field_name,
                index,
            )

            if "severity" in requirement:
                cls._validate_severity(
                    requirement["severity"],
                    field_name,
                    index,
                )

    @staticmethod
    def _validate_status(
        value: Any,
        field_name: str,
        index: int,
    ) -> None:
        """Validate laboratory status."""

        valid_values = {
            member.value for member in LabStatus
        }

        if value not in valid_values:
            raise KnowledgeSchemaError(
                f"'{field_name}[{index}].status' has invalid "
                f"value '{value}'. Expected one of: "
                f"{sorted(valid_values)}."
            )

    @staticmethod
    def _validate_severity(
        value: Any,
        field_name: str,
        index: int,
    ) -> None:
        """Validate optional severity."""

        valid_values = {
            member.value for member in Severity
        }

        if value not in valid_values:
            raise KnowledgeSchemaError(
                f"'{field_name}[{index}].severity' has invalid "
                f"value '{value}'. Expected one of: "
                f"{sorted(valid_values)}."
            )

    @staticmethod
    def _validate_explanations(value: Any) -> None:
        """Validate possible explanations."""

        if not isinstance(value, list):
            raise KnowledgeSchemaError(
                "'possible_explanations' must be a list."
            )

        for index, explanation in enumerate(value):

            if (
                not isinstance(explanation, str)
                or not explanation.strip()
            ):
                raise KnowledgeSchemaError(
                    f"'possible_explanations[{index}]' "
                    f"must be a non-empty string."
                )