from interpretation.reference_resolver import (
    resolve_reference_range
)


# =========================================================
# DISPLAY
# =========================================================

def show_result(
    name,
    result
):

    print("\n========================================")
    print(name)
    print("========================================")

    print(
        "Resolved:",
        result["resolved"]
    )

    print(
        "Min:",
        result["min"]
    )

    print(
        "Max:",
        result["max"]
    )

    print(
        "Matched by:",
        result["matched_by"]
    )

    print(
        "Matched age:",
        result["matched_age"]
    )

    print(
        "Matched age value:",
        result["matched_age_value"]
    )

    print(
        "Matched age unit:",
        result["matched_age_unit"]
    )

    print(
        "Matched sex:",
        result["matched_sex"]
    )

    if result["reason"]:

        print(
            "Reason:",
            result["reason"]
        )


# =========================================================
# TEST 1 — OLD DIRECT RANGE
# =========================================================

result = resolve_reference_range(
    "[13.0-18.0]",
    {
        "age": 34,
        "sex": "male"
    }
)

show_result(
    "TEST 1 — LEGACY DIRECT RANGE",
    result
)

assert result["resolved"] is True
assert result["min"] == 13.0
assert result["max"] == 18.0
assert result["matched_by"] == "report_direct"

assert result["matched_age"] == 34
assert result["matched_age_value"] == 34
assert result["matched_age_unit"] == "years"

print("✓ PASSED")


# =========================================================
# TEST 2 — NEW ADULT REPRESENTATION
# =========================================================

result = resolve_reference_range(
    "[13.0-18.0]",
    {
        "age": 34,
        "age_value": 34,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 2 — NEW ADULT REPRESENTATION",
    result
)

assert result["resolved"] is True
assert result["min"] == 13.0
assert result["max"] == 18.0

assert result["matched_age"] == 34
assert result["matched_age_value"] == 34
assert result["matched_age_unit"] == "years"

print("✓ PASSED")


# =========================================================
# TEST 3 — SEX SPECIFIC MALE
# =========================================================

reference = """
Male: 13.0 - 17.0
Female: 12.0 - 15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 3 — SEX SPECIFIC MALE",
    result
)

assert result["resolved"] is True
assert result["min"] == 13.0
assert result["max"] == 17.0
assert result["matched_by"] == "sex"
assert result["matched_sex"] == "male"

print("✓ PASSED")


# =========================================================
# TEST 4 — SEX SPECIFIC FEMALE
# =========================================================

result = resolve_reference_range(
    reference,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": "female"
    }
)

show_result(
    "TEST 4 — SEX SPECIFIC FEMALE",
    result
)

assert result["resolved"] is True
assert result["min"] == 12.0
assert result["max"] == 15.0
assert result["matched_by"] == "sex"
assert result["matched_sex"] == "female"

print("✓ PASSED")


# =========================================================
# TEST 5 — AGE + SEX YEARS
# =========================================================

reference = """
Male:
18-60 years: 13.0-17.0
61-120 years: 12.0-16.0

Female:
18-60 years: 12.0-15.0
61-120 years: 11.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 5 — AGE + SEX YEARS",
    result
)

assert result["resolved"] is True
assert result["min"] == 13.0
assert result["max"] == 17.0
assert result["matched_by"] == "age_and_sex"

assert result["matched_age_value"] == 34
assert result["matched_age_unit"] == "years"

print("✓ PASSED")


# =========================================================
# TEST 6 — OLDER FEMALE
# =========================================================

result = resolve_reference_range(
    reference,
    {
        "age_value": 72,
        "age_unit": "years",
        "sex": "female"
    }
)

show_result(
    "TEST 6 — OLDER FEMALE",
    result
)

assert result["resolved"] is True
assert result["min"] == 11.0
assert result["max"] == 15.0
assert result["matched_by"] == "age_and_sex"

print("✓ PASSED")


# =========================================================
# TEST 7 — AGE ONLY YEARS
# =========================================================

reference = """
1-5 years: 11.0-14.0
6-12 years: 12.0-15.0
13-17 years: 12.0-16.0
18-120 years: 13.0-17.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 10,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 7 — AGE ONLY YEARS",
    result
)

assert result["resolved"] is True
assert result["min"] == 12.0
assert result["max"] == 15.0
assert result["matched_by"] == "age"

print("✓ PASSED")


# =========================================================
# TEST 8 — NEWBORN DAYS
# =========================================================

reference = """
0-7 days: 14.0-22.0
8-30 days: 12.0-20.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 15,
        "age_unit": "days",
        "sex": "male"
    }
)

show_result(
    "TEST 8 — NEWBORN DAYS",
    result
)

assert result["resolved"] is True
assert result["min"] == 12.0
assert result["max"] == 20.0
assert result["matched_by"] == "age"

assert result["matched_age_value"] == 15
assert result["matched_age_unit"] == "days"

print("✓ PASSED")


# =========================================================
# TEST 9 — ZERO-DAY NEWBORN
# =========================================================

reference = """
0-7 days: 14.0-22.0
8-30 days: 12.0-20.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 0,
        "age_unit": "days",
        "sex": "female"
    }
)

show_result(
    "TEST 9 — ZERO-DAY NEWBORN",
    result
)

assert result["resolved"] is True
assert result["min"] == 14.0
assert result["max"] == 22.0

assert result["matched_age_value"] == 0
assert result["matched_age_unit"] == "days"

print("✓ PASSED")


# =========================================================
# TEST 10 — INFANT MONTHS
# =========================================================

reference = """
1-6 months: 10.0-14.0
7-12 months: 11.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 6,
        "age_unit": "months",
        "sex": "female"
    }
)

