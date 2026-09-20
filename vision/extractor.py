"""
vision/extractor.py

Adapter: existing extraction pipeline → VisionExtractionOutput.

RESPONSIBILITIES
----------------
- Accept any input supported by extraction.pipeline.process()
  (text PDF, scanned PDF, numpy image array).
- For text PDFs: call extraction.pipeline.process() unchanged.
- For OCR-sourced inputs: additionally run vision.layout_parser
  on the raw OCR text to improve multi-layout support, then
  merge with the existing pipeline's patient context.
- Map PipelineResult → VisionExtractionOutput using the
  existing reference_resolver for interval parsing.
- Carry OCR confidence / source metadata through.
- Mark uncertainty; never invent values.

DOES NOT
--------
- Compute LOW / NORMAL / HIGH.
- Add medical interpretation rules.
- Duplicate extraction or OCR logic.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Union

import numpy as np

from extraction.pipeline import PipelineResult, process as pipeline_process
from interpretation.reference_resolver import resolve_reference_range
from vision.extraction_output import (
    VisionExtractionOutput,
    VisionLabResult,
    VisionPatient,
    VisionReferenceInterval,
)
from vision.layout_parser import parse_ocr_text


# =========================================================
# ABNORMAL FLAG PATTERN
# =========================================================

_ABNORMAL_FLAG_RE = re.compile(
    r"(?<![\w])(H{1,2}|L{1,2}|\*|A)(?![\w])"
)


def _extract_abnormal_flag(raw_name: str) -> Optional[str]:
    """
    Return an explicit abnormal flag if one is embedded in
    the raw test-name token.  Returns None when not found.
    """
    match = _ABNORMAL_FLAG_RE.search(raw_name)
    return match.group(1) if match else None


# =========================================================
# PATIENT MAPPING
# =========================================================

def _map_patient(patient_dict: dict) -> VisionPatient:
    age_value = patient_dict.get("age_value")
    age_unit = patient_dict.get("age_unit")
    sex = patient_dict.get("sex")

    uncertain = (
        age_value is None
        and age_unit is None
        and sex is None
    )

    return VisionPatient(
        age_value=age_value,
        age_unit=age_unit,
        sex=sex,
        uncertain=uncertain,
    )


# =========================================================
# REFERENCE INTERVAL MAPPING
# =========================================================

def _resolve_interval(
    reference_raw: Optional[str],
    patient_dict: dict,
) -> tuple[Optional[VisionReferenceInterval], Optional[str]]:
    """
    Call the existing reference_resolver and return
    (VisionReferenceInterval | None, unresolved_reason | None).
    """
    if not reference_raw:
        return None, "Reference interval missing from source."

    result = resolve_reference_range(reference_raw, patient_dict)

    if result.get("resolved"):
        interval = VisionReferenceInterval(
            minimum=result["min"],
            maximum=result["max"],
            matched_by=result["matched_by"],
        )
        return interval, None

    return None, result.get("reason")


# =========================================================
# LAB RESULT MAPPING
# =========================================================

def _map_lab_result(
    test: dict,
    patient_dict: dict,
    ocr_confidence: Optional[float],
    ocr_engine: Optional[str],
) -> VisionLabResult:
    """
    Map one parsed test dict to a VisionLabResult.

    Accepts dicts from both extraction.parser.parse_cbc()
    and vision.layout_parser.parse_ocr_text() — both use
    the same key schema.
    """
    raw_name = test.get("raw_name") or ""
    canonical_name = test.get("canonical_name") or raw_name
    value = test.get("value")
    unit = test.get("unit")
    reference_raw = test.get("reference_raw")

    # Prefer explicit flag from layout_parser; fall back to
    # scanning the raw_name token.
    flag = test.get("abnormal_flag") or _extract_abnormal_flag(raw_name)

    interval, unresolved_reason = _resolve_interval(
        reference_raw, patient_dict
    )

    return VisionLabResult(
        canonical_name=canonical_name,
        raw_name=raw_name,
        value=value,
        unit=unit,
        raw_reference=reference_raw,
        reference_interval=interval,
        reference_unresolved_reason=unresolved_reason,
        abnormal_flag=flag,
        value_uncertain=(value is None),
        ocr_confidence=ocr_confidence,
        ocr_engine=ocr_engine,
    )


# =========================================================
# MERGE STRATEGY
# =========================================================

def _merge_tests(
    pipeline_tests: list[dict],
    layout_tests: list[dict],
) -> list[dict]:
    """
    Merge test lists from the existing pipeline and the
    layout parser.

    Strategy:
    - Start with layout_parser results (richer layout support).
    - Fill in any canonical names found only by the pipeline
      parser (vertical format already handled by pipeline).
    - Deduplicate by canonical_name, keeping the first entry.
    """
    seen: set[str] = set()
    merged: list[dict] = []

    for t in layout_tests + pipeline_tests:
        key = t.get("canonical_name")
        if key and key not in seen:
            seen.add(key)
            merged.append(t)

    return merged


# =========================================================
# PIPELINE RESULT → OUTPUT CONTRACT
# =========================================================

def _map_pipeline_result(
    result: PipelineResult,
    use_layout_parser: bool = False,
) -> VisionExtractionOutput:
    """
    Convert a PipelineResult into a VisionExtractionOutput.

    When use_layout_parser is True (OCR-sourced input),
    the layout parser is run on the raw text and its results
    are merged with the pipeline's parsed tests.
    """
    source = result.source
    patient_dict = result.patient

    patient = _map_patient(patient_dict)

    ocr_confidence = source.ocr_confidence
    ocr_engine = "paddleocr" if source.ocr_pages > 0 else None

    # Choose test list
    if use_layout_parser:
        layout_tests = parse_ocr_text(result.raw_text)
        tests = _merge_tests(result.tests, layout_tests)
    else:
        tests = result.tests

    lab_results = [
        _map_lab_result(
            test=t,
            patient_dict=patient_dict,
            ocr_confidence=ocr_confidence,
            ocr_engine=ocr_engine,
        )
        for t in tests
    ]

    extraction_warnings: list[str] = []
    validation = result.validation or {}
    for issue in validation.get("issues", []):
        if isinstance(issue, dict):
            msg = issue.get("message")
            if msg:
                extraction_warnings.append(msg)

    return VisionExtractionOutput(
        patient=patient,
        lab_results=lab_results,
        source_input_type=source.input_type.value,
        source_path=source.path,
        ocr_pages=source.ocr_pages,
        ocr_confidence=ocr_confidence,
        ocr_warnings=list(source.warnings),
        extraction_warnings=extraction_warnings,
    )


# =========================================================
# PUBLIC API
# =========================================================

def extract(
    source: Union[str, Path, np.ndarray],
    ocr_engine=None,
    dpi: int = 300,
    force_ocr: bool = False,
) -> VisionExtractionOutput:
    """
    Run the full vision extraction pipeline and return a
    validated structured output.

    Parameters
    ----------
    source : str | Path | np.ndarray
        PDF file path or pre-rendered image array.
    ocr_engine : BaseOCREngine | None
        OCR engine.  Defaults to PaddleOCREngine when needed.
    dpi : int
        Render DPI for scanned PDF pages.
    force_ocr : bool
        Force OCR even for text PDFs.

    Returns
    -------
    VisionExtractionOutput
    """
    pipeline_result = pipeline_process(
        source=source,
        ocr_engine=ocr_engine,
        dpi=dpi,
        force_ocr=force_ocr,
    )

    # Use layout parser for any OCR-sourced input
    use_layout = pipeline_result.source.ocr_pages > 0

    return _map_pipeline_result(pipeline_result, use_layout_parser=use_layout)
