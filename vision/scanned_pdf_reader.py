"""
vision/scanned_pdf_reader.py

Scanned PDF → text extraction via render + preprocess + OCR.

PURPOSE
-------
Provide a single entry point that accepts any PDF and returns
plain text, routing each page through the correct path:

    TEXT page   → PyMuPDF embedded text  (existing path)
    SCANNED page → render → preprocess → OCR → text

The output text format mirrors extraction/pdf_reader.py so
the downstream extraction pipeline (text_cleaner, parser,
etc.) requires zero changes.

PUBLIC API
----------
    read_pdf(pdf_path, ocr_engine=None) -> str

    The returned string uses the same
    "--- PAGE N ---" markers as pdf_reader.py.

DESIGN
------
- Pages are processed one at a time (generator-based) to
  avoid loading the entire document into memory.
- Empty pages produce an empty page block (not an error).
- Corrupted pages are logged and produce an empty block.
- The OCR engine is injected; defaults to PaddleOCREngine.
- This module does NOT modify the Knowledge Engine.
- This module does NOT interpret medical values.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import pymupdf

from vision.pdf_classifier import PDFClassification, PDFPageType, classify_pdf
from vision.pdf_renderer import render_pdf_pages
from vision.preprocessor import preprocess_image
from vision.ocr_base import BaseOCREngine
from vision.ocr_result import OCRResult

logger = logging.getLogger(__name__)

# Minimum chars on a page for it to be considered non-empty
# after OCR (avoids treating noise as content).
_MIN_OCR_CHARS = 5


# =========================================================
# RESULT MODEL
# =========================================================

class ScannedPDFResult:
    """
    Result of reading a (possibly scanned) PDF.

    Attributes
    ----------
    text : str
        Full extracted text with --- PAGE N --- markers.
    page_count : int
        Total pages processed.
    ocr_page_count : int
        Number of pages that went through OCR.
    text_page_count : int
        Number of pages that used embedded text.
    warnings : list[str]
        Non-fatal issues encountered.
    classification : PDFClassification
        Per-page TEXT/SCANNED classification.
    """

    def __init__(
        self,
        text: str,
        classification: PDFClassification,
        ocr_page_count: int,
        warnings: list,
    ):
        self.text = text
        self.classification = classification
        self.ocr_page_count = ocr_page_count
        self.text_page_count = classification.page_count - ocr_page_count
        self.warnings = warnings

    @property
    def page_count(self) -> int:
        return self.classification.page_count

    def __repr__(self) -> str:
        return (
            f"ScannedPDFResult("
            f"pages={self.page_count}, "
            f"text_pages={self.text_page_count}, "
            f"ocr_pages={self.ocr_page_count}, "
            f"warnings={len(self.warnings)})"
        )


# =========================================================
# INTERNAL HELPERS
# =========================================================

def _extract_page_text_embedded(
    doc: pymupdf.Document,
    page_index: int,
) -> str:
    """Extract embedded text from a single page."""
    try:
        page = doc[page_index]
        return page.get_text("text")
    except Exception as exc:
        logger.error(
            "scanned_pdf_reader: embedded text extraction "
            "failed on page %d — %s", page_index, exc,
        )
        return ""


def _ocr_page(
    image,
    page_index: int,
    engine: BaseOCREngine,
) -> str:
    """Preprocess image and run OCR. Returns extracted text."""
    if image is None:
        logger.warning(
            "scanned_pdf_reader: page %d image is None — skipping OCR",
            page_index,
        )
        return ""

    try:
        result = preprocess_image(image)
        preprocessed = result.image
    except Exception as exc:
        logger.error(
            "scanned_pdf_reader: preprocessing failed on page %d — %s",
            page_index, exc,
        )
        return ""

    try:
        ocr_result: OCRResult = engine.extract(
            preprocessed, page_number=page_index
        )
        return ocr_result.text
    except Exception as exc:
        logger.error(
            "scanned_pdf_reader: OCR failed on page %d — %s",
            page_index, exc,
        )
        return ""


# =========================================================
# PUBLIC API
# =========================================================

def read_pdf(
    pdf_path: Union[str, Path],
    ocr_engine: Optional[BaseOCREngine] = None,
    dpi: int = 300,
) -> ScannedPDFResult:
    """
    Read a PDF, routing each page through text extraction or OCR.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the PDF file.
    ocr_engine : BaseOCREngine | None
        OCR engine to use for scanned pages.
        If None, a PaddleOCREngine with default config is created.
    dpi : int
        Render resolution for scanned pages. Default 300.

    Returns
    -------
    ScannedPDFResult
        Contains combined text and metadata.

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist.
    ValueError
        If the file cannot be opened as a PDF.
    """
    path = Path(pdf_path)

    # --- Validate path ---
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix!r}")

    # --- Classify pages ---
    classification = classify_pdf(path)

    logger.info(
        "read_pdf: %r — %s",
        path.name, classification,
    )

    # --- Short-circuit: fully text PDF ---
    # Delegate entirely to the existing embedded-text path.
    if classification.is_fully_text:
        logger.info(
            "read_pdf: fully text PDF — using embedded text only"
        )
        text = _read_all_embedded(path, classification)
        return ScannedPDFResult(
            text=text,
            classification=classification,
            ocr_page_count=0,
            warnings=[],
        )

    # --- Lazy-create OCR engine if not provided ---
    if ocr_engine is None:
        from vision.ocr_paddle import PaddleOCREngine
        ocr_engine = PaddleOCREngine()

    # --- Process page by page ---
    warnings: list = []
    page_texts: dict = {}  # page_index → text string
    ocr_page_count = 0

    # Open doc once for embedded-text pages
    doc = pymupdf.open(str(path))

    try:
        # Build a set of scanned page indices for the renderer
        scanned_indices = set(classification.scanned_pages())

        # Collect embedded text for text pages first (cheap)
        for idx in classification.text_pages():
            page_texts[idx] = _extract_page_text_embedded(doc, idx)

        # Render and OCR scanned pages one at a time
        for page_index, image in render_pdf_pages(path, dpi=dpi):
            if page_index not in scanned_indices:
                continue  # already handled above

            ocr_page_count += 1

            if image is None:
                warnings.append(
                    f"Page {page_index + 1}: render failed — page skipped."
                )
                page_texts[page_index] = ""
                continue

            text = _ocr_page(image, page_index, ocr_engine)

            if not text.strip():
                warnings.append(
                    f"Page {page_index + 1}: OCR produced no text."
                )

            page_texts[page_index] = text

    finally:
        doc.close()

    # --- Assemble in page order ---
    combined = _assemble_pages(page_texts, classification.page_count)

    return ScannedPDFResult(
        text=combined,
        classification=classification,
        ocr_page_count=ocr_page_count,
        warnings=warnings,
    )


def _read_all_embedded(
    path: Path,
    classification: PDFClassification,
) -> str:
    """Read all pages as embedded text (fully text PDF fast path)."""
    doc = pymupdf.open(str(path))
    page_texts = {}
    try:
        for idx in range(classification.page_count):
            page_texts[idx] = _extract_page_text_embedded(doc, idx)
    finally:
        doc.close()
    return _assemble_pages(page_texts, classification.page_count)


def _assemble_pages(
    page_texts: dict,
    page_count: int,
) -> str:
    """
    Join page texts with --- PAGE N --- markers in page order.

    Matches the format produced by extraction/pdf_reader.py.
    """
    parts = []
    for idx in range(page_count):
        text = page_texts.get(idx, "")
        parts.append(f"\n--- PAGE {idx + 1} ---\n{text}")
    return "\n".join(parts)
