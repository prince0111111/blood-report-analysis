"""
vision/extraction_output.py

Output contract for the Vision extraction pipeline.

PIPELINE
--------
    Blood Report Image / Scanned PDF
        ↓  vision.scanned_pdf_reader  (render → preprocess → OCR)
        ↓  extraction.pipeline._run_extraction
        ↓  interpretation.reference_resolver  (existing)
        ↓
    VisionExtractionOutput   ← this module

DESIGN RULES
------------
- Does NOT compute LOW / NORMAL / HIGH.
- Does NOT add medical interpretation rules.
- Does NOT duplicate existing domain models.
- Preserves raw values and marks uncertainty when a field
  could not be reliably extracted.
- Calls the existing reference_resolver for interval parsing.
- OCR confidence / source information is carried through from
  SourceMeta (extraction.pipeline).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# =========================================================
# PATIENT CONTEXT
# =========================================================

@dataclass
class VisionPatient:
    """
    Patient context extracted from the report image.

    Fields that could not be extracted are None.
    `uncertain` is True when the raw text was present but
    could not be reliably parsed (e.g. OCR noise).
    """

    name: Optional[str] = None
    age_value: Optional[int] = None
    age_unit: Optional[str] = None
    sex: Optional[str] = None
    patient_id: Optional[str] = None
    report_date: Optional[str] = None

    # True when any field was present but uncertain
    uncertain: bool = False


# =========================================================
# REFERENCE INTERVAL (resolved)
# =========================================================

@dataclass
class VisionReferenceInterval:
    """
    Parsed reference interval as returned by the existing
    reference_resolver.  Only populated when the resolver
    succeeded (resolved=True).
    """

    minimum: float
    maximum: float
    matched_by: str          # "report_direct" | "sex" | "age" | "age_and_sex"


# =========================================================
# LAB RESULT
# =========================================================

@dataclass
class VisionLabResult:
    """
    One laboratory measurement extracted from the report image.

    Fields
    ------
    canonical_name : str
        Canonical test name from the existing TEST_ALIASES map.
    raw_name : str
        Test name exactly as it appeared in the OCR output.
    value : float | None
        Numeric result value.  None when extraction failed.
    unit : str | None
        Unit string as extracted.  None when missing.
    raw_reference : str | None
        Reference range exactly as it appeared in the source.
    reference_interval : VisionReferenceInterval | None
        Parsed interval from the existing reference_resolver.
        None when the resolver could not resolve the range.
    reference_unresolved_reason : str | None
        Reason string from the resolver when resolution failed.
    abnormal_flag : str | None
        Abnormal flag explicitly present in the source text
        (e.g. "H", "L", "*").  NOT computed here.
    value_uncertain : bool
        True when the value was present but OCR confidence
        for that token was below threshold.
    ocr_confidence : float | None
        Mean OCR confidence for the page this result came from.
        None for text PDFs (no OCR performed).
    ocr_engine : str | None
        Name of the OCR engine used.  None for text PDFs.
    """

    canonical_name: str
    raw_name: str
    value: Optional[float] = None
    unit: Optional[str] = None
    raw_reference: Optional[str] = None
    reference_interval: Optional[VisionReferenceInterval] = None
    reference_unresolved_reason: Optional[str] = None
    abnormal_flag: Optional[str] = None
    value_uncertain: bool = False
    ocr_confidence: Optional[float] = None
    ocr_engine: Optional[str] = None


# =========================================================
# TOP-LEVEL OUTPUT
# =========================================================

@dataclass
class VisionExtractionOutput:
    """
    Complete structured output of the Vision extraction pipeline.

    Fields
    ------
    patient : VisionPatient
        Extracted patient context.
    lab_results : list[VisionLabResult]
        Extracted and validated laboratory results.
    source_input_type : str
        "text_pdf" | "scanned_pdf" | "image"
    source_path : str | None
        File path if input was a file.
    ocr_pages : int
        Number of pages that went through OCR (0 for text PDFs).
    ocr_confidence : float | None
        Mean OCR confidence across all OCR'd pages.
    ocr_warnings : list[str]
        Non-fatal OCR / rendering warnings.
    extraction_warnings : list[str]
        Non-fatal extraction / validation warnings.
    """

    patient: VisionPatient
    lab_results: list[VisionLabResult] = field(default_factory=list)

    source_input_type: str = "unknown"
    source_path: Optional[str] = None
    ocr_pages: int = 0
    ocr_confidence: Optional[float] = None
    ocr_warnings: list[str] = field(default_factory=list)
    extraction_warnings: list[str] = field(default_factory=list)

    @property
    def result_count(self) -> int:
        return len(self.lab_results)

    @property
    def is_ocr_sourced(self) -> bool:
        return self.ocr_pages > 0
