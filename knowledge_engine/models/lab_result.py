"""
Laboratory result domain model.
"""

from dataclasses import dataclass

from .reference_interval import ReferenceInterval


@dataclass(frozen=True, slots=True)
class LabResult:
    """
    One validated laboratory measurement.
    """

    test_name: str

    raw_name: str

    value: float

    unit: str

    reference: ReferenceInterval

    raw_reference: str