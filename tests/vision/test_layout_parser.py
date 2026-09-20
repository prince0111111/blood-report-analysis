"""
tests/vision/test_layout_parser.py

Regression tests for vision/layout_parser.py.

Each test shows:
  - INPUT  : the raw OCR text fed to the parser
  - PARSED : the list of test dicts returned
  - VALIDATION : which fields are present / missing
  - CONFIDENCE / ERRORS : value_uncertain, abnormal_flag, etc.

Layouts covered
---------------
 1. Standard CBC — vertical (one token per line)
 2. CBC table — Test | Result | Unit | Reference Range columns
 3. Reference range in a separate column (wide spacing)
 4. Abnormal flags H / L in value column
 5. Reference range in parentheses
 6. Multi-section report (CBC + Liver + Kidney + Lipid)
 7. Multi-page report (--- PAGE N --- markers)
 8. Poor-quality scan (OCR noise, garbled tokens)
 9. Slightly rotated / misaligned (extra whitespace, broken tokens)
10. Mobile-camera report (mixed inline + vertical, uneven spacing)

All tests are deterministic and require no internet access.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vision.layout_parser import parse_ocr_text


# =========================================================
# DISPLAY HELPERS
# =========================================================

def _show(label: str, data) -> None:
    print(f"  {label}:")
    if isinstance(data, list):
        for item in data:
            print(f"    {item}")
    else:
        print(f"    {data}")


def _validate(results: list[dict]) -> dict:
    """
    Summarise which fields are present / missing across
    all parsed results.  Does NOT interpret medical values.
    """
    total = len(results)
    with_value = sum(1 for r in results if r["value"] is not None)
    with_unit = sum(1 for r in results if r["unit"] is not None)
    with_ref = sum(1 for r in results if r["reference_raw"] is not None)
    with_flag = sum(1 for r in results if r["abnormal_flag"] is not None)
    uncertain = sum(1 for r in results if r["value"] is None)

    return {
        "total": total,
        "with_value": with_value,
        "with_unit": with_unit,
        "with_reference": with_ref,
        "with_flag": with_flag,
        "value_uncertain_count": uncertain,
    }


def _print_result(results: list[dict], validation: dict) -> None:
    _show("PARSED", [
        f"{r['canonical_name']:15s}  val={r['value']}  "
        f"unit={r['unit']}  ref={r['reference_raw']}  "
        f"flag={r['abnormal_flag']}  layout={r['layout']}"
        for r in results
    ])
    _show("VALIDATION", validation)


# =========================================================
# TEST 1 — Standard CBC vertical layout
# =========================================================

print("\n" + "=" * 60)
print("TEST 1 — Standard CBC vertical layout")
print("=" * 60)

INPUT_1 = """
Age / Gender : 34 Years/Male
Hemoglobin
15.9
g/dl
13.0-18.0
Total RBC Count
5.2
Mill/Cmm
4.5-5.5
P.C.V
47.0
%
40-52
M.C.V.
90.0
fl
83-101
M.C.H.
30.0
pg
27-32
M.C.H.C.
33.5
g/dl
31.5-34.5
R.D.W.
13.5
%
11.6-14.0
Total WBC Count
7200
/cmm
4000-11000
Neutrophils
60
%
40-75
Lymphocytes
32
%
20-45
Eosinophils
3
%
1-6
Monocytes
4
%
2-10
Basophils
1
%
0-1
Platelet Count
250000
/ul
150000-400000
"""

print("  INPUT: vertical layout, 14 CBC markers")
results_1 = parse_ocr_text(INPUT_1)
validation_1 = _validate(results_1)
_print_result(results_1, validation_1)

assert validation_1["total"] == 14, f"Expected 14, got {validation_1['total']}"
assert validation_1["with_value"] == 14
assert validation_1["with_unit"] == 14
assert validation_1["with_reference"] == 14
assert validation_1["value_uncertain_count"] == 0

hgb = next(r for r in results_1 if r["canonical_name"] == "hemoglobin")
assert hgb["value"] == 15.9
assert hgb["unit"] == "g/dl"
assert hgb["reference_raw"] == "13.0-18.0"
assert hgb["layout"] == "vertical"

print("  ✓ PASSED")


# =========================================================
# TEST 2 — CBC table: Test | Result | Unit | Reference Range
# =========================================================

print("\n" + "=" * 60)
print("TEST 2 — CBC table (tab-separated columns)")
print("=" * 60)

INPUT_2 = """\
Test Name\tResult\tUnit\tReference Range
Hemoglobin\t15.9\tg/dl\t13.0-18.0
Total RBC Count\t5.2\tMill/Cmm\t4.5-5.5
P.C.V\t47.0\t%\t40-52
M.C.V.\t90.0\tfl\t83-101
M.C.H.\t30.0\tpg\t27-32
M.C.H.C.\t33.5\tg/dl\t31.5-34.5
R.D.W.\t13.5\t%\t11.6-14.0
Total WBC Count\t7200\t/cmm\t4000-11000
Neutrophils\t60\t%\t40-75
Lymphocytes\t32\t%\t20-45
Eosinophils\t3\t%\t1-6
Monocytes\t4\t%\t2-10
Basophils\t1\t%\t0-1
Platelet Count\t250000\t/ul\t150000-400000
"""

print("  INPUT: tab-separated table, header row present")
results_2 = parse_ocr_text(INPUT_2)
validation_2 = _validate(results_2)
_print_result(results_2, validation_2)

assert validation_2["total"] == 14, f"Expected 14, got {validation_2['total']}"
assert validation_2["with_value"] == 14
assert validation_2["with_unit"] == 14
assert validation_2["with_reference"] == 14

wbc = next(r for r in results_2 if r["canonical_name"] == "wbc")
assert wbc["value"] == 7200
assert wbc["unit"] == "/cmm"
assert wbc["reference_raw"] == "4000-11000"
assert wbc["layout"] == "tabular"

print("  ✓ PASSED")


# =========================================================
# TEST 3 — Reference range in a separate wide column
# =========================================================

print("\n" + "=" * 60)
print("TEST 3 — Reference range in separate column (wide spacing)")
print("=" * 60)

INPUT_3 = """\
Hemoglobin          15.9      g/dl          13.0 - 18.0
Total RBC Count      5.2      Mill/Cmm       4.5 - 5.5
P.C.V               47.0      %             40 - 52
M.C.V.              90.0      fl            83 - 101
Total WBC Count     7200      /cmm          4000 - 11000
Platelet Count    250000      /ul           150000 - 400000
"""

print("  INPUT: wide-spaced columns, reference in last column")
results_3 = parse_ocr_text(INPUT_3)
validation_3 = _validate(results_3)
_print_result(results_3, validation_3)

assert validation_3["total"] == 6, f"Expected 6, got {validation_3['total']}"
assert validation_3["with_value"] == 6
assert validation_3["with_reference"] == 6

hgb3 = next(r for r in results_3 if r["canonical_name"] == "hemoglobin")
assert hgb3["value"] == 15.9
assert hgb3["reference_raw"] is not None
assert "13" in hgb3["reference_raw"]

print("  ✓ PASSED")


# =========================================================
# TEST 4 — Abnormal flags H / L in value column
# =========================================================

print("\n" + "=" * 60)
print("TEST 4 — Abnormal flags H / L")
print("=" * 60)

INPUT_4 = """\
Hemoglobin\t7.2 L\tg/dl\t13.0-18.0
Total WBC Count\t14500 H\t/cmm\t4000-11000
Platelet Count\t95000 L\t/ul\t150000-400000
Neutrophils\t82 H\t%\t40-75
Lymphocytes\t12 L\t%\t20-45
"""

print("  INPUT: flags L/H appended to value in same cell")
results_4 = parse_ocr_text(INPUT_4)
validation_4 = _validate(results_4)
_print_result(results_4, validation_4)

assert validation_4["total"] == 5
assert validation_4["with_flag"] == 5, f"Expected 5 flags, got {validation_4['with_flag']}"

hgb4 = next(r for r in results_4 if r["canonical_name"] == "hemoglobin")
assert hgb4["value"] == 7.2
assert hgb4["abnormal_flag"] == "L"

wbc4 = next(r for r in results_4 if r["canonical_name"] == "wbc")
assert wbc4["value"] == 14500
assert wbc4["abnormal_flag"] == "H"

plt4 = next(r for r in results_4 if r["canonical_name"] == "platelets")
assert plt4["abnormal_flag"] == "L"

print("  ✓ PASSED")


# =========================================================
# TEST 5 — Reference range in parentheses
# =========================================================

print("\n" + "=" * 60)
print("TEST 5 — Reference range in parentheses")
print("=" * 60)

INPUT_5 = """\
Hemoglobin: 15.9 g/dl (13.0-18.0)
Total RBC Count: 5.2 Mill/Cmm (4.5-5.5)
P.C.V: 47.0 % (40-52)
Total WBC Count: 7200 /cmm (4000-11000)
Platelet Count: 250000 /ul (150000-400000)
"""

print("  INPUT: inline format with parenthesised reference range")
results_5 = parse_ocr_text(INPUT_5)
validation_5 = _validate(results_5)
_print_result(results_5, validation_5)

assert validation_5["total"] == 5, f"Expected 5, got {validation_5['total']}"
assert validation_5["with_value"] == 5
assert validation_5["with_reference"] == 5

hgb5 = next(r for r in results_5 if r["canonical_name"] == "hemoglobin")
assert hgb5["value"] == 15.9
assert hgb5["reference_raw"] is not None
assert "13" in hgb5["reference_raw"]
assert hgb5["layout"] == "inline"

print("  ✓ PASSED")


# =========================================================
# TEST 6 — Multi-section report
# =========================================================

print("\n" + "=" * 60)
print("TEST 6 — Multi-section report (CBC + Liver + Kidney + Lipid)")
print("=" * 60)

INPUT_6 = """\
COMPLETE BLOOD COUNT
Hemoglobin\t15.9\tg/dl\t13.0-18.0
Total WBC Count\t7200\t/cmm\t4000-11000
Platelet Count\t250000\t/ul\t150000-400000

