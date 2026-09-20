from extraction.plausibility import (
    check_test_plausibility,
    check_report_plausibility
)


# =========================================================
# TEST DATA
# =========================================================

normal_hemoglobin = {
    "raw_name": "Hemoglobin",
    "canonical_name": "hemoglobin",
    "value": 15.9,
    "unit": "g/dl",
    "reference_raw": "[13.0-18.0]"
}


corrupted_hemoglobin = {
    "raw_name": "Hemoglobin",
    "canonical_name": "hemoglobin",
    "value": 1590.0,
    "unit": "g/dl",
    "reference_raw": "[13.0-18.0]"
}


corrupted_neutrophils = {
    "raw_name": "Neutrophils",
    "canonical_name": "neutrophils",
    "value": 710.0,
    "unit": "%",
    "reference_raw": "[60-70]"
}


corrupted_platelets = {
    "raw_name": "Platelet Count",
    "canonical_name": "platelets",
    "value": 16700000.0,
    "unit": "/ul",
    "reference_raw": "[150000-450000]"
}


normal_platelets = {
    "raw_name": "Platelet Count",
    "canonical_name": "platelets",
    "value": 167000.0,
    "unit": "/ul",
    "reference_raw": "[150000-450000]"
}


# =========================================================
# TEST 1
# Normal hemoglobin
# =========================================================

print("\n========================================")
print("TEST 1 — NORMAL HEMOGLOBIN")
print("========================================")

result = check_test_plausibility(
    normal_hemoglobin
)

print(result)

assert result["status"] == "PLAUSIBLE"

print("✓ PASSED")


# =========================================================
# TEST 2
# Corrupted hemoglobin
# =========================================================

print("\n========================================")
print("TEST 2 — CORRUPTED HEMOGLOBIN")
print("========================================")

result = check_test_plausibility(
    corrupted_hemoglobin
)

print(result)

assert result["status"] == "VERIFY"

# Make sure the system did NOT alter the value.
assert result["value"] == 1590.0

print("✓ PASSED")
print("✓ Original suspicious value preserved")


# =========================================================
# TEST 3
# Corrupted neutrophils
# =========================================================

print("\n========================================")
print("TEST 3 — CORRUPTED NEUTROPHILS")
print("========================================")

result = check_test_plausibility(
    corrupted_neutrophils
)

print(result)

assert result["status"] == "VERIFY"
assert result["value"] == 710.0

print("✓ PASSED")
print("✓ Original suspicious value preserved")


# =========================================================
# TEST 4
# Corrupted platelets
# =========================================================

print("\n========================================")
print("TEST 4 — CORRUPTED PLATELETS")
print("========================================")

result = check_test_plausibility(
    corrupted_platelets
)

print(result)

assert result["status"] == "VERIFY"
assert result["value"] == 16700000.0

print("✓ PASSED")
print("✓ Original suspicious value preserved")


# =========================================================
# TEST 5
# Normal platelets
# =========================================================

print("\n========================================")
print("TEST 5 — NORMAL PLATELETS")
print("========================================")

result = check_test_plausibility(
    normal_platelets
)

print(result)

assert result["status"] == "PLAUSIBLE"

print("✓ PASSED")


# =========================================================
# TEST 6
# Complete report containing good + suspicious values
# =========================================================

print("\n========================================")
print("TEST 6 — MIXED REPORT")
print("========================================")

mixed_report = [
    normal_hemoglobin,
    normal_platelets,
    corrupted_neutrophils
]

report_result = check_report_plausibility(
    mixed_report
)

print(
    "Tests checked:",
    report_result["checked_tests"]
)

print(
    "Verification required:",
    report_result["verification_required_count"]
)

print(
    "Requires verification:",
    report_result["requires_verification"]
)

print("\nFlagged tests:")

for item in report_result["verification_required"]:

    print(
        "-",
        item["test"],
        "=",
        item["value"]
    )


assert report_result["checked_tests"] == 3

assert (
    report_result["verification_required_count"]
    == 1
)

assert (
    report_result["requires_verification"]
    is True
)

assert (
    report_result["verification_required"][0]["test"]
    == "neutrophils"
)

assert (
    report_result["verification_required"][0]["value"]
    == 710.0
)

print("✓ PASSED")


# =========================================================
# FINAL RESULT
# =========================================================

print("\n========================================")
print("       ALL PLAUSIBILITY TESTS PASSED")
print("========================================")