show_result(
    "TEST 10 — INFANT MONTHS",
    result
)

assert result["resolved"] is True
assert result["min"] == 10.0
assert result["max"] == 14.0

assert result["matched_age_value"] == 6
assert result["matched_age_unit"] == "months"

print("✓ PASSED")


# =========================================================
# TEST 11 — MONTH BOUNDARY
# =========================================================

reference = """
1-6 months: 10.0-14.0
7-12 months: 11.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 7,
        "age_unit": "months",
        "sex": "male"
    }
)

show_result(
    "TEST 11 — MONTH BOUNDARY",
    result
)

assert result["resolved"] is True
assert result["min"] == 11.0
assert result["max"] == 15.0

print("✓ PASSED")


# =========================================================
# TEST 12 — WEEKS
# =========================================================

reference = """
0-1 weeks: 15.0-22.0
2-4 weeks: 12.0-20.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 3,
        "age_unit": "weeks",
        "sex": "male"
    }
)

show_result(
    "TEST 12 — WEEKS",
    result
)

assert result["resolved"] is True
assert result["min"] == 12.0
assert result["max"] == 20.0

assert result["matched_age_unit"] == "weeks"

print("✓ PASSED")


# =========================================================
# TEST 13 — PEDIATRIC AGE + SEX
# =========================================================

reference = """
Male:
1-6 months: 10.0-14.0
7-12 months: 11.0-15.0
1-5 years: 11.5-15.5

Female:
1-6 months: 9.5-13.5
7-12 months: 10.5-14.5
1-5 years: 11.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 6,
        "age_unit": "months",
        "sex": "female"
    }
)

show_result(
    "TEST 13 — PEDIATRIC AGE + SEX",
    result
)

assert result["resolved"] is True

assert result["min"] == 9.5
assert result["max"] == 13.5

assert result["matched_by"] == "age_and_sex"

assert result["matched_age_value"] == 6
assert result["matched_age_unit"] == "months"

assert result["matched_sex"] == "female"

print("✓ PASSED")


# =========================================================
# TEST 14 — MISSING SEX
# =========================================================

reference = """
Male: 13.0-17.0
Female: 12.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": None
    }
)

show_result(
    "TEST 14 — MISSING SEX",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 15 — MISSING AGE
# =========================================================

reference = """
1-5 years: 11.0-14.0
6-12 years: 12.0-15.0
18-120 years: 13.0-17.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": None,
        "age_unit": None,
        "sex": "male"
    }
)

show_result(
    "TEST 15 — MISSING AGE",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 16 — AGE NOT COVERED
# =========================================================

reference = """
1-5 years: 11.0-14.0
6-12 years: 12.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 16 — AGE NOT COVERED",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 17 — AMBIGUOUS AGE BANDS
# =========================================================

reference = """
10-20 years: 11.0-14.0
15-25 years: 12.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 18,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 17 — AMBIGUOUS AGE BANDS",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 18 — UNSAFE CROSS-UNIT MATCH
# =========================================================
#
# Patient is 6 months old.
#
# The report only provides a YEARS range.
#
# We deliberately DO NOT decide that:
#
#     6 months = 0.5 years
#
# because our current resolver requires exact age units.
#
# =========================================================

reference = """
0-1 years: 10.0-14.0
2-5 years: 11.0-15.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 6,
        "age_unit": "months",
        "sex": "female"
    }
)

show_result(
    "TEST 18 — CROSS-UNIT REFUSED",
    result
)

assert result["resolved"] is False

assert (
    "cross-unit"
    in result["reason"].lower()
)

print("✓ PASSED")

print(
    "✓ Unsafe months-to-years conversion was refused"
)


# =========================================================
# TEST 19 — MONTHS DO NOT MATCH DAYS
# =========================================================

reference = """
0-30 days: 12.0-20.0
"""

result = resolve_reference_range(
    reference,
    {
        "age_value": 1,
        "age_unit": "months",
        "sex": "male"
    }
)

show_result(
    "TEST 19 — MONTHS VS DAYS REFUSED",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 20 — MISSING REFERENCE
# =========================================================

result = resolve_reference_range(
    None,
    {
        "age_value": 34,
        "age_unit": "years",
        "sex": "male"
    }
)

show_result(
    "TEST 20 — MISSING REFERENCE",
    result
)

assert result["resolved"] is False

print("✓ PASSED")


# =========================================================
# TEST 21 — DIRECT RANGE FOR INFANT
# =========================================================
#
# A direct range does not require age selection because
# the laboratory has provided only one applicable interval.
#
# We still preserve the patient's precise age.
#
# =========================================================

result = resolve_reference_range(
    "[10.0-15.0]",
    {
        "age_value": 6,
        "age_unit": "months",
        "sex": "female"
    }
)

show_result(
    "TEST 21 — DIRECT INFANT RANGE",
    result
)

assert result["resolved"] is True

assert result["min"] == 10.0
assert result["max"] == 15.0

assert result["matched_by"] == "report_direct"

assert result["matched_age"] is None
assert result["matched_age_value"] == 6
assert result["matched_age_unit"] == "months"

print("✓ PASSED")


# =========================================================
# FINAL
# =========================================================

print("\n========================================")
print(" ALL REFERENCE RESOLVER V2 TESTS PASSED")
print("========================================")