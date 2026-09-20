"""
Finding Generator.

Converts a validated LabResult into a Finding.

Responsibilities
----------------
LabResult
    ↓
ReferenceInterval.status_of(value)
    ↓
LabStatus
    ↓
Finding

This component does NOT:
- diagnose diseases
- match clinical patterns
- load YAML knowledge
- assign disease-specific severity
- invent medical thresholds
"""

from __future__ import annotations

from knowledge_engine.core.enums import LabStatus, Severity
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.lab_result import LabResult


class FindingGenerator:
    """
    Generates a Finding from a validated LabResult.
    """

    def generate(self, result: LabResult) -> Finding:
        """
        Convert one LabResult into one Finding.

        The laboratory status is determined by the
        already-resolved ReferenceInterval attached
        to the LabResult.
        """

        status = result.reference.status_of(
            result.value
        )

        reason = self._build_reason(
            result,
            status,
        )

        return Finding(
            result=result,
            status=status,
            severity=Severity.UNKNOWN,
            reason=reason,
        )

    @staticmethod
    def _build_reason(
        result: LabResult,
        status: LabStatus,
    ) -> str:
        """
        Build a transparent explanation for the
        LOW/NORMAL/HIGH classification.
        """

        minimum = result.reference.minimum
        maximum = result.reference.maximum
        value = result.value

        if status is LabStatus.LOW:
            return (
                f"{result.test_name} value {value} "
                f"is below the reference interval "
                f"{minimum}-{maximum}."
            )

        if status is LabStatus.HIGH:
            return (
                f"{result.test_name} value {value} "
                f"is above the reference interval "
                f"{minimum}-{maximum}."
            )

        if status is LabStatus.NORMAL:
            return (
                f"{result.test_name} value {value} "
                f"is within the reference interval "
                f"{minimum}-{maximum}."
            )

        return (
            f"{result.test_name} could not be classified "
            f"against the reference interval."
        )