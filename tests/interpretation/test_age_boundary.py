from interpretation.age_boundary import (
    compare_age_points,
    convert_exact_age,
    match_age_band,
    validate_age_band,
)


def age(value, unit):
    return {
        "value": value,
        "unit": unit,
    }


def show_result(name, result):
    print("\n========================================")
    print(name)
    print("========================================")
    print(result)


# =========================================================
# TEST 1
# Same-unit days
# =========================================================

result = compare_age_points(
    age(15, "days"),
    age(20, "days"),
)

show_result(
    "TEST 1 — DAYS COMPARISON",
    result,
)

assert result == -1

print("✓ PASSED")


# =========================================================
# TEST 2
# Weeks -> days exact conversion
# =========================================================

result = convert_exact_age(
    age(4, "weeks"),
    "days",
)

show_result(
    "TEST 2 — WEEKS TO DAYS",
    result,
)

assert result is not None
assert result["value"] == 28
assert result["unit"] == "days"

print("✓ PASSED")


# =========================================================
# TEST 3
# Exact days -> weeks
# =========================================================

result = convert_exact_age(
    age(28, "days"),
    "weeks",
)

show_result(
    "TEST 3 — DAYS TO WEEKS",
    result,
)

assert result is not None
assert result["value"] == 4
assert result["unit"] == "weeks"

print("✓ PASSED")


# =========================================================
# TEST 4
# Non-whole weeks are deliberately not converted
# =========================================================

result = convert_exact_age(
    age(20, "days"),
    "weeks",
)

show_result(
    "TEST 4 — NON-WHOLE WEEK CONVERSION",
    result,
)

assert result is None

print("✓ PASSED")


# =========================================================
# TEST 5
# Compare days against weeks
#
# 20 days < 4 weeks (28 days)
# =========================================================

result = compare_age_points(
    age(20, "days"),
    age(4, "weeks"),
)

show_result(
    "TEST 5 — DAYS VS WEEKS",
    result,
)

assert result == -1

print("✓ PASSED")


# =========================================================
# TEST 6
# Equality across exact units
#
# 28 days == 4 weeks
# =========================================================

result = compare_age_points(
    age(28, "days"),
    age(4, "weeks"),
)

show_result(
    "TEST 6 — EXACT CROSS-UNIT EQUALITY",
    result,
)

assert result == 0

print("✓ PASSED")


# =========================================================
# TEST 7
# Mayo-style mixed boundary:
#
# 15 days -> 4 weeks
# =========================================================

result = validate_age_band(
    age(15, "days"),
    age(4, "weeks"),
)

show_result(
    "TEST 7 — MIXED DAY/WEEK BAND",
    result,
)

assert result["valid"] is True

print("✓ PASSED")


# =========================================================
# TEST 8
# Patient 20 days should match:
#
# 15 days -> 4 weeks
# =========================================================

result = match_age_band(
    patient_age=age(20, "days"),
    min_age=age(15, "days"),
    max_age=age(4, "weeks"),
)

show_result(
    "TEST 8 — 20 DAYS IN 15 DAYS TO 4 WEEKS",
    result,
)

assert result["status"] == "MATCH"
assert result["matches"] is True

print("✓ PASSED")


# =========================================================
# TEST 9
# Patient before lower boundary
# =========================================================

result = match_age_band(
    patient_age=age(14, "days"),
    min_age=age(15, "days"),
    max_age=age(4, "weeks"),
)

show_result(
    "TEST 9 — BEFORE LOWER BOUNDARY",
    result,
)

assert result["status"] == "NO_MATCH"
assert result["matches"] is False

print("✓ PASSED")


# =========================================================
# TEST 10
# Patient exactly at upper boundary
# =========================================================

result = match_age_band(
    patient_age=age(28, "days"),
    min_age=age(15, "days"),
    max_age=age(4, "weeks"),
)

show_result(
    "TEST 10 — EXACT UPPER BOUNDARY",
    result,
)

assert result["status"] == "MATCH"
assert result["matches"] is True

print("✓ PASSED")


# =========================================================
# TEST 11
# Patient after upper boundary
# =========================================================

