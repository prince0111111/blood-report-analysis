"""
Clinical Finding domain model.

A Finding is the standardized clinical interpretation
of one laboratory result.
"""

from dataclasses import dataclass

from knowledge_engine.core.enums import LabStatus, Severity
from .lab_result import LabResult


@dataclass(frozen=True, slots=True)
class Finding:
    """
    Represents one interpreted laboratory finding.

    Example
    -------
    Hemoglobin

        value = 11.2
        status = LOW
        severity = UNKNOWN
    """

    result: LabResult

    status: LabStatus

    severity: Severity = Severity.UNKNOWN

    reason: str | None = None

    @property
    def test_name(self) -> str:
        """
        Canonical laboratory test name.
        """
        return self.result.test_name

    @property
    def value(self) -> float:
        """
        Laboratory value.
        """
        return self.result.value

    @property
    def unit(self) -> str:
        """
        Laboratory unit.
        """
        return self.result.unit