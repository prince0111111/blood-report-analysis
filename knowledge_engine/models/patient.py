"""
Patient domain model.
"""

from dataclasses import dataclass

from knowledge_engine.core.enums import AgeUnit, Sex


@dataclass(frozen=True, slots=True)
class Patient:
    """
    Represents the patient whose laboratory
    report is being interpreted.
    """

    sex: Sex

    age_value: float

    age_unit: AgeUnit