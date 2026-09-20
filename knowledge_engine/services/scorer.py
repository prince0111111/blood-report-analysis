"""
Knowledge pattern scorer.

Calculates a deterministic evidence score for
one MatchResult.

The scorer does NOT:
- perform matching
- determine LOW/NORMAL/HIGH
- diagnose disease
- generate recommendations
- use an LLM
"""

from __future__ import annotations

from knowledge_engine.models.match_result import MatchResult


class KnowledgeScorer:
    """
    Deterministic scorer for pattern evidence.

    Score range:
        0.0 - 100.0
    """

    REQUIRED_WEIGHT = 70.0
    SUPPORTIVE_WEIGHT = 30.0
    CONTRADICTORY_PENALTY = 25.0

    def score(self, result: MatchResult) -> float:
        """
        Calculate the evidence score for a MatchResult.
        """

        pattern = result.pattern
        evidence = result.evidence

        required_total = len(pattern.required)
        supportive_total = len(pattern.supportive)

        required_coverage = self._coverage(
            len(evidence.matched_required),
            required_total,
        )

        supportive_coverage = self._coverage(
            len(evidence.matched_supportive),
            supportive_total,
        )

        score = (
            required_coverage
            * self.REQUIRED_WEIGHT
        )

        score += (
            supportive_coverage
            * self.SUPPORTIVE_WEIGHT
        )

        if evidence.contradictory:
            score -= self.CONTRADICTORY_PENALTY

        return self._clamp(score)

    @staticmethod
    def _coverage(
        matched: int,
        total: int,
    ) -> float:
        """
        Calculate normalized coverage.

        Returns:
            0.0 when there is nothing matched.
            1.0 when everything is matched.
        """

        if total == 0:
            return 0.0

        return matched / total

    @staticmethod
    def _clamp(score: float) -> float:
        """
        Keep score inside the public 0-100 range.
        """

        return max(
            0.0,
            min(100.0, score),
        )