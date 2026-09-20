"""
Clinical Pattern domain model.

Represents one medical knowledge pattern.
"""

from dataclasses import dataclass, field

from knowledge_engine.core.enums import PatternCategory

from .finding_requirement import FindingRequirement


@dataclass(frozen=True, slots=True)
class Pattern:
    """
    One clinical reasoning pattern.
    """

    id: str

    name: str

    category: PatternCategory

    description: str

    priority: int = 100

    required: tuple[FindingRequirement, ...] = field(default_factory=tuple)

    supportive: tuple[FindingRequirement, ...] = field(default_factory=tuple)

    contradictory: tuple[FindingRequirement, ...] = field(default_factory=tuple)

    possible_explanations: tuple[str, ...] = field(default_factory=tuple)