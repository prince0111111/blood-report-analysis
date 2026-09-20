"""
vision/pdf_classifier.py

Classify each page of a PDF as TEXT or SCANNED.

PURPOSE
-------
Determine whether a PDF page contains usable embedded text
(TEXT path → existing pdf_reader.py) or only raster image
content (SCANNED path → render → preprocess → OCR).

STRATEGY
--------
A page is classified as TEXT if the stripped character count
of its embedded text meets or exceeds MIN_TEXT_CHARS.

This threshold-based approach is intentionally simple and
robust. It handles:
  - Pure text PDFs          → all pages TEXT
  - Pure scanned PDFs       → all pages SCANNED
  - Mixed PDFs              → per-page classification
  - Pages with only headers → classified SCANNED (low char count)

The classifier does NOT interpret medical content.

RESULT
------
PDFPageType  : enum  TEXT | SCANNED
PDFClassification : per-document result with per-page breakdown
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Union

logger = logging.getLogger(__name__)

# Minimum embedded-text characters for a page to be
# considered a text page. Pages below this are sent to OCR.
MIN_TEXT_CHARS = 50


class PDFPageType(Enum):
    TEXT = "text"
    SCANNED = "scanned"


@dataclass
class PDFClassification:
    """
    Classification result for an entire PDF document.

    Attributes
    ----------
    page_types : dict[int, PDFPageType]
        Mapping of zero-based page index → page type.
    is_fully_text : bool
        True if every page is TEXT.
    is_fully_scanned : bool
        True if every page is SCANNED.
    is_mixed : bool
        True if the document has both TEXT and SCANNED pages.
    page_count : int
        Total number of pages.
    """

    page_types: Dict[int, PDFPageType] = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.page_types)

    @property
    def is_fully_text(self) -> bool:
        return all(t == PDFPageType.TEXT for t in self.page_types.values())

    @property
    def is_fully_scanned(self) -> bool:
        return all(t == PDFPageType.SCANNED for t in self.page_types.values())

    @property
    def is_mixed(self) -> bool:
        types = set(self.page_types.values())
        return len(types) > 1

    def scanned_pages(self) -> List[int]:
        return [i for i, t in self.page_types.items() if t == PDFPageType.SCANNED]

    def text_pages(self) -> List[int]:
        return [i for i, t in self.page_types.items() if t == PDFPageType.TEXT]

    def __repr__(self) -> str:
        return (
            f"PDFClassification("
            f"pages={self.page_count}, "
            f"text={len(self.text_pages())}, "
            f"scanned={len(self.scanned_pages())})"
        )


def classify_pdf(
    pdf_path: Union[str, Path],
    min_text_chars: int = MIN_TEXT_CHARS,
) -> PDFClassification:
    """
    Classify each page of a PDF as TEXT or SCANNED.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the PDF file.
    min_text_chars : int
        Minimum character count for a page to be TEXT.
        Default 50.

    Returns
    -------
    PDFClassification

    Raises
    ------
    FileNotFoundError
        If the PDF does not exist.
    ValueError
        If the file cannot be opened as a PDF.
    """
    import pymupdf

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix!r}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise ValueError(f"Cannot open PDF {path.name!r}: {exc}") from exc

    classification = PDFClassification()

    try:
        for index in range(doc.page_count):
            page = doc[index]
            text = page.get_text("text")
            char_count = len(text.strip())

            page_type = (
                PDFPageType.TEXT
                if char_count >= min_text_chars
                else PDFPageType.SCANNED
            )

            classification.page_types[index] = page_type

            logger.debug(
                "classify_pdf: page %d — chars=%d → %s",
                index, char_count, page_type.value,
            )
    finally:
        doc.close()

    logger.info(
        "classify_pdf: %r — %s",
        path.name, classification,
    )

    return classification
