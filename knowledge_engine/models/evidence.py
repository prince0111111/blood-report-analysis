"""
Evidence domain model.

Represents the evidence collected for one
matched clinical pattern.
"""

from dataclasses import dataclass, field

from .finding import Finding


@dataclass(frozen=True, slots=True)
class Evidence:
    """
    Patient-specific evidence for one pattern.
    """

    matched_required: tuple[Finding, ...] = field(default_factory=tuple)

    matched_supportive: tuple[Finding, ...] = field(default_factory=tuple)

    missing_required: tuple[str, ...] = field(default_factory=tuple)

    contradictory: tuple[Finding, ...] = field(default_factory=tuple)