result = match_age_band(
    patient_age=age(29, "days"),
    min_age=age(15, "days"),
    max_age=age(4, "weeks"),
)

show_result(
    "TEST 11 — AFTER UPPER BOUNDARY",
    result,
)

assert result["status"] == "NO_MATCH"

print("✓ PASSED")


# =========================================================
# TEST 12
# Same-unit months
# =========================================================

result = match_age_band(
    patient_age=age(6, "months"),
    min_age=age(6, "months"),
    max_age=age(23, "months"),
)

show_result(
    "TEST 12 — MONTH RANGE",
    result,
)

assert result["status"] == "MATCH"

print("✓ PASSED")


# =========================================================
# TEST 13
# Same-unit years
# =========================================================

result = match_age_band(
    patient_age=age(4, "years"),
    min_age=age(3, "years"),
    max_age=age(5, "years"),
)

show_result(
    "TEST 13 — YEAR RANGE",
    result,
)

assert result["status"] == "MATCH"

print("✓ PASSED")


# =========================================================
# TEST 14
# Unsafe months -> weeks comparison
#
# We DO NOT assume:
#
#     1 month = 4 weeks
# =========================================================

result = compare_age_points(
    age(1, "months"),
    age(4, "weeks"),
)

show_result(
    "TEST 14 — MONTHS VS WEEKS REFUSED",
    result,
)

assert result is None

print("✓ PASSED")
print("✓ No approximate month/week conversion")


# =========================================================
# TEST 15
# Unsafe months -> years
# =========================================================

result = compare_age_points(
    age(6, "months"),
    age(1, "years"),
)

show_result(
    "TEST 15 — MONTHS VS YEARS REFUSED",
    result,
)

assert result is None

print("✓ PASSED")


# =========================================================
# TEST 16
# Patient months vs mixed week/month band.
#
# Example:
#
#     8 weeks -> 5 months
#
# Patient:
#
#     3 months
#
# Upper comparison is safe because both are months.
# Lower comparison is NOT exact because patient months
# cannot be converted to weeks.
#
# Therefore the result must be UNRESOLVED rather than
# guessing.
# =========================================================

result = match_age_band(
    patient_age=age(3, "months"),
    min_age=age(8, "weeks"),
    max_age=age(5, "months"),
)

show_result(
    "TEST 16 — MIXED WEEK/MONTH BAND",
    result,
)

assert result["status"] == "UNRESOLVED"
assert result["matches"] is False

print("✓ PASSED")
print("✓ Unsafe calendar conversion refused")


# =========================================================
# TEST 17
# Invalid reversed day/week band
#
# 5 weeks -> 20 days
#
# 35 days -> 20 days = invalid
# =========================================================

result = validate_age_band(
    age(5, "weeks"),
    age(20, "days"),
)

show_result(
    "TEST 17 — REVERSED MIXED BAND",
    result,
)

assert result["valid"] is False

print("✓ PASSED")


# =========================================================
# TEST 18
# Missing patient age
# =========================================================

result = match_age_band(
    patient_age=None,
    min_age=age(15, "days"),
    max_age=age(4, "weeks"),
)

show_result(
    "TEST 18 — MISSING PATIENT AGE",
    result,
)

assert result["status"] == "UNRESOLVED"

print("✓ PASSED")


# =========================================================
# TEST 19
# Negative age must be rejected
# =========================================================

result = match_age_band(
    patient_age=age(-1, "days"),
    min_age=age(0, "days"),
    max_age=age(14, "days"),
)

show_result(
    "TEST 19 — NEGATIVE AGE",
    result,
)

assert result["status"] == "UNRESOLVED"

print("✓ PASSED")


# =========================================================
# TEST 20
# Zero-day newborn
# =========================================================

result = match_age_band(
    patient_age=age(0, "days"),
    min_age=age(0, "days"),
    max_age=age(14, "days"),
)

show_result(
    "TEST 20 — ZERO-DAY NEWBORN",
    result,
)

assert result["status"] == "MATCH"

print("✓ PASSED")


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print("    ALL AGE BOUNDARY TESTS PASSED")
print("========================================")