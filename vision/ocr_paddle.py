"""
vision/ocr_paddle.py

PaddleOCR engine implementation.

PURPOSE
-------
Wrap PaddleOCR 3.x behind the BaseOCREngine interface so
the rest of the pipeline never imports PaddleOCR directly.

DESIGN DECISIONS
----------------
1.  Lazy initialisation — the PaddleOCR model is NOT loaded
    at import time. It is loaded on the first call to
    extract(). This keeps import cost zero when the engine
    is not used.

2.  The model is loaded once and cached on the instance.
    Subsequent calls to extract() reuse the same model.

3.  PaddleOCR 3.x predict() returns a list of result dicts.
    Each dict contains:
        rec_texts   : list[str]
        rec_scores  : list[float]
        rec_boxes   : list[list[list[float]]]  (4 corners)
        page_index  : int

4.  Text reconstruction preserves line order as returned
    by PaddleOCR (top-to-bottom reading order).

5.  This module does NOT interpret medical values.

IMPORTANT
---------
PaddleOCR downloads model weights on first use.
This requires internet access on the first run only.
Subsequent runs use the cached model from ~/.paddleocr/.
"""

from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np

from vision.ocr_base import BaseOCREngine, OCREngineConfig
from vision.ocr_result import BoundingBox, OCRLine, OCRResult


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# ENGINE NAME CONSTANT
# =========================================================

ENGINE_NAME = "paddleocr"


# =========================================================
# PADDLE OCR ENGINE
# =========================================================