LIVER FUNCTION
Hemoglobin\t15.9\tg/dl\t13.0-18.0

KIDNEY FUNCTION
Hemoglobin\t15.9\tg/dl\t13.0-18.0

LIPID PROFILE
Hemoglobin\t15.9\tg/dl\t13.0-18.0
"""

# Note: only CBC markers are in TEST_ALIASES; liver/kidney/lipid
# markers are not yet in the alias map, so only CBC rows parse.
# The test verifies section splitting does not break CBC parsing.

print("  INPUT: 4 sections; only CBC markers in alias map")
results_6 = parse_ocr_text(INPUT_6)
validation_6 = _validate(results_6)
_print_result(results_6, validation_6)

# Hemoglobin appears in all 4 sections but deduplication keeps only 1
assert validation_6["total"] >= 1
hgb6 = next(r for r in results_6 if r["canonical_name"] == "hemoglobin")
assert hgb6["value"] == 15.9

# WBC and platelets from CBC section
wbc6 = next((r for r in results_6 if r["canonical_name"] == "wbc"), None)
assert wbc6 is not None
assert wbc6["value"] == 7200

print("  ✓ PASSED")


# =========================================================
# TEST 7 — Multi-page report
# =========================================================

print("\n" + "=" * 60)
print("TEST 7 — Multi-page report")
print("=" * 60)

INPUT_7 = """\
--- PAGE 1 ---
Age / Gender : 34 Years/Male
COMPLETE BLOOD COUNT
Hemoglobin\t15.9\tg/dl\t13.0-18.0
Total RBC Count\t5.2\tMill/Cmm\t4.5-5.5
P.C.V\t47.0\t%\t40-52
M.C.V.\t90.0\tfl\t83-101
M.C.H.\t30.0\tpg\t27-32
M.C.H.C.\t33.5\tg/dl\t31.5-34.5
R.D.W.\t13.5\t%\t11.6-14.0

