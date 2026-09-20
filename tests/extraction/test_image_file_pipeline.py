"""Tests that image file paths enter the existing Vision/OCR path."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from extraction.pipeline import InputType, process
from vision.ocr_result import OCRResult


ROOT = Path(__file__).resolve().parents[2]


def _ocr(text: str) -> OCRResult:
    return OCRResult(
        text=text,
        lines=[],
        page_number=0,
        engine="test",
        confidence=0.99,
    )


print("\n========================================")
print("TEST 1 — IMAGE FILE ROUTES TO VISION")
print("========================================")

image = ROOT / "samples" / "reports" / "test_pipeline_input.png"
image.write_bytes(b"test")

engine = MagicMock()
engine.extract.return_value = _ocr("Age / Gender : 34 Years/Male\nHemoglobin\n15.9\ng/dl\n[13-18]")

try:
    with patch("vision.preprocessor.load_image", return_value=np.zeros((10, 10, 3), dtype=np.uint8)) as load, \
         patch("vision.preprocessor.preprocess_image", return_value=MagicMock(image=np.zeros((10, 10), dtype=np.uint8))):
        result = process(image, ocr_engine=engine)

    assert result.source.input_type is InputType.IMAGE
    assert result.source.path == str(image)
    assert result.source.ocr_pages == 1
    assert load.call_count == 1
    assert engine.extract.call_count == 1
    print("input_type:", result.source.input_type.value)
    print("ocr_pages:", result.source.ocr_pages)
    print("✓ PASSED")
finally:
    image.unlink(missing_ok=True)


print("\n========================================")
print("TEST 2 — PDF ROUTING REMAINS UNCHANGED")
print("========================================")

from extraction.pipeline import SourceMeta

with patch("extraction.pipeline._process_text_pdf", return_value=(
    "Age / Gender : 34 Years/Male\nHemoglobin\n15.9\ng/dl\n[13-18]",
    SourceMeta(input_type=InputType.TEXT_PDF, path="report.pdf", page_count=1),
)), \
     patch("vision.pdf_classifier.classify_pdf") as classifier, \
     patch("pathlib.Path.exists", return_value=True):

    classifier.return_value.is_fully_text = True
    result_pdf = process("report.pdf", ocr_engine=engine)

assert result_pdf.source.input_type is InputType.TEXT_PDF
assert engine.extract.call_count == 1  # no new OCR call from the PDF route
print("input_type:", result_pdf.source.input_type.value)
print("✓ PASSED")


print("\n========================================")
print("ALL IMAGE PIPELINE TESTS PASSED")
print("========================================")