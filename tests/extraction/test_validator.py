import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from extraction.validator import validate_tests


# TEST 1 — Perfect test
perfect = [
    {
        "raw_name": "Hemoglobin",
        "canonical_name": "hemoglobin",
        "value": 15.9,
        "unit": "g/dl",
        "reference_raw": "[13.0-18.0]"
    }
]


# TEST 2 — Missing unit
missing_unit = [
    {
        "raw_name": "Hemoglobin",
        "canonical_name": "hemoglobin",
        "value": 15.9,
        "unit": None,
        "reference_raw": "[13.0-18.0]"
    }
]


# TEST 3 — Missing reference range
missing_reference = [
    {
        "raw_name": "Hemoglobin",
        "canonical_name": "hemoglobin",
        "value": 15.9,
        "unit": "g/dl",
        "reference_raw": None
    }
]


# TEST 4 — Missing value
missing_value = [
    {
        "raw_name": "Hemoglobin",
        "canonical_name": "hemoglobin",
        "value": None,
        "unit": "g/dl",
        "reference_raw": "[13.0-18.0]"
    }
]


# TEST 5 — Nothing extracted
nothing = []


cases = {
    "PERFECT": perfect,
    "MISSING UNIT": missing_unit,
    "MISSING REFERENCE": missing_reference,
    "MISSING VALUE": missing_value,
    "NOTHING EXTRACTED": nothing
}


for name, data in cases.items():

    print(f"\n========== {name} ==========")

    result = validate_tests(data)

    print("Status:", result["status"])
    print("Issues:", result["issues"])