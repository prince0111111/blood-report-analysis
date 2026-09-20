"""
vision/ocr_base.py

Abstract base class for all OCR engine implementations.

PURPOSE
-------
Define a stable, engine-agnostic interface so that the
OCR engine can be swapped (PaddleOCR → Tesseract → cloud)
without changing any calling code.

CONTRACT
--------
Every concrete engine must implement:

    extract(image, page_number) -> OCRResult

The engine must NOT:
- interpret medical values
- determine LOW / NORMAL / HIGH
- diagnose disease
- apply medical rules
- modify Knowledge Engine logic
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np

from vision.ocr_result import OCRResult


# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# OCR ENGINE CONFIG
# =========================================================

class OCREngineConfig:
    """
    Shared configuration for OCR engines.

    Attributes
    ----------
    lang : str
        Language code passed to the engine.
        Default "en" (English).
    confidence_threshold : float
        Lines below this confidence are flagged in
        OCRResult.warnings but are still included in
        the output text.
        Range [0.0, 1.0]. Default 0.5.
    use_gpu : bool
        Whether to request GPU inference.
        Default False (CPU only).
    """

    def __init__(
        self,
        lang: str = "en",
        confidence_threshold: float = 0.5,
        use_gpu: bool = False
    ):
        self.lang = lang
        self.confidence_threshold = confidence_threshold
        self.use_gpu = use_gpu

    def __repr__(self) -> str:
        return (
            f"OCREngineConfig("
            f"lang={self.lang!r}, "
            f"confidence_threshold={self.confidence_threshold}, "
            f"use_gpu={self.use_gpu})"
        )


# =========================================================
# ABSTRACT BASE ENGINE
# =========================================================

class BaseOCREngine(ABC):
    """
    Abstract base class for OCR engine implementations.

    All concrete engines must inherit from this class and
    implement the `extract` method.

    The `extract` method accepts a preprocessed image
    (numpy array, grayscale or BGR, uint8) and returns
    an OCRResult.

    Parameters
    ----------
    config : OCREngineConfig | None
        Engine configuration. If None, defaults are used.
    """

    def __init__(
        self,
        config: Optional[OCREngineConfig] = None
    ):
        self.config = config or OCREngineConfig()

        logger.debug(
            "%s initialised with config=%s",
            self.__class__.__name__,
            self.config
        )

    # -------------------------------------------------
    # ABSTRACT — must be implemented by every engine
    # -------------------------------------------------

    @abstractmethod
    def extract(
        self,
        image: np.ndarray,
        page_number: int = 0
    ) -> OCRResult:
        """
        Run OCR on a preprocessed image.

        Parameters
        ----------
        image : np.ndarray
            Preprocessed image (grayscale or BGR, uint8).
            Must have been validated before calling this.
        page_number : int
            Zero-based page index for multi-page documents.
            Default 0 for single images.

        Returns
        -------
        OCRResult
            Extracted text with metadata.

        Raises
        ------
        RuntimeError
            If the OCR engine fails unexpectedly.
        ValueError
            If the image array is invalid.
        """
        raise NotImplementedError

    # -------------------------------------------------
    # ENGINE NAME — override in subclasses
    # -------------------------------------------------

    @property
    def engine_name(self) -> str:
        """
        Human-readable name of this engine.

        Subclasses should override this property.
        """
        return self.__class__.__name__

    # -------------------------------------------------
    # SHARED VALIDATION
    # -------------------------------------------------

    def _validate_input(
        self,
        image: np.ndarray
    ) -> None:
        """
        Validate the image array before passing to the
        engine.

        Raises
        ------
        ValueError
            If the image is not a valid numpy array.
        """

        if not isinstance(image, np.ndarray):
            raise ValueError(
                f"{self.engine_name}: image must be a "
                "numpy array."
            )

        if image.size == 0:
            raise ValueError(
                f"{self.engine_name}: image array is empty."
            )

        if image.ndim not in (2, 3):
            raise ValueError(
                f"{self.engine_name}: image must be 2-D "
                "(grayscale) or 3-D (colour). "
                f"Got ndim={image.ndim}."
            )

        if image.dtype != np.uint8:
            raise ValueError(
                f"{self.engine_name}: image dtype must be "
                f"uint8. Got {image.dtype}."
            )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"config={self.config})"
        )
