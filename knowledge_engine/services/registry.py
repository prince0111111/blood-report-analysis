"""
Knowledge registry.

Responsible for:
1. Loading knowledge documents.
2. Validating their schema.
3. Converting them into Pattern domain objects.
4. Storing and retrieving registered patterns.

The registry does not perform clinical matching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from knowledge_engine.core.enums import (
    LabStatus,
    PatternCategory,
    Severity,
)

from knowledge_engine.knowledge.schema import (
    KnowledgeSchemaValidator,
)

from knowledge_engine.models.finding_requirement import (
    FindingRequirement,
)

from knowledge_engine.models.pattern import Pattern


class KnowledgeRegistryError(ValueError):
    """Raised when knowledge cannot be registered or loaded."""


class KnowledgeRegistry:
    """
    Stores validated clinical knowledge as Pattern objects.
    """

    def __init__(self) -> None:
        self._patterns: dict[str, Pattern] = {}

    def register(self, document: dict[str, Any]) -> Pattern:
        """
        Convert one validated knowledge document into a Pattern
        and register it.
        """

        pattern = self._build_pattern(document)

        if pattern.id in self._patterns:
            raise KnowledgeRegistryError(
                f"Pattern '{pattern.id}' is already registered."
            )

        self._patterns[pattern.id] = pattern

        return pattern

    def load_file(self, path: str | Path) -> Pattern:
        """
        Load one YAML knowledge file, validate it,
        convert it into a Pattern, and register it.
        """

        file_path = Path(path)

        if not file_path.exists():
            raise KnowledgeRegistryError(
                f"Knowledge file does not exist: {file_path}"
            )

        if not file_path.is_file():
            raise KnowledgeRegistryError(
                f"Knowledge path is not a file: {file_path}"
            )

        try:
            with file_path.open(
                "r",
                encoding="utf-8",
            ) as handle:
                document = yaml.safe_load(handle)

        except yaml.YAMLError as exc:
            raise KnowledgeRegistryError(
                f"Invalid YAML file: {file_path}"
            ) from exc

        try:
            KnowledgeSchemaValidator.validate(document)

        except Exception as exc:
            raise KnowledgeRegistryError(
                f"Knowledge schema validation failed "
                f"for '{file_path}': {exc}"
            ) from exc

        return self.register(document)

    def get(self, pattern_id: str) -> Pattern:
        """
        Retrieve a registered pattern by ID.
        """

        try:
            return self._patterns[pattern_id]

        except KeyError as exc:
            raise KnowledgeRegistryError(
                f"Pattern '{pattern_id}' is not registered."
            ) from exc

    def all(self) -> tuple[Pattern, ...]:
        """
        Return all registered patterns.
        """

        return tuple(self._patterns.values())

    def count(self) -> int:
        """
        Return the number of registered patterns.
        """

        return len(self._patterns)

    @staticmethod
    def _build_pattern(
        document: dict[str, Any],
    ) -> Pattern:
        """
        Convert validated dictionary data into a Pattern.
        """

        return Pattern(
            id=document["id"],
            name=document["name"],
            category=PatternCategory(
                document["category"]
            ),
            description=document["description"],
            priority=document.get("priority", 100),
            required=KnowledgeRegistry._build_requirements(
                document.get("required", [])
            ),
            supportive=KnowledgeRegistry._build_requirements(
                document.get("supportive", [])
            ),
            contradictory=KnowledgeRegistry._build_requirements(
                document.get("contradictory", [])
            ),
            possible_explanations=tuple(
                document.get(
                    "possible_explanations",
                    [],
                )
            ),
        )

    @staticmethod
    def _build_requirements(
        requirements: list[dict[str, Any]],
    ) -> tuple[FindingRequirement, ...]:
        """
        Convert requirement dictionaries into
        FindingRequirement objects.
        """

        return tuple(
            FindingRequirement(
                test_name=item["test_name"],
                status=LabStatus(item["status"]),
                severity=(
                    Severity(item["severity"])
                    if item.get("severity") is not None
                    else None
                ),
            )
            for item in requirements
        )