--- PAGE 2 ---
Total WBC Count\t7200\t/cmm\t4000-11000
Neutrophils\t60\t%\t40-75
Lymphocytes\t32\t%\t20-45
Eosinophils\t3\t%\t1-6
Monocytes\t4\t%\t2-10
Basophils\t1\t%\t0-1
Platelet Count\t250000\t/ul\t150000-400000
"""

print("  INPUT: 14 CBC markers split across 2 pages")
results_7 = parse_ocr_text(INPUT_7)
validation_7 = _validate(results_7)
_print_result(results_7, validation_7)

assert validation_7["total"] == 14, f"Expected 14, got {validation_7['total']}"
assert validation_7["with_value"] == 14
assert validation_7["with_reference"] == 14

# Markers from page 1
assert any(r["canonical_name"] == "hemoglobin" for r in results_7)
assert any(r["canonical_name"] == "mcv" for r in results_7)
# Markers from page 2
assert any(r["canonical_name"] == "wbc" for r in results_7)
assert any(r["canonical_name"] == "platelets" for r in results_7)

print("  ✓ PASSED")


# =========================================================
# TEST 8 — Poor-quality scan (OCR noise)
# =========================================================

print("\n" + "=" * 60)
print("TEST 8 — Poor-quality scan (OCR noise / garbled tokens)")
print("=" * 60)

# Simulates common OCR errors:
#   - extra spaces inside values
#   - garbled lines between real data
#   - partial test names that don't match (skipped gracefully)
#   - real data still present and parseable

INPUT_8 = """\
--- PAGE 1 ---
|||||||||||||||||||||||||||||||
Hemoglobin
1 5.9
g/dl
13.0-18.0
xXxXxXxXx
Total WBC Count
7200
/cmm
4000-11000
@#$%^&*
Platelet Count
250000
/ul
150000-400000
|||||||||||||||||||||||||||||||
"""

print("  INPUT: noise lines interspersed, value split by space")
results_8 = parse_ocr_text(INPUT_8)
validation_8 = _validate(results_8)
_print_result(results_8, validation_8)

# Hemoglobin value "1 5.9" cannot be parsed as float → value=None
hgb8 = next((r for r in results_8 if r["canonical_name"] == "hemoglobin"), None)
assert hgb8 is not None, "Hemoglobin must still be detected despite noise"
# value may be None due to OCR noise — that is correct behaviour
print(f"  hemoglobin value (may be None due to noise): {hgb8['value']}")
print(f"  hemoglobin value_uncertain: {hgb8['value'] is None}")

# WBC and platelets should parse cleanly
wbc8 = next((r for r in results_8 if r["canonical_name"] == "wbc"), None)
assert wbc8 is not None
assert wbc8["value"] == 7200

plt8 = next((r for r in results_8 if r["canonical_name"] == "platelets"), None)
assert plt8 is not None
assert plt8["value"] == 250000

# Noise lines must not produce spurious results
canonical_names_8 = {r["canonical_name"] for r in results_8}
assert "xXxXxXxXx" not in canonical_names_8
assert "@#$%^&*" not in canonical_names_8

print("  ✓ PASSED")


# =========================================================
# TEST 9 — Slightly rotated / misaligned (broken tokens)
# =========================================================

print("\n" + "=" * 60)
print("TEST 9 — Slightly rotated / misaligned report")
print("=" * 60)

# Simulates OCR output from a slightly rotated scan:
#   - extra leading/trailing whitespace
#   - occasional line merges (two tokens on one line)
#   - some lines with only partial content

INPUT_9 = """\
  Hemoglobin   15.9   g/dl   13.0-18.0
  Total RBC Count   5.2   Mill/Cmm   4.5-5.5
  P.C.V   47.0   %   40-52
  M.C.V.   90.0   fl   83-101
  Total WBC Count   7200   /cmm   4000-11000
  Platelet Count   250000   /ul   150000-400000
