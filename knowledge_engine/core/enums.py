from enum import Enum


class Sex(str, Enum):
    """Patient biological sex."""

    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class AgeUnit(str, Enum):
    """Supported patient age units."""

    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"
    YEARS = "years"


class LabStatus(str, Enum):
    """
    Relationship between a lab value and
    its reference interval.
    """

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"

    UNKNOWN = "unknown"


class Severity(str, Enum):
    """
    Clinical severity.

    Different from LabStatus.
    """

    NORMAL = "normal"

    MILD = "mild"

    MODERATE = "moderate"

    SEVERE = "severe"

    CRITICAL = "critical"

    UNKNOWN = "unknown"


class PatternCategory(str, Enum):
    """Knowledge categories."""

    CBC = "cbc"

    LIPID = "lipid"

    LIVER = "liver"

    KIDNEY = "kidney"

    THYROID = "thyroid"

    DIABETES = "diabetes"


class MatchStrength(str, Enum):
    """
    Strength of evidence supporting
    a matched pattern.
    """

    WEAK = "weak"

    MODERATE = "moderate"

    STRONG = "strong"


class RecommendationPriority(str, Enum):
    """
    Importance of a recommendation.
    """

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    URGENT = "urgent"



class EvidenceType(str, Enum):
    REQUIRED = "required"
    SUPPORTIVE = "supportive"
    CONTRADICTORY = "contradictory"
    MISSING = "missing"