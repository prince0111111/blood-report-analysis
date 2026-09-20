"""
tests/vision/test_ocr.py

Unit tests for the OCR layer.

All unit tests use mocked OCR output.
No internet access or model download is required.

Tests
-----
1.  Successful OCR — valid result with text and confidence
2.  Empty OCR result — engine returns no text
3.  OCR failure — engine raises RuntimeError
4.  Low-confidence result — warning is attached
5.  Multiple lines — line order and metadata preserved
6.  Multiple pages — page_number is set correctly

Integration test (optional)
----------------------------
7.  Real PaddleOCR on a synthetic image
    Skipped automatically if the model is not cached.
    Run with: python -X utf8 tests/vision/test_ocr.py
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.ocr_base import BaseOCREngine, OCREngineConfig
from vision.ocr_config import (
    create_ocr_engine,
    DEFAULT_ENGINE,
    SUPPORTED_ENGINES,
)
from vision.ocr_result import OCRLine, OCRResult
from vision.ocr_paddle import PaddleOCREngine


# =========================================================
# HELPERS
# =========================================================

def make_gray_image(
    height: int = 100,
    width: int = 200
) -> np.ndarray:
    """
    Create a plain white grayscale image for testing.
    """
    return np.full(
        (height, width),
        255,
        dtype=np.uint8
    )


def make_paddle_raw_result(
    texts: list,
    scores: list,
    boxes: list = None
) -> list:
    """
    Build a fake PaddleOCR 3.x predict() return value.

    PaddleOCR returns a list containing one dict per image.
    """

    if boxes is None:
        boxes = [
            [[0, 0], [100, 0], [100, 20], [0, 20]]
            for _ in texts
        ]

    return [
        {
            "rec_texts": texts,
            "rec_scores": scores,
            "rec_boxes": boxes,
            "page_index": 0
        }
    ]


# =========================================================
# TEST 1 — SUCCESSFUL OCR
# =========================================================

print("\n========================================")
print("TEST 1 — SUCCESSFUL OCR")
print("========================================")

engine = PaddleOCREngine()

raw = make_paddle_raw_result(
    texts=["Hemoglobin", "15.9", "g/dl"],
    scores=[0.99, 0.97, 0.95]
)

with patch.object(
    engine,
    "_load_model"
):
    engine._model = MagicMock()
    engine._model.predict.return_value = raw

    result = engine.extract(
        make_gray_image(),
        page_number=0
    )

assert isinstance(result, OCRResult), (
    "extract() must return an OCRResult"
)

assert result.engine == "paddleocr"

assert result.page_number == 0

assert not result.is_empty, (
    "Result must not be empty"
)

assert "Hemoglobin" in result.text

assert result.line_count == 3

assert result.confidence is not None

assert result.confidence > 0.9, (
    f"Expected confidence > 0.9, got {result.confidence}"
)

assert not result.warnings, (
    f"No warnings expected, got: {result.warnings}"
)

print("Text:", repr(result.text))
print("Lines:", result.line_count)
print("Confidence:", round(result.confidence, 3))
print("Warnings:", result.warnings)

print("✓ PASSED")


# =========================================================
# TEST 2 — EMPTY OCR RESULT
# =========================================================

print("\n========================================")
print("TEST 2 — EMPTY OCR RESULT")
print("========================================")

engine = PaddleOCREngine()

raw_empty = make_paddle_raw_result(
    texts=[],
    scores=[]
)

with patch.object(engine, "_load_model"):
    engine._model = MagicMock()
    engine._model.predict.return_value = raw_empty

    result = engine.extract(make_gray_image())

assert result.is_empty, (
    "Result must be empty when no text is detected"
)

assert result.line_count == 0

assert result.text == ""

assert len(result.warnings) > 0, (
    "A warning must be attached for empty OCR output"
)

print("is_empty:", result.is_empty)
print("line_count:", result.line_count)
print("warnings:", result.warnings)

print("✓ PASSED")


# =========================================================
# TEST 3 — OCR FAILURE
# =========================================================

print("\n========================================")
print("TEST 3 — OCR FAILURE")
print("========================================")

engine = PaddleOCREngine()

with patch.object(engine, "_load_model"):
    engine._model = MagicMock()
    engine._model.predict.side_effect = Exception(
        "CUDA out of memory"
    )

    error_raised = False

    try:
        engine.extract(make_gray_image())

    except RuntimeError as error:
        error_raised = True
        print("Caught expected RuntimeError:", error)

assert error_raised, (
    "RuntimeError must be raised when predict() fails"
)

print("✓ PASSED")


# =========================================================
# TEST 4 — LOW-CONFIDENCE RESULT
# =========================================================

print("\n========================================")
print("TEST 4 — LOW-CONFIDENCE RESULT")
print("========================================")

engine = PaddleOCREngine(
    config=OCREngineConfig(
        confidence_threshold=0.8
    )
)

raw_low = make_paddle_raw_result(
    texts=["Hemoglobin", "1S.9"],
    scores=[0.95, 0.42]
)

with patch.object(engine, "_load_model"):
    engine._model = MagicMock()
    engine._model.predict.return_value = raw_low

    result = engine.extract(make_gray_image())

assert not result.is_empty

assert result.low_confidence is False, (
    "Mean confidence is above 0.6 so low_confidence "
    "must be False"
)

# The low-confidence line must be flagged in warnings
assert len(result.warnings) > 0, (
    "A warning must be attached for the low-confidence line"
)

low_conf_warning = any(
    "low confidence" in w.lower()
    for w in result.warnings
)

assert low_conf_warning, (
    f"Expected a low-confidence warning, "
    f"got: {result.warnings}"
)

# The low-confidence line must still appear in the text
assert "1S.9" in result.text, (
    "Low-confidence lines must still be included in text"
)

print("Confidence:", round(result.confidence, 3))
print("low_confidence flag:", result.low_confidence)
print("Warnings:", result.warnings)

print("✓ PASSED")


# =========================================================
# TEST 5 — MULTIPLE LINES
# =========================================================

print("\n========================================")
print("TEST 5 — MULTIPLE LINES")
print("========================================")

engine = PaddleOCREngine()

texts = [
    "Patient Name: Test Patient",
    "Age / Gender : 34 Years/Male",
    "Hemoglobin",
    "15.9",
    "g/dl",
    "[13.0-18.0]",
    "Total WBC Count",
    "7200",
    "/cmm",
    "[4000-11000]",
]

scores = [0.99] * len(texts)

raw_multi = make_paddle_raw_result(
    texts=texts,
    scores=scores
)

with patch.object(engine, "_load_model"):
    engine._model = MagicMock()
    engine._model.predict.return_value = raw_multi

    result = engine.extract(make_gray_image())

assert result.line_count == len(texts), (
    f"Expected {len(texts)} lines, "
    f"got {result.line_count}"
)

# Line order must be preserved
for index, expected_text in enumerate(texts):
    assert result.lines[index].text == expected_text, (
        f"Line {index}: expected {expected_text!r}, "
        f"got {result.lines[index].text!r}"
    )

# line_index must match position
for index, line in enumerate(result.lines):
    assert line.line_index == index, (
        f"line_index mismatch at position {index}"
    )

# All lines must have bounding boxes
for line in result.lines:
    assert line.bounding_box is not None, (
        f"Line {line.line_index} missing bounding_box"
    )
    assert len(line.bounding_box) == 4, (
        "Bounding box must have 4 corner points"
    )

# Full text must contain all lines joined by newlines
expected_full_text = "\n".join(texts)

assert result.text == expected_full_text, (
    "Full text must be lines joined by newlines"
)

print("Lines:", result.line_count)
print("First line:", result.lines[0].text)
print("Last line:", result.lines[-1].text)
print("Bounding box sample:", result.lines[0].bounding_box)

print("✓ PASSED")


# =========================================================
# TEST 6 — MULTIPLE PAGES
# =========================================================

print("\n========================================")
print("TEST 6 — MULTIPLE PAGES")
print("========================================")

engine = PaddleOCREngine()

page_texts = [
    ["CBC REPORT", "Page 1"],
    ["Hemoglobin", "15.9"],
    ["Total WBC Count", "7200"],
]

page_scores = [
    [0.99, 0.98],
    [0.97, 0.96],
    [0.95, 0.94],
]

results = []

for page_num, (texts, scores) in enumerate(
    zip(page_texts, page_scores)
):

    raw = make_paddle_raw_result(
        texts=texts,
        scores=scores
    )

    with patch.object(engine, "_load_model"):
        engine._model = MagicMock()
        engine._model.predict.return_value = raw

        result = engine.extract(
            make_gray_image(),
            page_number=page_num
        )

    results.append(result)

assert len(results) == 3, (
    "Must have one result per page"
)

for page_num, result in enumerate(results):

    assert result.page_number == page_num, (
        f"Page {page_num}: expected page_number="
        f"{page_num}, got {result.page_number}"
    )

    assert result.line_count == len(
        page_texts[page_num]
    ), (
        f"Page {page_num}: expected "
        f"{len(page_texts[page_num])} lines, "
        f"got {result.line_count}"
    )

    assert not result.is_empty

    print(
        f"Page {page_num}: "
        f"{result.line_count} lines, "
        f"conf={result.confidence:.3f}"
    )

print("✓ PASSED")


# =========================================================
# ADDITIONAL UNIT TESTS
# =========================================================

# ---------------------------------------------------------
# OCRResult model properties
# ---------------------------------------------------------

print("\n========================================")
print("TEST — OCRResult MODEL PROPERTIES")
print("========================================")

# is_empty
empty_result = OCRResult(
    text="",
    engine="test"
)
assert empty_result.is_empty

whitespace_result = OCRResult(
    text="   \n  ",
    engine="test"
)
assert whitespace_result.is_empty

non_empty_result = OCRResult(
    text="Hemoglobin",
    engine="test"
)
assert not non_empty_result.is_empty

# low_confidence
low_conf_result = OCRResult(
    text="text",
    confidence=0.45,
    engine="test"
)
assert low_conf_result.low_confidence

high_conf_result = OCRResult(
    text="text",
    confidence=0.95,
    engine="test"
)
assert not high_conf_result.low_confidence

no_conf_result = OCRResult(
    text="text",
    confidence=None,
    engine="test"
)
assert not no_conf_result.low_confidence

print("is_empty: OK")
print("low_confidence: OK")
print("✓ PASSED")


# ---------------------------------------------------------
# BaseOCREngine input validation
# ---------------------------------------------------------

print("\n========================================")
print("TEST — INPUT VALIDATION")
print("========================================")

engine = PaddleOCREngine()

# Not a numpy array
error_raised = False
try:
    engine._validate_input("not_an_array")
except ValueError as e:
    error_raised = True
    print("Non-array error:", e)
assert error_raised

# Empty array
error_raised = False
try:
    engine._validate_input(np.array([], dtype=np.uint8))
except ValueError as e:
    error_raised = True
    print("Empty array error:", e)
assert error_raised

# Wrong dtype
error_raised = False
try:
    engine._validate_input(
        np.zeros((100, 100), dtype=np.float32)
    )
except ValueError as e:
    error_raised = True
    print("Wrong dtype error:", e)
assert error_raised

# Valid grayscale — must not raise
engine._validate_input(make_gray_image())
print("Valid grayscale: OK")

# Valid BGR — must not raise
bgr = np.full((100, 200, 3), 255, dtype=np.uint8)
engine._validate_input(bgr)
print("Valid BGR: OK")

print("✓ PASSED")


# ---------------------------------------------------------
# create_ocr_engine factory
# ---------------------------------------------------------

print("\n========================================")
print("TEST — create_ocr_engine FACTORY")
print("========================================")

engine = create_ocr_engine("paddle")
assert isinstance(engine, PaddleOCREngine)
print("paddle engine created:", type(engine).__name__)

engine_default = create_ocr_engine()
assert isinstance(engine_default, PaddleOCREngine)
print("default engine created:", type(engine_default).__name__)

error_raised = False
try:
    create_ocr_engine("nonexistent_engine")
except ValueError as e:
    error_raised = True
    print("Unknown engine error:", e)
assert error_raised

print("✓ PASSED")


# ---------------------------------------------------------
# OCRLine repr and fields
# ---------------------------------------------------------

print("\n========================================")
print("TEST — OCRLine FIELDS")
print("========================================")

line = OCRLine(
    text="Hemoglobin",
    confidence=0.99,
    bounding_box=[
        (0.0, 0.0),
        (100.0, 0.0),
        (100.0, 20.0),
        (0.0, 20.0)
    ],
    line_index=0
)

assert line.text == "Hemoglobin"
assert line.confidence == 0.99
assert len(line.bounding_box) == 4
assert line.line_index == 0

print("OCRLine repr:", repr(line))
print("✓ PASSED")


# ---------------------------------------------------------
# _parse_box edge cases
# ---------------------------------------------------------

print("\n========================================")
print("TEST — _parse_box EDGE CASES")
print("========================================")

engine = PaddleOCREngine()

# Valid box
valid_box = [[0, 0], [100, 0], [100, 20], [0, 20]]
parsed = engine._parse_box(valid_box)
assert parsed is not None
assert len(parsed) == 4
print("Valid box parsed:", parsed)

# Wrong shape
bad_box = [[0, 0], [100, 0]]
parsed_bad = engine._parse_box(bad_box)
assert parsed_bad is None
print("Bad box returned None: OK")

# None input
parsed_none = engine._parse_box(None)
assert parsed_none is None
print("None box returned None: OK")

print("✓ PASSED")


# =========================================================
# INTEGRATION TEST (optional)
# =========================================================

print("\n========================================")
print("TEST 7 — INTEGRATION (real PaddleOCR)")
print("========================================")

import os
import cv2

_PADDLE_CACHE = Path.home() / ".paddleocr"

_model_cached = _PADDLE_CACHE.exists() and any(
    _PADDLE_CACHE.rglob("*.pdmodel")
)

if not _model_cached:

    print(
        "SKIPPED — PaddleOCR model not cached locally."
    )
    print(
        "Run once with internet access to download "
        "the model, then re-run this test."
    )

else:

    print("Model cache found — running real OCR...")

    # Build a synthetic blood-report-like image
    image = np.full((400, 600, 3), 255, dtype=np.uint8)

    labels = [
        "Hemoglobin",
        "15.9",
        "g/dl",
        "[13.0-18.0]",
    ]

    y = 60

    for label in labels:
        cv2.putText(
            image,
            label,
            (30, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 0),
            2,
            cv2.LINE_AA
        )
        y += 70

    real_engine = PaddleOCREngine(
        config=OCREngineConfig(lang="en")
    )

    real_result = real_engine.extract(image, page_number=0)

    assert isinstance(real_result, OCRResult)
    assert real_result.engine == "paddleocr"
    assert real_result.page_number == 0

    print("Engine:", real_result.engine)
    print("Lines:", real_result.line_count)
    print("Confidence:", real_result.confidence)
    print("Text:\n", real_result.text)
    print("Warnings:", real_result.warnings)

    print("✓ PASSED (integration)")


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("   ALL OCR TESTS PASSED")
print("========================================")
