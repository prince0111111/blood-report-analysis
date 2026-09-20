"""
Knowledge pattern matcher.

Compares patient Findings against a knowledge Pattern.

The matcher determines:
- required findings that matched
- supportive findings that matched
- required findings that are missing
- contradictory findings

The matcher does NOT:
- diagnose disease
- calculate the clinical score
- generate recommendations
- use an LLM
"""

from __future__ import annotations

from knowledge_engine.models.evidence import Evidence
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.match_result import MatchResult
from knowledge_engine.models.pattern import Pattern


class KnowledgeMatcher:
    """
    Deterministic matcher between patient findings
    and a knowledge pattern.
    """

    def match(
        self,
        findings: tuple[Finding, ...],
        pattern: Pattern,
    ) -> MatchResult:
        """
        Match patient findings against one pattern.
        """

        finding_map = {
            finding.test_name: finding
            for finding in findings
        }

        matched_required: list[Finding] = []
        matched_supportive: list[Finding] = []

        missing_required: list[str] = []
        contradictory: list[Finding] = []

        # -----------------------------------------
        # REQUIRED
        # -----------------------------------------

        for requirement in pattern.required:

            finding = finding_map.get(
                requirement.test_name
            )

            if finding is None:
                missing_required.append(
                    requirement.test_name
                )
                continue

            if self._matches_requirement(
                finding,
                requirement,
            ):
                matched_required.append(
                    finding
                )
            else:
                missing_required.append(
                    requirement.test_name
                )

        # -----------------------------------------
        # SUPPORTIVE
        # -----------------------------------------

        for requirement in pattern.supportive:

            finding = finding_map.get(
                requirement.test_name
            )

            if finding is None:
                continue

            if self._matches_requirement(
                finding,
                requirement,
            ):
                matched_supportive.append(
                    finding
                )

        # -----------------------------------------
        # CONTRADICTORY
        # -----------------------------------------

        for requirement in pattern.contradictory:

            finding = finding_map.get(
                requirement.test_name
            )

            if finding is None:
                continue

            if self._matches_requirement(
                finding,
                requirement,
            ):
                contradictory.append(
                    finding
                )

        # -----------------------------------------
        # EVIDENCE
        # -----------------------------------------

        evidence = Evidence(
            matched_required=tuple(
                matched_required
            ),
            matched_supportive=tuple(
                matched_supportive
            ),
            missing_required=tuple(
                missing_required
            ),
            contradictory=tuple(
                contradictory
            ),
        )

        # -----------------------------------------
        # MATCH STATUS
        # -----------------------------------------

        matched = (
            len(missing_required) == 0
            and len(contradictory) == 0
        )

        # Scoring belongs to the Scorer component.
        score = 0.0

        return MatchResult(
            pattern=pattern,
            evidence=evidence,
            score=score,
            matched=matched,
        )

    @staticmethod
    def _matches_requirement(
        finding: Finding,
        requirement,
    ) -> bool:
        """
        Check whether a Finding satisfies
        a FindingRequirement.
        """

        if finding.status != requirement.status:
            return False

        if (
            requirement.severity is not None
            and finding.severity
            != requirement.severity
        ):
            return False

        return True