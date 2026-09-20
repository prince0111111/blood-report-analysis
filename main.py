"""
Application entry point for the Blood Report Analysis AI.

The application delegates the clinical workflow to ClinicalPipeline.

Pipeline:

    input
      -> input routing
      -> extraction
      -> validation
      -> reference resolution
      -> finding generation
      -> knowledge engine
"""

from __future__ import annotations

import sys
from pathlib import Path

from clinical_pipeline import ClinicalPipeline
from knowledge_engine.services.engine import KnowledgeEngine
from knowledge_engine.services.matcher import KnowledgeMatcher
from knowledge_engine.services.registry import KnowledgeRegistry
from knowledge_engine.services.scorer import KnowledgeScorer


DEFAULT_REPORT = Path("samples/reports/sample.png")
PATTERN_ROOT = Path("knowledge_engine/knowledge")


def get_value(obj, key, default=None):
    """
    Safely read a value from either:

    - an object with attributes
    - a dictionary

    The application entry point must not impose
    a different domain-model structure on the
    existing clinical pipeline.
    """

    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def build_knowledge_engine() -> KnowledgeEngine:
    """Load all YAML knowledge patterns."""

    registry = KnowledgeRegistry()

    pattern_files = sorted(
        PATTERN_ROOT.rglob("patterns/*.yaml")
    )

    if not pattern_files:
        raise RuntimeError(
            f"No knowledge pattern YAML files found under "
            f"{PATTERN_ROOT}"
        )

    for path in pattern_files:
        registry.load_file(path)

    return KnowledgeEngine(
        registry=registry,
        matcher=KnowledgeMatcher(),
        scorer=KnowledgeScorer(),
    )