class PaddleOCREngine(BaseOCREngine):
    """
    OCR engine backed by PaddleOCR 3.x.

    Parameters
    ----------
    config : OCREngineConfig | None
        Shared engine configuration.
        If None, defaults are used (English, CPU).

    Notes
    -----
    PaddleOCR is imported lazily inside _load_model().
    If paddleocr is not installed, a clear ImportError
    is raised at the point of first use, not at import
    time of this module.
    """

    def __init__(
        self,
        config: Optional[OCREngineConfig] = None
    ):
        super().__init__(config)

        # Model is loaded lazily on first extract() call.
        self._model = None

        logger.debug(
            "PaddleOCREngine: created (model not yet loaded)"
        )

    # -------------------------------------------------
    # ENGINE NAME
    # -------------------------------------------------

    @property
    def engine_name(self) -> str:
        return ENGINE_NAME

    # -------------------------------------------------
    # LAZY MODEL LOADING
    # -------------------------------------------------

    def _load_model(self) -> None:
        """
        Load the PaddleOCR model on first use.

        Raises
        ------
        ImportError
            If paddleocr is not installed.
        RuntimeError
            If the model fails to initialise.
        """

        if self._model is not None:
            return

        try:
            from paddleocr import PaddleOCR

        except ImportError as error:
            raise ImportError(
                "PaddleOCR is not installed. "
                "Install it with: "
                "pip install paddlepaddle paddleocr"
            ) from error

        logger.info(
            "PaddleOCREngine: loading model "
            "(lang=%s, use_gpu=%s)",
            self.config.lang,
            self.config.use_gpu
        )

        try:

            device = (
                "gpu"
                if self.config.use_gpu
                else "cpu"
            )

            self._model = PaddleOCR(
                lang=self.config.lang,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                device=device,
                enable_mkldnn=False,
            )

        except Exception as error:
            raise RuntimeError(
                f"PaddleOCREngine: failed to load model: "
                f"{error}"
            ) from error

        logger.info(
            "PaddleOCREngine: model loaded successfully"
        )

    # -------------------------------------------------
    # RESULT PARSING
    # -------------------------------------------------

    def _parse_result(
        self,
        raw_results: list,
        page_number: int
    ) -> OCRResult:
        """
        Convert PaddleOCR 3.x raw output into OCRResult.

        PaddleOCR 3.x predict() returns a list of dicts.
        Each dict represents one image and contains:

            rec_texts  : list[str]
            rec_scores : list[float]
            rec_boxes  : list[list[list[float]]]
            page_index : int

        Parameters
        ----------
        raw_results : list
            Direct output from PaddleOCR.predict().
        page_number : int
            Page index to assign to the result.

        Returns
        -------
        OCRResult
        """

        warnings: List[str] = []

        # PaddleOCR returns one dict per input image.
        # We always pass one image, so take index 0.
        if not raw_results:
            logger.warning(
                "PaddleOCREngine: predict() returned "
                "empty list"
            )
            return OCRResult(
                text="",
                lines=[],
                page_number=page_number,
                engine=ENGINE_NAME,
                confidence=None,
                warnings=["OCR returned no results."]
            )

        result_dict = raw_results[0]

        rec_texts = result_dict.get("rec_texts", [])
        rec_scores = result_dict.get("rec_scores", [])
        rec_boxes = result_dict.get("rec_boxes", [])

        if not rec_texts:
            logger.info(
                "PaddleOCREngine: no text detected "
                "on page %d",
                page_number
            )
            return OCRResult(
                text="",
                lines=[],
                page_number=page_number,
                engine=ENGINE_NAME,
                confidence=None,
                warnings=["No text detected on this page."]
            )

        # -------------------------------------------------
        # Build OCRLine list
        # -------------------------------------------------

        lines: List[OCRLine] = []

        scores_available = (
            len(rec_scores) == len(rec_texts)
        )

        boxes_available = (
            len(rec_boxes) == len(rec_texts)
        )

        for index, text in enumerate(rec_texts):

            confidence = (
                float(rec_scores[index])
                if scores_available
                else None
            )

            bounding_box = (
                self._parse_box(rec_boxes[index])
                if boxes_available
                else None
            )

            if (
                confidence is not None
                and confidence
                < self.config.confidence_threshold
            ):
                warnings.append(
                    f"Line {index} has low confidence "
                    f"({confidence:.3f}): {text!r}"
                )

            lines.append(
                OCRLine(
                    text=text,
                    confidence=confidence,
                    bounding_box=bounding_box,
                    line_index=index
                )
            )

        # -------------------------------------------------
        # Full text — join lines preserving order
        # -------------------------------------------------

        full_text = "\n".join(
            line.text for line in lines
        )

        # -------------------------------------------------
        # Mean confidence
        # -------------------------------------------------

        mean_confidence: Optional[float] = None

        if scores_available and lines:

            mean_confidence = float(
                sum(
                    line.confidence
                    for line in lines
                    if line.confidence is not None
                )
                / len(lines)
            )

        logger.info(
            "PaddleOCREngine: page %d — "
            "%d lines, mean_conf=%s",
            page_number,
            len(lines),
            (
                f"{mean_confidence:.3f}"
                if mean_confidence is not None
                else "n/a"
            )
        )

        return OCRResult(
            text=full_text,
            lines=lines,
            page_number=page_number,
            engine=ENGINE_NAME,
            confidence=mean_confidence,
            warnings=warnings
        )

    @staticmethod
    def _parse_box(
        raw_box: object
    ) -> Optional[BoundingBox]:
        """
        Convert a raw PaddleOCR bounding box into the
        standard BoundingBox format.

        PaddleOCR 3.x returns boxes as numpy arrays or
        nested lists of shape (4, 2).

        Returns None if the box cannot be parsed.
        """

        try:

            box_array = np.array(raw_box, dtype=float)

            if box_array.shape != (4, 2):
                return None

            return [
                (float(box_array[i, 0]),
                 float(box_array[i, 1]))
                for i in range(4)
            ]

        except Exception:
            return None

    # -------------------------------------------------
    # EXTRACT — public interface
    # -------------------------------------------------

    def extract(
        self,
        image: np.ndarray,
        page_number: int = 0
    ) -> OCRResult:
        """
        Run PaddleOCR on a preprocessed image.

        Parameters
        ----------
        image : np.ndarray
            Preprocessed image (grayscale or BGR, uint8).
        page_number : int
            Zero-based page index. Default 0.

        Returns
        -------
        OCRResult
            Extracted text with line metadata.

        Raises
        ------
        ValueError
            If the image array is invalid.
        RuntimeError
            If PaddleOCR fails unexpectedly.
        ImportError
            If paddleocr is not installed.
        """

        self._validate_input(image)
        ocr_image = image

        if image.ndim == 2:
            import cv2

            ocr_image = cv2.cvtColor(
         image,
            cv2.COLOR_GRAY2BGR,
            )
        self._load_model()

        logger.debug(
            "PaddleOCREngine: running predict on "
            "image shape=%s page=%d",
            image.shape,
            page_number
        )

        try:

            raw_results = self._model.predict(ocr_image)

        except Exception as error:
            raise RuntimeError(
                f"PaddleOCREngine: predict() failed: "
                f"{error}"
            ) from error

        return self._parse_result(raw_results, page_number)
