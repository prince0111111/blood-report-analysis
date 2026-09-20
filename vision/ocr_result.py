"""
vision/ocr_result.py

Data model for OCR output.

PURPOSE
-------
Provide a clean, engine-agnostic container for OCR results.

This model is intentionally free of any medical logic.
It holds only what the OCR engine produced.

FIELDS
------
text            : full extracted text as a single string
lines           : ordered list of OCRLine objects
page_number     : 0-based page index (0 for single images)
engine          : name of the OCR engine that produced this
confidence      : mean confidence across all lines (0.0–1.0)
                  None if the engine did not return scores
warnings        : non-fatal issues encountered during OCR
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# =========================================================
# BOUNDING BOX TYPE
# =========================================================
#
# A bounding box is represented as four (x, y) corner
# points in clockwise order:
#
#   top-left, top-right, bottom-right, bottom-left
#
# Each point is a tuple of two floats: (x, y).
#
# Type alias for readability.
# =========================================================

BoundingBox = List[Tuple[float, float]]


# =========================================================
# OCR LINE
# =========================================================

@dataclass
class OCRLine:
    """
    A single recognised text line from the OCR engine.

    Attributes
    ----------
    text : str
        The recognised text for this line.
    confidence : float | None
        Recognition confidence in range [0.0, 1.0].
        None if the engine did not return a score.
    bounding_box : BoundingBox | None
        Four corner points of the text region.
        None if the engine did not return coordinates.
    line_index : int
        Zero-based position of this line in the result.
    """

    text: str
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBox] = None
    line_index: int = 0

    def __repr__(self) -> str:
        conf = (
            f"{self.confidence:.3f}"
            if self.confidence is not None
            else "n/a"
        )
        return (
            f"OCRLine("
            f"index={self.line_index}, "
            f"conf={conf}, "
            f"text={self.text!r})"
        )


# =========================================================
# OCR RESULT
# =========================================================

@dataclass
class OCRResult:
    """
    Complete OCR output for one page / image.

    Attributes
    ----------
    text : str
        Full extracted text joined by newlines.
        Empty string if nothing was recognised.
    lines : list[OCRLine]
        Individual recognised lines with metadata.
    page_number : int
        Zero-based page index.
        Always 0 for single images.
    engine : str
        Name of the OCR engine that produced this result.
    confidence : float | None
        Mean confidence across all lines.
        None if no confidence scores were available.
    warnings : list[str]
        Non-fatal issues encountered during OCR.
    """

    text: str
    lines: List[OCRLine] = field(default_factory=list)
    page_number: int = 0
    engine: str = "unknown"
    confidence: Optional[float] = None
    warnings: List[str] = field(default_factory=list)

    # -------------------------------------------------
    # CONVENIENCE PROPERTIES
    # -------------------------------------------------

    @property
    def is_empty(self) -> bool:
        """True if no text was extracted."""
        return not self.text.strip()

    @property
    def line_count(self) -> int:
        """Number of recognised lines."""
        return len(self.lines)

    @property
    def low_confidence(self) -> bool:
        """
        True if mean confidence is below 0.6.

        Returns False if confidence is not available.
        """
        if self.confidence is None:
            return False
        return self.confidence < 0.6

    def __repr__(self) -> str:
        conf = (
            f"{self.confidence:.3f}"
            if self.confidence is not None
            else "n/a"
        )
        return (
            f"OCRResult("
            f"page={self.page_number}, "
            f"engine={self.engine!r}, "
            f"lines={self.line_count}, "
            f"conf={conf}, "
            f"empty={self.is_empty})"
        )
