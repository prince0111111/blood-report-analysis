"""
Real PaddleOCR runtime regression test.

Purpose
-------
Verify that the actual installed PaddleOCR engine can consume the
same preprocessed image produced by our real vision pipeline.

This is intentionally NOT a mocked/unit test.

It exercises:

    real image
        ↓
    preprocess_image()
        ↓
    PaddleOCREngine
        ↓
    OCRResult

If this test fails while the rest of the project tests pass,
the failure belongs to the PaddleOCR adapter/runtime boundary.
"""

from pathlib import Path

import cv2
import numpy as np

from vision.preprocessor import preprocess_image
from vision.ocr_config import create_ocr_engine
from vision.ocr_result import OCRResult


SAMPLE_IMAGE = Path("samples/reports/image.jpg")


def test_real_paddleocr_accepts_preprocessed_image():
    """
    Run the actual installed PaddleOCR engine against the actual
    preprocessed sample image.

    No mocks.
    No dummy OCR output.
    """

    assert SAMPLE_IMAGE.exists(), (
        f"Real sample image not found: {SAMPLE_IMAGE}"
    )

    # ---------------------------------------------------------
    # LOAD REAL IMAGE
    # ---------------------------------------------------------

    image = cv2.imread(str(SAMPLE_IMAGE))

    assert image is not None, (
        f"Could not load sample image: {SAMPLE_IMAGE}"
    )

    assert isinstance(image, np.ndarray)
    assert image.size > 0

    # ---------------------------------------------------------
    # RUN OUR REAL PREPROCESSOR
    # ---------------------------------------------------------

    processed = preprocess_image(image)

    assert processed is not None
    assert processed.image is not None

    processed_image = processed.image

    assert isinstance(processed_image, np.ndarray)
    assert processed_image.size > 0
    assert processed_image.dtype == np.uint8

    # Our current preprocessor produces a valid 2-D image.
    assert processed_image.ndim in (2, 3)

    print()
    print("========================================")
    print("REAL PADDLEOCR RUNTIME TEST")
    print("========================================")
    print(f"Original shape:  {image.shape}")
    print(f"Processed shape: {processed_image.shape}")
    print(f"Processed dtype: {processed_image.dtype}")
    print(f"Steps:           {processed.steps_applied}")

    # ---------------------------------------------------------
    # CREATE THE ACTUAL OCR ENGINE
    # ---------------------------------------------------------

    engine = create_ocr_engine("paddle")

    assert engine is not None

    print(f"OCR engine:      {engine.engine_name}")

    # ---------------------------------------------------------
    # ACTUAL OCR CALL
    # ---------------------------------------------------------

    result = engine.extract(
        processed_image,
        page_number=0,
    )

    # ---------------------------------------------------------
    # VERIFY OUR OCR CONTRACT
    # ---------------------------------------------------------

    assert isinstance(result, OCRResult)

    assert result.page_number == 0
    assert isinstance(result.text, str)
    assert isinstance(result.lines, list)

    print(f"OCR lines:       {result.line_count}")
    print(f"OCR confidence:  {result.confidence}")
    print(f"Text empty:      {result.is_empty}")

    print("✓ REAL PADDLEOCR RUNTIME TEST PASSED")