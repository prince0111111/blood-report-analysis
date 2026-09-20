"""
Reference Interval Domain Model.

Represents one resolved laboratory reference interval after
all age/sex specific resolution has been completed.

This class is intentionally mathematical only.
It does NOT contain any medical reasoning.
"""

from dataclasses import dataclass

from knowledge_engine.core.enums import LabStatus


@dataclass(frozen=True, slots=True)
class ReferenceInterval:
    """
    Numeric laboratory reference interval.

    Example
    -------
    Hemoglobin

        minimum = 13.0
        maximum = 17.0
    """

    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        """
        Validate interval consistency.
        """
        if self.minimum > self.maximum:
            raise ValueError(
                "Reference interval minimum cannot be greater than maximum."
            )

    @property
    def width(self) -> float:
        """
        Width of the interval.

        Example:
            13.0–17.0 -> 4.0
        """
        return self.maximum - self.minimum

    def contains(self, value: float) -> bool:
        """
        Returns True if value lies inside
        the reference interval.
        """
        return self.minimum <= value <= self.maximum

    def status_of(self, value: float) -> LabStatus:
        """
        Determine whether a value is
        LOW, NORMAL or HIGH relative
        to this interval.
        """

        if value < self.minimum:
            return LabStatus.LOW

        if value > self.maximum:
            return LabStatus.HIGH

        return LabStatus.NORMAL

    def distance_from_lower(self, value: float) -> float:
        """
        Distance from the lower boundary.

        Positive:
            value is above minimum

        Negative:
            value is below minimum
        """
        return value - self.minimum

    def distance_from_upper(self, value: float) -> float:
        """
        Distance from the upper boundary.

        Positive:
            value is above maximum

        Negative:
            value is below maximum
        """
        return value - self.maximum