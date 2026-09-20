"""
Application-level clinical analysis pipeline.

This module is the bridge between the existing extraction pipeline and
the already-tested clinical reasoning stack.

INPUT
-----
PDF / scanned PDF / image path / image array
        ↓
extraction.pipeline.process()
        ↓
report patient + extracted tests
        ↓
interpretation.reference_resolver
        ↓
canonical LabResult
        ↓
FindingGenerator
        ↓
KnowledgeEngine

The extraction router remains responsible for choosing PDF text extraction
or Vision/OCR. This module does not duplicate that routing logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import numpy as np

from extraction.pipeline import PipelineResult, process as extract_process
from interpretation.reference_resolver import resolve_reference_range
from knowledge_engine.models.finding import Finding
from knowledge_engine.models.lab_result import LabResult
from knowledge_engine.models.reference_interval import ReferenceInterval
from knowledge_engine.models.match_result import MatchResult
from knowledge_engine.services.engine import KnowledgeEngine
from knowledge_engine.services.generator import FindingGenerator


SourceInput = Union[str, Path, np.ndarray]


@dataclass(frozen=True, slots=True)
class UnresolvedReference:
    """One extracted test whose report reference could not be resolved."""

    test_name: str
    raw_reference: Optional[str]
    reason: str


@dataclass(frozen=True, slots=True)
class ClinicalPipelineResult:
    """Complete output of the application-level clinical pipeline."""

    extraction: PipelineResult
    lab_results: tuple[LabResult, ...] = field(default_factory=tuple)
    findings: tuple[Finding, ...] = field(default_factory=tuple)
    matches: tuple[MatchResult, ...] = field(default_factory=tuple)
    unresolved_references: tuple[UnresolvedReference, ...] = field(
        default_factory=tuple
    )

    @property
    def matched(self) -> tuple[MatchResult, ...]:
        """Return only patterns satisfying the Knowledge Engine match rules."""
        return tuple(result for result in self.matches if result.matched)


class ClinicalPipeline:
    """
    Orchestrates extraction → reference resolution → findings → knowledge.

    The class deliberately receives a KnowledgeEngine instance instead of
    loading YAML knowledge itself. Knowledge registration therefore remains
    the responsibility of the existing KnowledgeRegistry layer.
    """

    def __init__(
        self,
        engine: KnowledgeEngine,
        generator: FindingGenerator | None = None,
    ) -> None:
        self._engine = engine
        self._generator = generator or FindingGenerator()

    def run(
        self,
        source: SourceInput,
        *,
        ocr_engine=None,
        dpi: int = 300,
        force_ocr: bool = False,
    ) -> ClinicalPipelineResult:
        """
        Run the complete clinical pipeline.

        Extraction failures and validation failures are preserved in the
        returned PipelineResult. The reasoning stages are only entered when
        extraction validation says the report can be analyzed.
        """

        extraction = extract_process(
            source=source,
            ocr_engine=ocr_engine,
            dpi=dpi,
            force_ocr=force_ocr,
        )

        if not extraction.validation.get("can_analyze", False):
            return ClinicalPipelineResult(
                extraction=extraction,
            )

        lab_results: list[LabResult] = []
        findings: list[Finding] = []
        unresolved: list[UnresolvedReference] = []

        patient = extraction.patient
        tests = extraction.validation.get(
            "validated_test_data",
            extraction.tests,
        )

        for test in tests:
            test_name = test.get("canonical_name") or test.get("raw_name")
            value = test.get("value")
            unit = test.get("unit")
            raw_reference = test.get("reference_raw")

            if test_name is None or value is None or unit is None:
                continue

            resolved = resolve_reference_range(
                raw_reference,
                patient,
            )

            if not resolved.get("resolved", False):
                unresolved.append(
                    UnresolvedReference(
                        test_name=test_name,
                        raw_reference=raw_reference,
                        reason=resolved.get(
                            "reason",
                            "Reference interval could not be resolved.",
                        ),
                    )
                )
                continue

            interval = ReferenceInterval(
                minimum=resolved["min"],
                maximum=resolved["max"],
            )

            result = LabResult(
                test_name=test_name,
                raw_name=test.get("raw_name") or test_name,
                value=float(value),
                unit=str(unit),
                reference=interval,
                raw_reference=str(raw_reference) if raw_reference is not None else "",
            )

            lab_results.append(result)
            findings.append(self._generator.generate(result))

        finding_tuple = tuple(findings)
        matches = self._engine.evaluate(finding_tuple)

        return ClinicalPipelineResult(
            extraction=extraction,
            lab_results=tuple(lab_results),
            findings=finding_tuple,
            matches=matches,
            unresolved_references=tuple(unresolved),
        )