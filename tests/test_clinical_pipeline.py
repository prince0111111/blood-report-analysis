"""Tests for the application-level clinical pipeline."""

from pathlib import Path
from unittest.mock import patch

from clinical_pipeline import ClinicalPipeline
from extraction.pipeline import InputType, PipelineResult, SourceMeta
from knowledge_engine.models.match_result import MatchResult
from knowledge_engine.services.engine import KnowledgeEngine
from knowledge_engine.services.registry import KnowledgeRegistry


ROOT = Path(__file__).resolve().parents[1]
PATTERN = ROOT / "knowledge_engine" / "knowledge" / "cbc" / "patterns" / "microcytic_pattern.yaml"


def _registry() -> KnowledgeRegistry:
    registry = KnowledgeRegistry()
    registry.load_file(PATTERN)
    return registry


def _extraction_result() -> PipelineResult:
    tests = [
        {
            "raw_name": "M.C.V.",
            "canonical_name": "mcv",
            "value": 65.0,
            "unit": "fl",
            "reference_raw": "[80-100]",
        },
        {
            "raw_name": "M.C.H.",
            "canonical_name": "mch",
            "value": 20.0,
            "unit": "pg",
            "reference_raw": "[27-32]",
        },
    ]

    validation = {
        "status": "VALID",
        "can_analyze": True,
        "patient": {
            "age": 34,
            "age_value": 34,
            "age_unit": "years",
            "sex": "male",
        },
        "tests_detected": 2,
        "valid_tests": 2,
        "validated_test_data": tests,
        "issues": [],
        "user_questions": [],
    }

    return PipelineResult(
        source=SourceMeta(input_type=InputType.TEXT_PDF),
        raw_text="synthetic",
        cleaned_text="synthetic",
        patient=validation["patient"],
        tests=tests,
        coverage={"status": "COMPLETE"},
        validation=validation,
        plausibility=None,
    )


print("\n========================================")
print("TEST 1 — EXTRACTION → REFERENCE → FINDING")
print("========================================")

engine = KnowledgeEngine(_registry())
pipeline = ClinicalPipeline(engine)

with patch("clinical_pipeline.extract_process", return_value=_extraction_result()):
    result = pipeline.run("samples/reports/sample.pdf")

assert len(result.lab_results) == 2
assert len(result.findings) == 2
assert result.findings[0].test_name == "mcv"
assert result.findings[0].status.value == "low"
assert result.findings[1].test_name == "mch"
assert result.findings[1].status.value == "low"
assert result.lab_results[0].reference.minimum == 80.0
assert result.lab_results[0].reference.maximum == 100.0
print("✓ PASSED")


print("\n========================================")
print("TEST 2 — FINDINGS → KNOWLEDGE ENGINE")
print("========================================")

assert len(result.matches) == 1
assert isinstance(result.matches[0], MatchResult)
assert result.matches[0].pattern.id == "microcytic_cbc_pattern"
assert result.matches[0].matched is True
assert result.matches[0].score > 0
print("pattern:", result.matches[0].pattern.id)
print("score:", result.matches[0].score)
print("✓ PASSED")


print("\n========================================")
print("TEST 3 — VALIDATION GATE STOPS REASONING")
print("========================================")

blocked = _extraction_result()
blocked.validation["can_analyze"] = False
blocked.validation["status"] = "NEEDS_USER_INPUT"

with patch("clinical_pipeline.extract_process", return_value=blocked):
    result_blocked = pipeline.run("samples/reports/sample.pdf")

assert result_blocked.lab_results == ()
assert result_blocked.findings == ()
assert result_blocked.matches == ()
assert result_blocked.extraction.validation["status"] == "NEEDS_USER_INPUT"
print("✓ PASSED")


print("\n========================================")
print("TEST 4 — UNRESOLVED REFERENCE IS NOT INVENTED")
print("========================================")

unresolved = _extraction_result()
unresolved.validation["validated_test_data"][0]["reference_raw"] = "not-a-range"

with patch("clinical_pipeline.extract_process", return_value=unresolved):
    result_unresolved = pipeline.run("samples/reports/sample.pdf")

assert len(result_unresolved.unresolved_references) == 1
assert result_unresolved.unresolved_references[0].test_name == "mcv"
assert len(result_unresolved.lab_results) == 1
assert len(result_unresolved.findings) == 1
print("unresolved:", result_unresolved.unresolved_references[0].reason)
print("✓ PASSED")


print("\n========================================")
print("ALL CLINICAL PIPELINE TESTS PASSED")
print("========================================")