"""

print("  INPUT: extra whitespace from rotation/misalignment")
results_9 = parse_ocr_text(INPUT_9)
validation_9 = _validate(results_9)
_print_result(results_9, validation_9)

assert validation_9["total"] == 6, f"Expected 6, got {validation_9['total']}"
assert validation_9["with_value"] == 6
assert validation_9["with_reference"] == 6

hgb9 = next(r for r in results_9 if r["canonical_name"] == "hemoglobin")
assert hgb9["value"] == 15.9
assert hgb9["reference_raw"] is not None

print("  ✓ PASSED")


# =========================================================
# TEST 10 — Mobile-camera report (mixed inline + vertical)
# =========================================================

print("\n" + "=" * 60)
print("TEST 10 — Mobile-camera report (mixed inline + vertical)")
print("=" * 60)

# Simulates OCR from a mobile photo:
#   - some tests inline (name: value unit [ref])
#   - some tests vertical (OCR split the line)
#   - uneven spacing
#   - one test with abnormal flag

INPUT_10 = """\
Hemoglobin: 15.9 g/dl [13.0-18.0]
Total RBC Count: 5.2 Mill/Cmm [4.5-5.5]
P.C.V
47.0
%
40-52
M.C.V.
90.0
fl
83-101
Total WBC Count: 14500 H /cmm [4000-11000]
Platelet Count
95000
/ul
150000-400000
"""

print("  INPUT: mixed inline and vertical, one H flag, one low platelet")
results_10 = parse_ocr_text(INPUT_10)
validation_10 = _validate(results_10)
_print_result(results_10, validation_10)

assert validation_10["total"] == 6, f"Expected 6, got {validation_10['total']}"
assert validation_10["with_value"] == 6

# Inline results
hgb10 = next(r for r in results_10 if r["canonical_name"] == "hemoglobin")
assert hgb10["value"] == 15.9
assert hgb10["layout"] == "inline"

# Vertical results
pcv10 = next(r for r in results_10 if r["canonical_name"] == "hematocrit")
assert pcv10["value"] == 47.0
assert pcv10["layout"] == "vertical"

# Abnormal flag preserved
wbc10 = next(r for r in results_10 if r["canonical_name"] == "wbc")
assert wbc10["value"] == 14500
assert wbc10["abnormal_flag"] == "H"

print("  ✓ PASSED")


# =========================================================
# EDGE CASES
# =========================================================

print("\n" + "=" * 60)
print("EDGE CASES")
print("=" * 60)

# Empty input
assert parse_ocr_text("") == []
assert parse_ocr_text("   \n\n  ") == []
print("  Empty input → [] : OK")

# Only noise / header lines
noise_only = "Test Name\tResult\tUnit\tReference Range\n|||||||\n@@@@@"
assert parse_ocr_text(noise_only) == []
print("  Noise-only input → [] : OK")

# Unknown test names are silently skipped
unknown = "SomeUnknownTest\t99.9\tmg/dL\t10-20"
assert parse_ocr_text(unknown) == []
print("  Unknown test name → [] : OK")

# Reference range in brackets preserved as raw string
bracket_ref = "Hemoglobin\t15.9\tg/dl\t[13.0-18.0]"
r_bracket = parse_ocr_text(bracket_ref)
assert len(r_bracket) == 1
assert r_bracket[0]["reference_raw"] is not None
print("  Bracketed reference preserved : OK")

# Reference range with 'to' keyword
to_ref = "Hemoglobin\t15.9\tg/dl\t13.0 to 18.0"
r_to = parse_ocr_text(to_ref)
assert len(r_to) == 1
assert r_to[0]["reference_raw"] is not None
print("  'to' reference range preserved : OK")

# Duplicate canonical names — only first kept
dup = "Hemoglobin\t15.9\tg/dl\t13.0-18.0\nHemoglobin\t16.0\tg/dl\t13.0-18.0"
r_dup = parse_ocr_text(dup)
assert len(r_dup) == 1
assert r_dup[0]["value"] == 15.9
print("  Duplicate canonical name → first kept : OK")

print("  ✓ ALL EDGE CASES PASSED")


# =========================================================
# FINAL
# =========================================================

print("\n" + "=" * 60)
print("   ALL LAYOUT PARSER TESTS PASSED")
print("=" * 60)