def display_result(result) -> None:
    """Display the result returned by ClinicalPipeline."""

    extraction = result.extraction

    source = get_value(extraction, "source")

    print("\n========================================")
    print("       BLOOD REPORT ANALYSIS")
    print("========================================")

    # --------------------------------------------------
    # INPUT
    # --------------------------------------------------

    print("\nINPUT")

    if source is not None:

        print(
            "Path:",
            get_value(source, "path", "unknown"),
        )

        input_type = get_value(
            source,
            "input_type",
            "unknown",
        )

        if hasattr(input_type, "value"):
            input_type = input_type.value

        print("Type:", input_type)

        print(
            "Pages:",
            get_value(source, "page_count", 0),
        )

        print(
            "OCR pages:",
            get_value(source, "ocr_pages", 0),
        )

        ocr_confidence = get_value(
            source,
            "ocr_confidence",
        )

        if ocr_confidence is not None:
            print(
                "OCR confidence:",
                ocr_confidence,
            )

    # --------------------------------------------------
    # PATIENT
    # --------------------------------------------------

    print("\nPATIENT")

    patient = get_value(
        extraction,
        "patient",
    )

    if not patient:

        print(
            "Patient context: "
            "NOT SAFELY RESOLVED"
        )

    else:

        sex = get_value(
            patient,
            "sex",
            "unknown",
        )

        age = get_value(
            patient,
            "age_value",
        )

        if age is None:
            age = get_value(
                patient,
                "age",
            )

        age_unit = get_value(
            patient,
            "age_unit",
        )

        if hasattr(sex, "value"):
            sex = sex.value

        if hasattr(age_unit, "value"):
            age_unit = age_unit.value

        print("Sex:", sex)
        print("Age:", age)
        print("Age unit:", age_unit)

    # --------------------------------------------------
    # EXTRACTION
    # --------------------------------------------------

    print("\nEXTRACTION")

    tests = get_value(
        extraction,
        "tests",
        [],
    )

    lab_results = get_value(
        result,
        "lab_results",
        [],
    )

    print(
        "Tests extracted:",
        len(tests),
    )

    print(
        "Canonical LabResults:",
        len(lab_results),
    )

    validation = get_value(
        extraction,
        "validation",
        {},
    )

    validation_status = get_value(
        validation,
        "status",
        "unknown",
    )

    can_analyze = get_value(
        validation,
        "can_analyze",
        False,
    )

    print(
        "Validation:",
        validation_status,
    )

    print(
        "Can analyze:",
        can_analyze,
    )

    coverage = get_value(
        extraction,
        "coverage",
        {},
    )

    print(
        "CBC coverage:",
        get_value(
            coverage,
            "status",
            "unknown",
        ),
    )

    # --------------------------------------------------
    # UNRESOLVED REFERENCES
    # --------------------------------------------------

    unresolved = get_value(
        result,
        "unresolved_references",
        [],
    )

    if unresolved:

        print("\nUNRESOLVED REFERENCES")

        for item in unresolved:

            test_name = get_value(
                item,
                "test_name",
                "unknown",
            )

            reason = get_value(
                item,
                "reason",
                "Reference interval could not be resolved.",
            )

            print(
                f"- {test_name}: {reason}"
            )

    # --------------------------------------------------
    # VALIDATION GATE
    # --------------------------------------------------

    if not can_analyze:

        print("\n========================================")
        print("       ANALYSIS BLOCKED")
        print("========================================")

        reason = get_value(
            validation,
            "reason",
        )

        if reason:
            print(reason)
        else:
            print(
                "The report could not safely "
                "be analyzed."
            )

        return

    # --------------------------------------------------
    # FINDINGS
    # --------------------------------------------------

    findings = get_value(
        result,
        "findings",
        [],
    )

    print("\nFINDINGS")

    if not findings:

        print("No findings generated.")

    else:

        for finding in findings:

            status = get_value(
                finding,
                "status",
                "unknown",
            )

            if hasattr(status, "value"):
                status = status.value

            print(
                f"- {get_value(finding, 'test_name', 'unknown')}: "
                f"{get_value(finding, 'value', 'unknown')} "
                f"{get_value(finding, 'unit', '')} "
                f"→ {status}"
            )

    # --------------------------------------------------
    # KNOWLEDGE ENGINE
    # --------------------------------------------------

    matches = get_value(
        result,
        "matches",
        [],
    )

    print("\nKNOWLEDGE ENGINE")

    if not matches:

        print(
            "No knowledge patterns evaluated."
        )

        return

    for match in matches:

        pattern = get_value(
            match,
            "pattern",
        )

        pattern_id = get_value(
            pattern,
            "id",
            "unknown",
        )

        score = get_value(
            match,
            "score",
            0.0,
        )

        matched = get_value(
            match,
            "matched",
            False,
        )

        print(
            f"- {pattern_id}: "
            f"score={score:.1f}, "
            f"matched={matched}"
        )

        evidence = get_value(
            match,
            "evidence",
        )

        if evidence:

            missing = get_value(
                evidence,
                "missing_required",
                (),
            )

            contradictory = get_value(
                evidence,
                "contradictory",
                (),
            )

            if missing:

                print(
                    "  missing required:",
                    ", ".join(missing),
                )

            if contradictory:

                names = [
                    get_value(
                        finding,
                        "test_name",
                        "unknown",
                    )
                    for finding in contradictory
                ]

                print(
                    "  contradictory:",
                    ", ".join(names),
                )


def main() -> int:
    """Run one report through the complete pipeline."""

    report_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else DEFAULT_REPORT
    )

    if not report_path.exists():

        print(
            f"ERROR: report does not exist: "
            f"{report_path}"
        )

        return 1

    try:

        engine = build_knowledge_engine()

        pipeline = ClinicalPipeline(
            engine=engine,
        )

        result = pipeline.run(
            report_path,
        )

        display_result(result)

        # A clinically blocked report is still a
        # successful application execution.
        #
        # Therefore:
        #
        #   unsafe input -> pipeline blocks it -> 0
        #
        # while:
        #
        #   application crash -> 1

        return 0

    except Exception as exc:

        print(
            f"ERROR: {type(exc).__name__}: {exc}"
        )

        return 1


if __name__ == "__main__":
    raise SystemExit(main())