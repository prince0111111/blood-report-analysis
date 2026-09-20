"""
Finding Requirement domain model.

Represents one laboratory condition required by
a clinical pattern.
"""

from dataclasses import dataclass

from knowledge_engine.core.enums import LabStatus, Severity


@dataclass(frozen=True, slots=True)
class FindingRequirement:
    """
    One expected laboratory finding.

    Example
    -------
    Hemoglobin must be LOW.
    """

    test_name: str

    status: LabStatus

    severity: Severity | None = None