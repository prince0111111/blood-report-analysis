"""
extraction/pipeline.py

Unified extraction pipeline for blood report analysis.

PURPOSE
-------
Accept any supported input (text PDF, scanned PDF, or
pre-rendered image array) and return a fully validated,
structured extraction result by routing through the
correct text-acquisition path and then the existing
extraction modules — unchanged.

TWO PATHS
---------

TEXT PDF
    pdf_reader (PyMuPDF embedded text)
        ↓
    text_cleaner → patient_parser → parser
        → coverage → validator → plausibility

SCANNED PDF / IMAGE
    vision.scanned_pdf_reader  (render → preprocess → OCR)
        ↓
    text_cleaner → patient_parser → parser
        → coverage → validator → plausibility

The downstream extraction modules are called identically
in both paths.  No logic is duplicated.

SOURCE METADATA
---------------
Every result carries a `source` dict:

    {
        "input_type":  "text_pdf" | "scanned_pdf" | "image",
        "path":        str | None,
        "page_count":  int | None,
        "ocr_pages":   int,          # 0 for text PDFs
        "ocr_confidence": float | None,
    }

CONSTRAINTS
-----------
- Does NOT interpret medical values.
- Does NOT determine LOW / NORMAL / HIGH.
- Does NOT modify the Knowledge Engine.
- Does NOT duplicate any existing extraction function.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


# =========================================================
# INPUT TYPE
# =========================================================

class InputType(Enum):
    TEXT_PDF    = "text_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE       = "image"


# =========================================================
# SOURCE METADATA
# =========================================================

@dataclass
class SourceMeta:
    """
    Metadata about how the raw text was obtained.

    Attributes
    ----------
    input_type : InputType
    path : str | None
        File path if input was a file.
    page_count : int | None
        Total pages (PDFs only).
    ocr_pages : int
        Number of pages that went through OCR.
        Always 0 for text PDFs.
    ocr_confidence : float | None
        Mean OCR confidence across all OCR'd pages.
        None when no OCR was performed or confidence
        was not available.
    warnings : list[str]
        Non-fatal issues from the OCR / rendering layer.
    """
    input_type: InputType
    path: Optional[str] = None
    page_count: Optional[int] = None
    ocr_pages: int = 0
    ocr_confidence: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "input_type":     self.input_type.value,
            "path":           self.path,
            "page_count":     self.page_count,
            "ocr_pages":      self.ocr_pages,
            "ocr_confidence": self.ocr_confidence,
            "warnings":       list(self.warnings),
        }


# =========================================================
# PIPELINE RESULT
# =========================================================

@dataclass
class PipelineResult:
    """
    Complete output of the extraction pipeline.

    Attributes
    ----------
    source : SourceMeta
        How and where the text was obtained.
    raw_text : str
        Text as returned by the acquisition layer
        (before cleaning).
    cleaned_text : str
        Text after text_cleaner.clean_pdf_text().
    patient : dict
        Output of patient_parser.extract_patient_context().
    tests : list[dict]
        Output of parser.parse_cbc().
    coverage : dict
        Output of coverage.check_cbc_coverage().
    validation : dict
        Output of validator.validate_report().
    plausibility : dict | None
        Output of plausibility.check_report_plausibility().
        None when validation.can_analyze is False.
    """
    source: SourceMeta
    raw_text: str
    cleaned_text: str
    patient: dict
    tests: List[dict]
    coverage: dict
    validation: dict
    plausibility: Optional[dict] = None

    def __repr__(self) -> str:
        return (
            f"PipelineResult("
            f"input={self.source.input_type.value}, "
            f"tests={len(self.tests)}, "
            f"status={self.validation.get('status')!r})"
        )


# =========================================================
# INTERNAL: EXISTING EXTRACTION PIPELINE
# =========================================================

def _run_extraction(raw_text: str) -> tuple:
    """
    Run the existing extraction modules on raw text.

    Returns (cleaned_text, patient, tests, coverage,
             validation, plausibility).

    This function is the single place that calls every
    existing extraction module.  It must never be
    duplicated.
    """
    from extraction.text_cleaner   import clean_pdf_text
    from extraction.patient_parser import extract_patient_context
    from extraction.parser         import parse_cbc
    from extraction.coverage       import check_cbc_coverage
    from extraction.validator      import validate_report
    from extraction.plausibility   import check_report_plausibility

    cleaned   = clean_pdf_text(raw_text)
    patient   = extract_patient_context(cleaned)
    tests     = parse_cbc(cleaned)
    coverage  = check_cbc_coverage(tests)
    validation = validate_report(patient=patient, tests=tests)

    plausibility = None
    if validation["can_analyze"]:
        valid_tests  = validation.get("validated_test_data", [])
        plausibility = check_report_plausibility(valid_tests)

    return cleaned, patient, tests, coverage, validation, plausibility


# =========================================================
# INTERNAL: TEXT PDF PATH
# =========================================================

def _process_text_pdf(path: Path) -> tuple:
    """
    Extract text from a text-based PDF using PyMuPDF.

    Returns (raw_text, source_meta).
    """
    import pymupdf

    doc = pymupdf.open(str(path))
    pages = []
    try:
        for i, page in enumerate(doc):
            text = page.get_text("text")
            pages.append(f"\n--- PAGE {i + 1} ---\n{text}")
    finally:
        doc.close()

    raw_text = "\n".join(pages)

    if not raw_text.strip():
        raise ValueError(
            "No embedded text detected. "
            "This may be a scanned/image-based PDF."
        )

    meta = SourceMeta(
        input_type=InputType.TEXT_PDF,
        path=str(path),
        page_count=len(pages),
        ocr_pages=0,
    )
    return raw_text, meta


# =========================================================
# INTERNAL: SCANNED / MIXED PDF PATH
# =========================================================

def _process_scanned_pdf(
    path: Path,
    ocr_engine=None,
    dpi: int = 300,
) -> tuple:
    """
    Render + preprocess + OCR a scanned (or mixed) PDF.

    Returns (raw_text, source_meta).
    """
    from vision.scanned_pdf_reader import read_pdf

    result = read_pdf(path, ocr_engine=ocr_engine, dpi=dpi)

    meta = SourceMeta(
        input_type=InputType.SCANNED_PDF,
        path=str(path),
        page_count=result.page_count,
        ocr_pages=result.ocr_page_count,
        warnings=list(result.warnings),
    )
    return result.text, meta


# =========================================================
# INTERNAL: IMAGE PATH
# =========================================================

def _process_image(
    image: np.ndarray,
    ocr_engine=None,
) -> tuple:
    """
    Preprocess + OCR a single image array.

    Returns (raw_text, source_meta).
    """
    from vision.preprocessor import preprocess_image
    from vision.ocr_result   import OCRResult

    if ocr_engine is None:
        from vision.ocr_paddle import PaddleOCREngine
        ocr_engine = PaddleOCREngine()

    prep   = preprocess_image(image)
    result: OCRResult = ocr_engine.extract(prep.image, page_number=0)

    # Wrap in page markers so text_cleaner works identically
    raw_text = f"\n--- PAGE 1 ---\n{result.text}"

    meta = SourceMeta(
        input_type=InputType.IMAGE,
        path=None,
        page_count=1,
        ocr_pages=1,
        ocr_confidence=result.confidence,
        warnings=list(result.warnings),
    )
    return raw_text, meta


# =========================================================
# PUBLIC API
# =========================================================

def process(
    source: Union[str, Path, np.ndarray],
    ocr_engine=None,
    dpi: int = 300,
    force_ocr: bool = False,
) -> PipelineResult:
    """
    Run the full extraction pipeline on any supported input.

    Parameters
    ----------
    source : str | Path | np.ndarray
        - str / Path ending in .pdf  → PDF (auto-detected)
        - np.ndarray                 → pre-rendered image
    ocr_engine : BaseOCREngine | None
        OCR engine for scanned pages / images.
        If None, PaddleOCREngine with defaults is used
        when OCR is needed.
    dpi : int
        Render resolution for scanned PDF pages. Default 300.
    force_ocr : bool
        If True, treat every PDF page as scanned regardless
        of embedded text.  Useful for testing.

    Returns
    -------
    PipelineResult

    Raises
    ------
    FileNotFoundError
        If a file path does not exist.
    ValueError
        If the input type cannot be determined or the file
        cannot be opened.
    TypeError
        If source is not a str, Path, or numpy array.
    """

    # --------------------------------------------------
    # IMAGE ARRAY
    # --------------------------------------------------
    if isinstance(source, np.ndarray):
        logger.info("pipeline: input=image shape=%s", source.shape)
        raw_text, meta = _process_image(source, ocr_engine=ocr_engine)

    # --------------------------------------------------
    # FILE PATH
    # --------------------------------------------------
    elif isinstance(source, (str, Path)):
        path = Path(source)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()

        # --------------------------------------------------
        # IMAGE FILE PATH
        # --------------------------------------------------
        # Image paths use the same Vision/OCR path as numpy
        # image arrays. This keeps file-based images and
        # already-loaded images on the same extraction path.
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
            from vision.preprocessor import load_image

            logger.info("pipeline: input=image path=%s", path.name)
            image = load_image(path)
            raw_text, meta = _process_image(
                image,
                ocr_engine=ocr_engine,
            )
            meta.path = str(path)

        elif suffix != ".pdf":
            raise ValueError(
                f"Unsupported file type: {path.suffix!r}. "
                "Supported inputs are PDF files, image files, "
                "or numpy image arrays."
            )

        elif force_ocr:
            logger.info("pipeline: input=scanned_pdf (forced) path=%s", path.name)
            raw_text, meta = _process_scanned_pdf(
                path, ocr_engine=ocr_engine, dpi=dpi
            )
        else:
            # Classify to choose the right path
            from vision.pdf_classifier import classify_pdf
            classification = classify_pdf(path)

            if classification.is_fully_text:
                logger.info("pipeline: input=text_pdf path=%s", path.name)
                raw_text, meta = _process_text_pdf(path)
            else:
                logger.info(
                    "pipeline: input=scanned_pdf path=%s "
                    "(scanned_pages=%d)",
                    path.name,
                    len(classification.scanned_pages()),
                )
                raw_text, meta = _process_scanned_pdf(
                    path, ocr_engine=ocr_engine, dpi=dpi
                )

    else:
        raise TypeError(
            f"source must be a file path (str/Path) or a numpy array. "
            f"Got {type(source).__name__!r}."
        )

    # --------------------------------------------------
    # EXISTING EXTRACTION PIPELINE (identical for all paths)
    # --------------------------------------------------
    (
        cleaned, patient, tests,
        coverage, validation, plausibility,
    ) = _run_extraction(raw_text)

    logger.info(
        "pipeline: complete — input=%s tests=%d status=%s",
        meta.input_type.value,
        len(tests),
        validation.get("status"),
    )

    return PipelineResult(
        source=meta,
        raw_text=raw_text,
        cleaned_text=cleaned,
        patient=patient,
        tests=tests,
        coverage=coverage,
        validation=validation,
        plausibility=plausibility,
    )