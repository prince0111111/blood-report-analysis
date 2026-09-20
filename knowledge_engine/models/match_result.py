"""
Match Result domain model.

Represents the result of matching one
clinical pattern against one patient's findings.
"""

from dataclasses import dataclass

from .pattern import Pattern
from .evidence import Evidence


@dataclass(frozen=True, slots=True)
class MatchResult:
    """
    One completed pattern match.
    """

    pattern: Pattern

    evidence: Evidence

    score: float

    matched: bool