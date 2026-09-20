"""
tests/vision/test_scanned_pdf.py

Unit tests for PART 4: Scanned PDF → Image → OCR support.

All tests are fully mocked.
No internet access, no model download, no real PDF required.

Tests
-----
 1. One-page scanned PDF — OCR text returned
 2. Multi-page scanned PDF — all pages OCR'd, order preserved
 3. Mixed text/image PDF — text pages use embedded text, scanned use OCR
 4. Empty page — empty page produces empty block, warning attached
 5. Invalid PDF path — FileNotFoundError raised
 6. Non-PDF file — ValueError raised
 7. Corrupted PDF (cannot open) — ValueError raised
 8. Render failure on one page — page skipped, warning attached
 9. Fully text PDF — OCR engine never called
10. Page assembly — --- PAGE N --- markers in correct order
11. PDFClassification properties — is_fully_text / is_fully_scanned / is_mixed
12. classify_pdf threshold — pages below MIN_TEXT_CHARS → SCANNED
13. get_page_count — returns correct count
14. ScannedPDFResult properties — page_count, ocr_page_count, text_page_count
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.pdf_classifier import (
    PDFClassification,
    PDFPageType,
    classify_pdf,
    MIN_TEXT_CHARS,
)
from vision.pdf_renderer import render_pdf_pages, get_page_count
from vision.scanned_pdf_reader import (
    ScannedPDFResult,
    read_pdf,
    _assemble_pages,
)
from vision.ocr_base import OCREngineConfig
from vision.ocr_result import OCRLine, OCRResult


# =========================================================
# HELPERS
# =========================================================

def _gray(h=100, w=200) -> np.ndarray:
    return np.full((h, w), 255, dtype=np.uint8)


def _bgr(h=100, w=200) -> np.ndarray:
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _make_ocr_result(text: str, page: int = 0) -> OCRResult:
    lines = [
        OCRLine(text=t, confidence=0.99, line_index=i)
        for i, t in enumerate(text.splitlines())
        if t
    ]
    return OCRResult(
        text=text,
        lines=lines,
        page_number=page,
        engine="paddleocr",
        confidence=0.99,
    )


def _make_classification(page_types: dict) -> PDFClassification:
    c = PDFClassification()
    c.page_types = {
        i: (PDFPageType.TEXT if t == "text" else PDFPageType.SCANNED)
        for i, t in page_types.items()
    }
    return c


def _fake_pdf_path(tmp_path_str: str = r"C:\fake\report.pdf") -> Path:
    """Return a Path that appears to exist via mock."""
    return Path(tmp_path_str)


# =========================================================
# TEST 1 — ONE-PAGE SCANNED PDF
# =========================================================

print("\n========================================")
print("TEST 1 — ONE-PAGE SCANNED PDF")
print("========================================")

mock_engine = MagicMock()
mock_engine.extract.return_value = _make_ocr_result(
    "Hemoglobin\n15.9\ng/dl\n[13.0-18.0]"
)

classification = _make_classification({0: "scanned"})

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification), \
     patch("vision.scanned_pdf_reader.render_pdf_pages",
           return_value=iter([(0, _bgr())])), \
     patch("vision.scanned_pdf_reader.preprocess_image") as mock_pre, \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    mock_pre.return_value = MagicMock(image=_gray())

    result = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine,
    )

assert isinstance(result, ScannedPDFResult)
assert result.page_count == 1
assert result.ocr_page_count == 1
assert result.text_page_count == 0
assert "Hemoglobin" in result.text
assert "--- PAGE 1 ---" in result.text
assert mock_engine.extract.call_count == 1

print("page_count:", result.page_count)
print("ocr_page_count:", result.ocr_page_count)
print("text snippet:", result.text[:60])
print("✓ PASSED")


# =========================================================
# TEST 2 — MULTI-PAGE SCANNED PDF
# =========================================================

print("\n========================================")
print("TEST 2 — MULTI-PAGE SCANNED PDF")
print("========================================")

page_texts = [
    "CBC REPORT\nPage 1",
    "Hemoglobin\n15.9",
    "Total WBC Count\n7200",
]

mock_engine2 = MagicMock()
mock_engine2.extract.side_effect = [
    _make_ocr_result(t, page=i)
    for i, t in enumerate(page_texts)
]

classification2 = _make_classification({0: "scanned", 1: "scanned", 2: "scanned"})

rendered_pages = [(i, _bgr()) for i in range(3)]

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification2), \
     patch("vision.scanned_pdf_reader.render_pdf_pages",
           return_value=iter(rendered_pages)), \
     patch("vision.scanned_pdf_reader.preprocess_image") as mock_pre2, \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    mock_pre2.return_value = MagicMock(image=_gray())

    result2 = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine2,
    )

assert result2.page_count == 3
assert result2.ocr_page_count == 3
assert mock_engine2.extract.call_count == 3

# Page order preserved
assert result2.text.index("--- PAGE 1 ---") < result2.text.index("--- PAGE 2 ---")
assert result2.text.index("--- PAGE 2 ---") < result2.text.index("--- PAGE 3 ---")

# Content from each page present
assert "CBC REPORT" in result2.text
assert "Hemoglobin" in result2.text
assert "Total WBC Count" in result2.text

print("page_count:", result2.page_count)
print("ocr_page_count:", result2.ocr_page_count)
print("page order preserved: OK")
print("✓ PASSED")


# =========================================================
# TEST 3 — MIXED TEXT/IMAGE PDF
# =========================================================

print("\n========================================")
print("TEST 3 — MIXED TEXT/IMAGE PDF")
print("========================================")

mock_engine3 = MagicMock()
mock_engine3.extract.return_value = _make_ocr_result(
    "Scanned page content"
)

# Page 0 = text, page 1 = scanned, page 2 = text
classification3 = _make_classification({
    0: "text",
    1: "scanned",
    2: "text",
})

embedded_texts = {
    0: "Embedded text page 1",
    2: "Embedded text page 3",
}

def fake_embedded(doc, idx):
    return embedded_texts.get(idx, "")

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification3), \
     patch("vision.scanned_pdf_reader.render_pdf_pages",
           return_value=iter([(1, _bgr())])), \
     patch("vision.scanned_pdf_reader.preprocess_image") as mock_pre3, \
     patch("vision.scanned_pdf_reader._extract_page_text_embedded",
           side_effect=fake_embedded), \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    mock_pre3.return_value = MagicMock(image=_gray())

    result3 = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine3,
    )

assert result3.page_count == 3
assert result3.ocr_page_count == 1
assert result3.text_page_count == 2

# OCR engine called only for scanned page
assert mock_engine3.extract.call_count == 1

# Embedded text pages present
assert "Embedded text page 1" in result3.text
assert "Embedded text page 3" in result3.text
assert "Scanned page content" in result3.text

print("page_count:", result3.page_count)
print("text_page_count:", result3.text_page_count)
print("ocr_page_count:", result3.ocr_page_count)
print("✓ PASSED")


# =========================================================
# TEST 4 — EMPTY PAGE
# =========================================================

print("\n========================================")
print("TEST 4 — EMPTY PAGE")
print("========================================")

mock_engine4 = MagicMock()
# OCR returns empty text for the empty page
mock_engine4.extract.return_value = OCRResult(
    text="",
    lines=[],
    page_number=0,
    engine="paddleocr",
    confidence=None,
    warnings=["No text detected on this page."],
)

classification4 = _make_classification({0: "scanned"})

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification4), \
     patch("vision.scanned_pdf_reader.render_pdf_pages",
           return_value=iter([(0, _bgr())])), \
     patch("vision.scanned_pdf_reader.preprocess_image") as mock_pre4, \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    mock_pre4.return_value = MagicMock(image=_gray())

    result4 = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine4,
    )

assert result4.page_count == 1
assert result4.ocr_page_count == 1
# Empty page produces a warning
assert len(result4.warnings) > 0
assert any("no text" in w.lower() or "Page 1" in w for w in result4.warnings)
# Page marker still present
assert "--- PAGE 1 ---" in result4.text

print("warnings:", result4.warnings)
print("text:", repr(result4.text))
print("✓ PASSED")


# =========================================================
# TEST 5 — INVALID PDF PATH
# =========================================================

print("\n========================================")
print("TEST 5 — INVALID PDF PATH")
print("========================================")

error_raised = False
try:
    read_pdf(Path(r"C:\does\not\exist.pdf"))
except FileNotFoundError as e:
    error_raised = True
    print("Caught FileNotFoundError:", e)

assert error_raised, "FileNotFoundError must be raised for missing PDF"
print("✓ PASSED")


# =========================================================
# TEST 6 — NON-PDF FILE
# =========================================================

print("\n========================================")
print("TEST 6 — NON-PDF FILE")
print("========================================")

import tempfile, os

with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
    tmp.write(b"\xff\xd8\xff")
    tmp_path = tmp.name

error_raised = False
try:
    read_pdf(Path(tmp_path))
except ValueError as e:
    error_raised = True
    print("Caught ValueError:", e)
finally:
    os.unlink(tmp_path)

assert error_raised, "ValueError must be raised for non-PDF file"
print("✓ PASSED")


# =========================================================
# TEST 7 — CORRUPTED PDF (cannot open)
# =========================================================

print("\n========================================")
print("TEST 7 — CORRUPTED PDF (cannot open)")
print("========================================")

import tempfile

with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
    tmp.write(b"not a real pdf content")
    corrupt_path = tmp.name

error_raised = False
try:
    classify_pdf(Path(corrupt_path))
except ValueError as e:
    error_raised = True
    print("Caught ValueError from classify_pdf:", e)
finally:
    os.unlink(corrupt_path)

assert error_raised, "ValueError must be raised for corrupted PDF"
print("✓ PASSED")


# =========================================================
# TEST 8 — RENDER FAILURE ON ONE PAGE
# =========================================================

print("\n========================================")
print("TEST 8 — RENDER FAILURE ON ONE PAGE")
print("========================================")

mock_engine8 = MagicMock()
mock_engine8.extract.return_value = _make_ocr_result("Good page text")

classification8 = _make_classification({0: "scanned", 1: "scanned"})

# Page 0 renders fine, page 1 returns None (render failure)
rendered8 = [(0, _bgr()), (1, None)]

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification8), \
     patch("vision.scanned_pdf_reader.render_pdf_pages",
           return_value=iter(rendered8)), \
     patch("vision.scanned_pdf_reader.preprocess_image") as mock_pre8, \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    mock_pre8.return_value = MagicMock(image=_gray())

    result8 = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine8,
    )

assert result8.page_count == 2
# OCR called only for the page that rendered successfully
assert mock_engine8.extract.call_count == 1
# Warning for the failed page
assert len(result8.warnings) > 0
assert any("render" in w.lower() or "Page 2" in w for w in result8.warnings)
# Both page markers present
assert "--- PAGE 1 ---" in result8.text
assert "--- PAGE 2 ---" in result8.text

print("warnings:", result8.warnings)
print("ocr calls:", mock_engine8.extract.call_count)
print("✓ PASSED")


# =========================================================
# TEST 9 — FULLY TEXT PDF (OCR engine never called)
# =========================================================

print("\n========================================")
print("TEST 9 — FULLY TEXT PDF")
print("========================================")

mock_engine9 = MagicMock()

classification9 = _make_classification({0: "text", 1: "text"})

embedded9 = {0: "Page one text", 1: "Page two text"}

def fake_emb9(doc, idx):
    return embedded9.get(idx, "")

with patch("vision.scanned_pdf_reader.classify_pdf", return_value=classification9), \
     patch("vision.scanned_pdf_reader._extract_page_text_embedded",
           side_effect=fake_emb9), \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pymupdf.open"):

    result9 = read_pdf(
        Path(r"C:\fake\report.pdf"),
        ocr_engine=mock_engine9,
    )

assert result9.page_count == 2
assert result9.ocr_page_count == 0
assert result9.text_page_count == 2
# OCR engine must never be called
assert mock_engine9.extract.call_count == 0
assert "Page one text" in result9.text
assert "Page two text" in result9.text

print("ocr_page_count:", result9.ocr_page_count)
print("engine calls:", mock_engine9.extract.call_count)
print("✓ PASSED")


# =========================================================
# TEST 10 — PAGE ASSEMBLY ORDER
# =========================================================

print("\n========================================")
print("TEST 10 — PAGE ASSEMBLY ORDER")
print("========================================")

page_texts = {
    0: "First page",
    1: "Second page",
    2: "Third page",
    3: "Fourth page",
}

assembled = _assemble_pages(page_texts, page_count=4)

# All markers present
for n in range(1, 5):
    assert f"--- PAGE {n} ---" in assembled, f"Missing PAGE {n} marker"

# Correct order
positions = [assembled.index(f"--- PAGE {n} ---") for n in range(1, 5)]
assert positions == sorted(positions), "Page markers must be in order"

# Content present
for text in page_texts.values():
    assert text in assembled

# Missing page index → empty block (no crash)
partial = _assemble_pages({0: "Only page"}, page_count=3)
assert "--- PAGE 1 ---" in partial
assert "--- PAGE 2 ---" in partial
assert "--- PAGE 3 ---" in partial

print("All markers present and ordered: OK")
print("Missing page handled gracefully: OK")
print("✓ PASSED")


# =========================================================
# TEST 11 — PDFClassification PROPERTIES
# =========================================================

print("\n========================================")
print("TEST 11 — PDFClassification PROPERTIES")
print("========================================")

# Fully text
c_text = _make_classification({0: "text", 1: "text", 2: "text"})
assert c_text.is_fully_text
assert not c_text.is_fully_scanned
assert not c_text.is_mixed
assert c_text.scanned_pages() == []
assert c_text.text_pages() == [0, 1, 2]

# Fully scanned
c_scan = _make_classification({0: "scanned", 1: "scanned"})
assert not c_scan.is_fully_text
assert c_scan.is_fully_scanned
assert not c_scan.is_mixed
assert c_scan.text_pages() == []
assert c_scan.scanned_pages() == [0, 1]

# Mixed
c_mix = _make_classification({0: "text", 1: "scanned", 2: "text"})
assert not c_mix.is_fully_text
assert not c_mix.is_fully_scanned
assert c_mix.is_mixed
assert c_mix.scanned_pages() == [1]
assert c_mix.text_pages() == [0, 2]

print("is_fully_text: OK")
print("is_fully_scanned: OK")
print("is_mixed: OK")
print("scanned_pages / text_pages: OK")
print("✓ PASSED")


# =========================================================
# TEST 12 — classify_pdf THRESHOLD
# =========================================================

print("\n========================================")
print("TEST 12 — classify_pdf THRESHOLD")
print("========================================")

import pymupdf as _pymupdf

# Build fake pymupdf pages
def _make_fake_doc(page_texts_list):
    """Return a mock pymupdf.Document with given per-page texts."""
    doc = MagicMock()
    doc.page_count = len(page_texts_list)
    pages = []
    for t in page_texts_list:
        pg = MagicMock()
        pg.get_text.return_value = t
        pages.append(pg)
    doc.__getitem__ = lambda self, i: pages[i]
    doc.__enter__ = lambda self: self
    doc.__exit__ = MagicMock(return_value=False)
    doc.close = MagicMock()
    return doc

fake_doc = _make_fake_doc([
    "A" * (MIN_TEXT_CHARS + 10),   # page 0 → TEXT
    "B" * (MIN_TEXT_CHARS - 1),    # page 1 → SCANNED (below threshold)
    "",                             # page 2 → SCANNED (empty)
    "C" * MIN_TEXT_CHARS,          # page 3 → TEXT (exactly at threshold)
])

import pymupdf as _pymupdf_mod

with patch.object(_pymupdf_mod, "open", return_value=fake_doc), \
     patch("pathlib.Path.exists", return_value=True), \
     patch("pathlib.Path.suffix", new_callable=PropertyMock, return_value=".pdf"):

    clf = classify_pdf(Path(r"C:\fake\report.pdf"))

assert clf.page_types[0] == PDFPageType.TEXT,   "Above threshold → TEXT"
assert clf.page_types[1] == PDFPageType.SCANNED, "Below threshold → SCANNED"
assert clf.page_types[2] == PDFPageType.SCANNED, "Empty → SCANNED"
assert clf.page_types[3] == PDFPageType.TEXT,   "Exactly at threshold → TEXT"

print(f"page 0 (chars={MIN_TEXT_CHARS+10}): {clf.page_types[0].value}")
print(f"page 1 (chars={MIN_TEXT_CHARS-1}): {clf.page_types[1].value}")
print(f"page 2 (chars=0): {clf.page_types[2].value}")
print(f"page 3 (chars={MIN_TEXT_CHARS}): {clf.page_types[3].value}")
print("✓ PASSED")


# =========================================================
# TEST 13 — get_page_count
# =========================================================

print("\n========================================")
print("TEST 13 — get_page_count")
print("========================================")

fake_doc13 = MagicMock()
fake_doc13.page_count = 7
fake_doc13.close = MagicMock()

import pymupdf as _pymupdf_mod13

with patch.object(_pymupdf_mod13, "open", return_value=fake_doc13), \
     patch("pathlib.Path.exists", return_value=True):

    count = get_page_count(Path(r"C:\fake\report.pdf"))

assert count == 7
print("page_count:", count)
print("✓ PASSED")

# FileNotFoundError for missing path
error_raised = False
try:
    get_page_count(Path(r"C:\no\such\file.pdf"))
except FileNotFoundError:
    error_raised = True
assert error_raised
print("FileNotFoundError for missing path: OK")
print("✓ PASSED")


# =========================================================
# TEST 14 — ScannedPDFResult PROPERTIES
# =========================================================

print("\n========================================")
print("TEST 14 — ScannedPDFResult PROPERTIES")
print("========================================")

clf14 = _make_classification({0: "text", 1: "scanned", 2: "scanned"})

res14 = ScannedPDFResult(
    text="some text",
    classification=clf14,
    ocr_page_count=2,
    warnings=["warn1"],
)

assert res14.page_count == 3
assert res14.ocr_page_count == 2
assert res14.text_page_count == 1
assert res14.warnings == ["warn1"]
assert repr(res14).startswith("ScannedPDFResult(")

print("page_count:", res14.page_count)
print("ocr_page_count:", res14.ocr_page_count)
print("text_page_count:", res14.text_page_count)
print("repr:", repr(res14))
print("✓ PASSED")


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("   ALL SCANNED PDF TESTS PASSED")
print("========================================")
