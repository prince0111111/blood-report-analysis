"""
vision/pdf_renderer.py

Render PDF pages as numpy image arrays using PyMuPDF.

PURPOSE
-------
Convert each page of a PDF into a uint8 BGR numpy array
suitable for the preprocessing pipeline.

This module is purely a rendering utility.
It does NOT classify PDFs, run OCR, or interpret content.

RESOLUTION
----------
DPI is controlled via a scale factor applied to PyMuPDF's
Matrix. 150 DPI ≈ scale 2.08; 300 DPI ≈ scale 4.17.
We default to 300 DPI (scale=4.17) for OCR quality.
The caller may override this.

MEMORY
------
Pages are rendered one at a time and yielded as a
generator so large documents are never fully loaded
into memory simultaneously.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# 300 DPI relative to PyMuPDF's default 72 DPI baseline
DEFAULT_DPI = 300
_BASELINE_DPI = 72.0


def _dpi_to_scale(dpi: int) -> float:
    return dpi / _BASELINE_DPI


# =========================================================
# PUBLIC API
# =========================================================

def render_pdf_pages(
    pdf_path: Union[str, Path],
    dpi: int = DEFAULT_DPI,
) -> Generator[Tuple[int, np.ndarray], None, None]:
    """
    Yield (page_index, image_array) for every page in the PDF.

    Parameters
    ----------
    pdf_path : str | Path
        Path to the PDF file.
    dpi : int
        Render resolution. Default 300.

    Yields
    ------
    (page_index, np.ndarray)
        page_index : zero-based page number
        np.ndarray : BGR uint8 image of shape (H, W, 3)

    Raises
    ------
    FileNotFoundError
        If the PDF path does not exist.
    ValueError
        If the file is not a PDF or cannot be opened.
    RuntimeError
        If a page fails to render (logged; page is skipped).
    """
    import pymupdf  # lazy — only needed when rendering

    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path.suffix!r}")

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise ValueError(
            f"Cannot open PDF {path.name!r}: {exc}"
        ) from exc

    scale = _dpi_to_scale(dpi)
    matrix = pymupdf.Matrix(scale, scale)
    page_count = doc.page_count

    logger.info(
        "pdf_renderer: opening %r — %d page(s) at %d DPI (scale=%.2f)",
        path.name, page_count, dpi, scale,
    )

    try:
        for index in range(page_count):
            try:
                page = doc[index]
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)

                # samples is a bytes object: H * W * n bytes (RGB)
                arr = np.frombuffer(
                    pixmap.samples, dtype=np.uint8
                ).reshape(pixmap.height, pixmap.width, pixmap.n)

                # PyMuPDF returns RGB; convert to BGR for OpenCV/preprocessor
                import cv2
                bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

                logger.debug(
                    "pdf_renderer: page %d rendered — shape=%s",
                    index, bgr.shape,
                )
                yield index, bgr

            except Exception as exc:
                logger.error(
                    "pdf_renderer: failed to render page %d — %s",
                    index, exc,
                )
                # Yield None so the caller can handle the gap
                yield index, None  # type: ignore[misc]
    finally:
        doc.close()


def get_page_count(pdf_path: Union[str, Path]) -> int:
    """Return the number of pages in a PDF without rendering."""
    import pymupdf

    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    try:
        doc = pymupdf.open(str(path))
        count = doc.page_count
        doc.close()
        return count
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc
