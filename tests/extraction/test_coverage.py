from extraction.coverage import check_cbc_coverage


# =========================================================
# HELPER
# =========================================================

def make_test(canonical_name):
    """
    Create minimal test data required by the coverage
    checker.

    Coverage only cares about canonical_name.
    """

    return {
        "canonical_name": canonical_name
    }


# =========================================================
# COMPLETE 14-MARKER CBC
# =========================================================

complete_cbc = [

    make_test("hemoglobin"),
    make_test("rbc"),
    make_test("hematocrit"),
    make_test("mcv"),
    make_test("mch"),
    make_test("mchc"),
    make_test("rdw"),
    make_test("wbc"),
    make_test("neutrophils"),
    make_test("lymphocytes"),
    make_test("eosinophils"),
    make_test("monocytes"),
    make_test("basophils"),
    make_test("platelets"),

]


# =========================================================
# TEST 1
# COMPLETE CBC
# =========================================================

print("\n========================================")
print("TEST 1 — COMPLETE CBC")
print("========================================")

result = check_cbc_coverage(
    complete_cbc
)

print(
    "Status:",
    result["status"]
)

print(
    "Expected:",
    result["expected_count"]
)

print(
    "Detected:",
    result["detected_count"]
)

print(
    "Missing:",
    result["missing_count"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

assert result["status"] == "COMPLETE"

assert result["expected_count"] == 14

assert result["detected_count"] == 14

assert result["missing_count"] == 0

assert result["coverage_percent"] == 100.0

assert result["missing_markers"] == []

assert result["duplicate_markers"] == []

print("✓ PASSED")


# =========================================================
# TEST 2
# TWO MARKERS MISSING
# =========================================================

print("\n========================================")
print("TEST 2 — TWO MARKERS MISSING")
print("========================================")

incomplete_cbc = [

    test
    for test in complete_cbc

    if test["canonical_name"]
    not in {
        "wbc",
        "mch"
    }
]

result = check_cbc_coverage(
    incomplete_cbc
)

print(
    "Status:",
    result["status"]
)

print(
    "Expected:",
    result["expected_count"]
)

print(
    "Detected:",
    result["detected_count"]
)

print(
    "Missing:",
    result["missing_count"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

print(
    "Missing markers:",
    result["missing_markers"]
)

assert result["status"] == "INCOMPLETE"

assert result["expected_count"] == 14

assert result["detected_count"] == 12

assert result["missing_count"] == 2

assert result["coverage_percent"] == 85.71

assert set(
    result["missing_markers"]
) == {
    "wbc",
    "mch"
}

print("✓ PASSED")
print("✓ Exact missing markers identified")


# =========================================================
# TEST 3
# NOTHING EXTRACTED
# =========================================================

print("\n========================================")
print("TEST 3 — NO CBC MARKERS")
print("========================================")

result = check_cbc_coverage(
    []
)

print(
    "Status:",
    result["status"]
)

print(
    "Expected:",
    result["expected_count"]
)

print(
    "Detected:",
    result["detected_count"]
)

print(
    "Missing:",
    result["missing_count"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

assert result["status"] == "NO_COVERAGE"

assert result["expected_count"] == 14

assert result["detected_count"] == 0

assert result["missing_count"] == 14

assert result["coverage_percent"] == 0.0

print("✓ PASSED")


# =========================================================
# TEST 4
# DUPLICATE MARKER
# =========================================================

print("\n========================================")
print("TEST 4 — DUPLICATE MARKER")
print("========================================")

duplicate_cbc = (
    complete_cbc
    + [
        make_test(
            "hemoglobin"
        )
    ]
)

result = check_cbc_coverage(
    duplicate_cbc
)

print(
    "Status:",
    result["status"]
)

print(
    "Detected unique:",
    result["detected_count"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

print(
    "Duplicates:",
    result["duplicate_markers"]
)

assert result["status"] == "COMPLETE"

# Very important:
# 15 extracted rows must still equal only
# 14 UNIQUE supported markers.

assert result["detected_count"] == 14

assert result["coverage_percent"] == 100.0

assert result["duplicate_markers"] == [
    "hemoglobin"
]

print("✓ PASSED")

print(
    "✓ Duplicate did not inflate coverage"
)


# =========================================================
# TEST 5
# UNKNOWN MARKER
# =========================================================

print("\n========================================")
print("TEST 5 — UNKNOWN MARKER")
print("========================================")

unknown_cbc = (
    complete_cbc
    + [
        make_test(
            "some_unknown_test"
        )
    ]
)

result = check_cbc_coverage(
    unknown_cbc
)

print(
    "Status:",
    result["status"]
)

print(
    "Detected supported:",
    result["detected_count"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

print(
    "Unknown:",
    result["unknown_markers"]
)

assert result["status"] == "COMPLETE"

assert result["detected_count"] == 14

assert result["coverage_percent"] == 100.0

assert result["unknown_markers"] == [
    "some_unknown_test"
]

print("✓ PASSED")

print(
    "✓ Unknown marker did not inflate coverage"
)


# =========================================================
# TEST 6
# DUPLICATE + MISSING
# =========================================================

print("\n========================================")
print("TEST 6 — DUPLICATE + MISSING")
print("========================================")

duplicate_and_missing = [

    test
    for test in complete_cbc

    if test["canonical_name"]
    not in {
        "wbc",
        "platelets"
    }
]

duplicate_and_missing.append(
    make_test(
        "hemoglobin"
    )
)

result = check_cbc_coverage(
    duplicate_and_missing
)

print(
    "Status:",
    result["status"]
)

print(
    "Detected unique:",
    result["detected_count"]
)

print(
    "Missing:",
    result["missing_markers"]
)

print(
    "Duplicates:",
    result["duplicate_markers"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

assert result["status"] == "INCOMPLETE"

assert result["detected_count"] == 12

assert result["missing_count"] == 2

assert set(
    result["missing_markers"]
) == {
    "wbc",
    "platelets"
}

assert result["duplicate_markers"] == [
    "hemoglobin"
]

assert result["coverage_percent"] == 85.71

print("✓ PASSED")

print(
    "✓ Missing and duplicate conditions "
    "detected independently"
)


# =========================================================
# TEST 7
# UNKNOWN MARKER ONLY
# =========================================================

print("\n========================================")
print("TEST 7 — UNKNOWN MARKER ONLY")
print("========================================")

unknown_only = [

    make_test(
        "random_lab_test"
    )

]

result = check_cbc_coverage(
    unknown_only
)

print(
    "Status:",
    result["status"]
)

print(
    "Detected supported:",
    result["detected_count"]
)

print(
    "Unknown:",
    result["unknown_markers"]
)

print(
    "Coverage:",
    result["coverage_percent"]
)

assert result["status"] == "NO_COVERAGE"

assert result["detected_count"] == 0

assert result["coverage_percent"] == 0.0

assert result["unknown_markers"] == [
    "random_lab_test"
]

print("✓ PASSED")

print(
    "✓ Unknown test was not treated "
    "as CBC coverage"
)


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("       ALL COVERAGE TESTS PASSED")
print("========================================")