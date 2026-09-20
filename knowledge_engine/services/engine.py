"""
Knowledge Engine orchestration service.

The KnowledgeEngine coordinates:

    registered patterns
            ↓
        KnowledgeMatcher
            ↓
        KnowledgeScorer
            ↓
        MatchResults

It does not contain clinical rules itself.
Clinical knowledge lives in Pattern definitions.
"""

from __future__ import annotations

from knowledge_engine.models.finding import Finding
from knowledge_engine.models.match_result import MatchResult

from .matcher import KnowledgeMatcher
from .registry import KnowledgeRegistry
from .scorer import KnowledgeScorer


class KnowledgeEngine:
    """
    Main orchestration layer for the knowledge engine.
    """

    def __init__(
        self,
        registry: KnowledgeRegistry,
        matcher: KnowledgeMatcher | None = None,
        scorer: KnowledgeScorer | None = None,
    ) -> None:

        self._registry = registry

        self._matcher = (
            matcher
            if matcher is not None
            else KnowledgeMatcher()
        )

        self._scorer = (
            scorer
            if scorer is not None
            else KnowledgeScorer()
        )

    def evaluate(
        self,
        findings: tuple[Finding, ...],
    ) -> tuple[MatchResult, ...]:
        """
        Evaluate patient findings against every
        registered knowledge pattern.

        Returns results in registry order.
        """

        results: list[MatchResult] = []

        for pattern in self._registry.all():

            match = self._matcher.match(
                findings,
                pattern,
            )

            score = self._scorer.score(
                match
            )

            result = MatchResult(
                pattern=match.pattern,
                evidence=match.evidence,
                score=score,
                matched=match.matched,
            )

            results.append(result)

        return tuple(results)

    def evaluate_matched(
        self,
        findings: tuple[Finding, ...],
    ) -> tuple[MatchResult, ...]:
        """
        Evaluate findings and return only patterns
        that satisfy all required conditions and
        contain no contradictory evidence.
        """

        return tuple(
            result
            for result in self.evaluate(findings)
            if result.matched
        )

    def evaluate_ranked(
        self,
        findings: tuple[Finding, ...],
    ) -> tuple[MatchResult, ...]:
        """
        Evaluate all patterns and return them ordered
        from highest score to lowest score.

        Ties preserve registry order.
        """

        results = self.evaluate(findings)

        return tuple(
            sorted(
                results,
                key=lambda result: result.score,
                reverse=True,
            )
        )