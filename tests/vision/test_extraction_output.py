"""
tests/vision/test_extraction_output.py

Schema and output tests for the Vision extraction output contract.

Coverage
--------
1.  VisionPatient — field mapping from patient_parser dict
2.  VisionPatient — uncertain flag when all fields missing
3.  VisionLabResult — full field mapping
4.  VisionLabResult — value_uncertain when value is None
5.  VisionLabResult — reference_interval populated on success
6.  VisionLabResult — reference_unresolved_reason on failure
7.  VisionLabResult — abnormal_flag preserved from raw_name
8.  VisionLabResult — ocr_confidence / ocr_engine carried through
9.  VisionExtractionOutput — result_count property
10. VisionExtractionOutput — is_ocr_sourced property
11. _map_pipeline_result — full mapping from PipelineResult
12. _map_pipeline_result — extraction_warnings from validation issues
13. extract() — end-to-end with mocked pipeline.process
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraction.pipeline import InputType, PipelineResult, SourceMeta
from vision.extraction_output import (
    VisionExtractionOutput,
    VisionLabResult,
    VisionPatient,
    VisionReferenceInterval,
)
from vision.extractor import (
    _extract_abnormal_flag,
    _map_lab_result,
    _map_patient,
    _map_pipeline_result,
    _resolve_interval,
)


# =========================================================
# HELPERS
# =========================================================

def _make_source(
    input_type=InputType.TEXT_PDF,
    ocr_pages=0,
    ocr_confidence=None,
    warnings=None,
    path=None,
):
    return SourceMeta(
        input_type=input_type,
        path=path,
        page_count=1,
        ocr_pages=ocr_pages,
        ocr_confidence=ocr_confidence,
        warnings=warnings or [],
    )


def _make_pipeline_result(
    patient=None,
    tests=None,
    source=None,
    validation=None,
):
    return PipelineResult(
        source=source or _make_source(),
        raw_text="raw",
        cleaned_text="cleaned",
        patient=patient or {"age": 34, "age_value": 34, "age_unit": "years", "sex": "male"},
        tests=tests or [],
        coverage={},
        validation=validation or {"status": "VALID", "can_analyze": True, "issues": []},
        plausibility=None,
    )


def _make_test(
    raw_name="Hemoglobin",
    canonical_name="hemoglobin",
    value=15.9,
    unit="g/dl",
    reference_raw="13.0-18.0",
):
    return {
        "raw_name": raw_name,
        "canonical_name": canonical_name,
        "value": value,
        "unit": unit,
        "reference_raw": reference_raw,
    }


# =========================================================
# TEST 1 — VisionPatient field mapping
# =========================================================

print("\n========================================")
print("TEST 1 — VisionPatient field mapping")
print("========================================")

patient = _map_patient({
    "age": 34,
    "age_value": 34,
    "age_unit": "years",
    "sex": "male",
})

assert isinstance(patient, VisionPatient)
assert patient.age_value == 34
assert patient.age_unit == "years"
assert patient.sex == "male"
assert patient.uncertain is False
assert patient.name is None
assert patient.patient_id is None
assert patient.report_date is None

print("age_value:", patient.age_value)
print("age_unit:", patient.age_unit)
print("sex:", patient.sex)
print("uncertain:", patient.uncertain)
print("✓ PASSED")


# =========================================================
# TEST 2 — VisionPatient uncertain when all fields missing
# =========================================================

print("\n========================================")
print("TEST 2 — VisionPatient uncertain flag")
print("========================================")

empty_patient = _map_patient({"age": None, "age_value": None, "age_unit": None, "sex": None})

assert empty_patient.uncertain is True
assert empty_patient.age_value is None
assert empty_patient.sex is None

print("uncertain:", empty_patient.uncertain)
print("✓ PASSED")


# =========================================================
# TEST 3 — VisionLabResult full field mapping
# =========================================================

print("\n========================================")
print("TEST 3 — VisionLabResult full field mapping")
print("========================================")

patient_dict = {"age_value": 34, "age_unit": "years", "sex": "male"}
result = _map_lab_result(
    test=_make_test(),
    patient_dict=patient_dict,
    ocr_confidence=0.97,
    ocr_engine="paddleocr",
)

assert isinstance(result, VisionLabResult)
assert result.canonical_name == "hemoglobin"
assert result.raw_name == "Hemoglobin"
assert result.value == 15.9
assert result.unit == "g/dl"
assert result.raw_reference == "13.0-18.0"
assert result.ocr_confidence == 0.97
assert result.ocr_engine == "paddleocr"

print("canonical_name:", result.canonical_name)
print("value:", result.value)
print("unit:", result.unit)
print("ocr_confidence:", result.ocr_confidence)
print("✓ PASSED")


# =========================================================
# TEST 4 — value_uncertain when value is None
# =========================================================

print("\n========================================")
print("TEST 4 — value_uncertain when value is None")
print("========================================")

uncertain_result = _map_lab_result(
    test=_make_test(value=None),
    patient_dict={},
    ocr_confidence=0.45,
    ocr_engine="paddleocr",
)

assert uncertain_result.value is None
assert uncertain_result.value_uncertain is True

print("value_uncertain:", uncertain_result.value_uncertain)
print("✓ PASSED")


# =========================================================
# TEST 5 — reference_interval populated on successful resolve
# =========================================================

print("\n========================================")
print("TEST 5 — reference_interval on success")
print("========================================")

interval, reason = _resolve_interval(
    "13.0-18.0",
    {"age_value": 34, "age_unit": "years", "sex": "male"},
)

assert interval is not None
assert isinstance(interval, VisionReferenceInterval)
assert interval.minimum == 13.0
assert interval.maximum == 18.0
assert interval.matched_by == "report_direct"
assert reason is None

print("minimum:", interval.minimum)
print("maximum:", interval.maximum)
print("matched_by:", interval.matched_by)
print("✓ PASSED")


# =========================================================
# TEST 6 — reference_unresolved_reason on failure
# =========================================================

print("\n========================================")
print("TEST 6 — reference_unresolved_reason on failure")
print("========================================")

interval_none, reason_str = _resolve_interval(
    None,
    {"age_value": 34, "age_unit": "years", "sex": "male"},
)

assert interval_none is None
assert reason_str is not None
assert len(reason_str) > 0

print("reason:", reason_str)
print("✓ PASSED")

# Unparsable range
interval_bad, reason_bad = _resolve_interval(
    "see chart",
    {"age_value": 34, "age_unit": "years", "sex": "male"},
)

assert interval_bad is None
assert reason_bad is not None

print("unparsable reason:", reason_bad)
print("✓ PASSED")


# =========================================================
# TEST 7 — abnormal_flag preserved from raw_name
# =========================================================

print("\n========================================")
print("TEST 7 — abnormal_flag from raw_name")
print("========================================")

assert _extract_abnormal_flag("Hemoglobin H") == "H"
assert _extract_abnormal_flag("Hemoglobin L") == "L"
assert _extract_abnormal_flag("Hemoglobin HH") == "HH"
assert _extract_abnormal_flag("Hemoglobin *") == "*"
assert _extract_abnormal_flag("Hemoglobin") is None

print("H flag: OK")
print("L flag: OK")
print("HH flag: OK")
print("* flag: OK")
print("no flag: OK")
print("✓ PASSED")


# =========================================================
# TEST 8 — ocr_confidence / ocr_engine None for text PDF
# =========================================================

print("\n========================================")
print("TEST 8 — ocr_confidence/engine None for text PDF")
print("========================================")

text_pdf_result = _map_lab_result(
    test=_make_test(),
    patient_dict={"age_value": 34, "age_unit": "years", "sex": "male"},
    ocr_confidence=None,
    ocr_engine=None,
)

assert text_pdf_result.ocr_confidence is None
assert text_pdf_result.ocr_engine is None

print("ocr_confidence:", text_pdf_result.ocr_confidence)
print("ocr_engine:", text_pdf_result.ocr_engine)
print("✓ PASSED")


# =========================================================
# TEST 9 — result_count property
# =========================================================

print("\n========================================")
print("TEST 9 — result_count property")
print("========================================")

output = VisionExtractionOutput(
    patient=VisionPatient(),
    lab_results=[
        VisionLabResult(canonical_name="hemoglobin", raw_name="Hemoglobin"),
        VisionLabResult(canonical_name="wbc", raw_name="Total WBC Count"),
    ],
)

assert output.result_count == 2

print("result_count:", output.result_count)
print("✓ PASSED")


# =========================================================
# TEST 10 — is_ocr_sourced property
# =========================================================

print("\n========================================")
print("TEST 10 — is_ocr_sourced property")
print("========================================")

ocr_output = VisionExtractionOutput(patient=VisionPatient(), ocr_pages=2)
text_output = VisionExtractionOutput(patient=VisionPatient(), ocr_pages=0)

assert ocr_output.is_ocr_sourced is True
assert text_output.is_ocr_sourced is False

print("ocr_sourced (2 pages):", ocr_output.is_ocr_sourced)
print("ocr_sourced (0 pages):", text_output.is_ocr_sourced)
print("✓ PASSED")


# =========================================================
# TEST 11 — _map_pipeline_result full mapping
# =========================================================

print("\n========================================")
print("TEST 11 — _map_pipeline_result full mapping")
print("========================================")

pipeline_result = _make_pipeline_result(
    patient={"age": 34, "age_value": 34, "age_unit": "years", "sex": "male"},
    tests=[
        _make_test("Hemoglobin", "hemoglobin", 15.9, "g/dl", "13.0-18.0"),
        _make_test("Total WBC Count", "wbc", 7200, "/cmm", "4000-11000"),
    ],
    source=_make_source(
        input_type=InputType.SCANNED_PDF,
        ocr_pages=1,
        ocr_confidence=0.95,
        path="/tmp/report.pdf",
        warnings=["Page 1: low contrast"],
    ),
    validation={"status": "VALID", "can_analyze": True, "issues": []},
)

output = _map_pipeline_result(pipeline_result)

assert isinstance(output, VisionExtractionOutput)
assert output.patient.age_value == 34
assert output.patient.sex == "male"
assert output.result_count == 2
assert output.source_input_type == "scanned_pdf"
assert output.source_path == "/tmp/report.pdf"
assert output.ocr_pages == 1
assert output.ocr_confidence == 0.95
assert output.ocr_warnings == ["Page 1: low contrast"]
assert output.is_ocr_sourced is True

hgb = output.lab_results[0]
assert hgb.canonical_name == "hemoglobin"
assert hgb.value == 15.9
assert hgb.reference_interval is not None
assert hgb.reference_interval.minimum == 13.0
assert hgb.reference_interval.maximum == 18.0
assert hgb.ocr_confidence == 0.95
assert hgb.ocr_engine == "paddleocr"

print("patient.age_value:", output.patient.age_value)
print("result_count:", output.result_count)
print("source_input_type:", output.source_input_type)
print("hgb.reference_interval:", output.lab_results[0].reference_interval)
print("✓ PASSED")


# =========================================================
# TEST 12 — extraction_warnings from validation issues
# =========================================================

print("\n========================================")
print("TEST 12 — extraction_warnings from validation issues")
print("========================================")

pipeline_with_issues = _make_pipeline_result(
    validation={
        "status": "NEEDS_USER_INPUT",
        "can_analyze": False,
        "issues": [
            {"type": "USER_INPUT_REQUIRED", "field": "age", "message": "We couldn't find your age in the report."},
            {"type": "USER_INPUT_REQUIRED", "field": "sex", "message": "We couldn't find your sex in the report."},
        ],
    }
)

output_with_warnings = _map_pipeline_result(pipeline_with_issues)

assert len(output_with_warnings.extraction_warnings) == 2
assert "age" in output_with_warnings.extraction_warnings[0]

print("extraction_warnings:", output_with_warnings.extraction_warnings)
print("✓ PASSED")


# =========================================================
# TEST 13 — extract() end-to-end with mocked pipeline
# =========================================================

print("\n========================================")
print("TEST 13 — extract() end-to-end (mocked pipeline)")
print("========================================")

mock_pipeline_result = _make_pipeline_result(
    patient={"age": 25, "age_value": 25, "age_unit": "years", "sex": "female"},
    tests=[_make_test("Hemoglobin", "hemoglobin", 12.5, "g/dl", "12.0-16.0")],
    source=_make_source(
        input_type=InputType.IMAGE,
        ocr_pages=1,
        ocr_confidence=0.91,
    ),
)

with patch("vision.extractor.pipeline_process", return_value=mock_pipeline_result):
    from vision.extractor import extract
    import numpy as np

    dummy_image = np.zeros((100, 100), dtype=np.uint8)
    result = extract(dummy_image)

assert isinstance(result, VisionExtractionOutput)
assert result.patient.sex == "female"
assert result.patient.age_value == 25
assert result.result_count == 1
assert result.lab_results[0].canonical_name == "hemoglobin"
assert result.lab_results[0].value == 12.5
assert result.is_ocr_sourced is True
assert result.source_input_type == "image"

print("patient.sex:", result.patient.sex)
print("result_count:", result.result_count)
print("source_input_type:", result.source_input_type)
print("✓ PASSED")


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("   ALL EXTRACTION OUTPUT TESTS PASSED")
print("========================================")
