"""
Blood report domain model.
"""

from dataclasses import dataclass, field

from .lab_result import LabResult
from .patient import Patient


@dataclass(frozen=True, slots=True)
class Report:
    """
    One validated laboratory report.
    """

    patient: Patient

    lab_results: tuple[LabResult, ...] = field(default_factory=tuple)

    report_date: str | None = None

    laboratory: str | None = None

    report_id: str | None = None

    @property   
    def lab_result_count(self) -> int:
        """
        Number of laboratory results.
        """
        return len(self.lab_results)