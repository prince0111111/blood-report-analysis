"""
Plausibility checking for extracted CBC values.

PURPOSE
-------
Detect values that are so unusual that an extraction/parsing
error should be considered.

IMPORTANT
---------
This module does NOT:

- diagnose disease
- determine normal/high/low
- replace laboratory reference ranges
- automatically correct values
- reject unusual results as medically impossible

A flagged value means:

    "Verify this value against the original report."

It does NOT mean:

    "This value is definitely wrong."
"""


# =========================================================
# EXTRACTION SANITY BOUNDS
# =========================================================
#
# These are intentionally BROAD.
#
# They are NOT clinical reference ranges.
#
# They exist only to catch obvious extraction problems such
# as:
#
#     Hemoglobin = 1590 g/dL
#     Hematocrit = 490 %
#     Neutrophils = 710 %
#
# Borderline or clinically abnormal results should NOT be
# flagged here merely for being outside the lab range.
# =========================================================

PLAUSIBILITY_BOUNDS = {

    "hemoglobin": {
        "min": 1.0,
        "max": 30.0
    },

    "rbc": {
        "min": 0.1,
        "max": 15.0
    },

    "hematocrit": {
        "min": 1.0,
        "max": 80.0
    },

    "mcv": {
        "min": 30.0,
        "max": 160.0
    },

    "mch": {
        "min": 5.0,
        "max": 60.0
    },

    "mchc": {
        "min": 10.0,
        "max": 60.0
    },

    "rdw": {
        "min": 5.0,
        "max": 50.0
    },

    "wbc": {
        "min": 100.0,
        "max": 500000.0
    },

    "neutrophils": {
        "min": 0.0,
        "max": 100.0
    },

    "lymphocytes": {
        "min": 0.0,
        "max": 100.0
    },

    "eosinophils": {
        "min": 0.0,
        "max": 100.0
    },

    "monocytes": {
        "min": 0.0,
        "max": 100.0
    },

    "basophils": {
        "min": 0.0,
        "max": 100.0
    },

    "platelets": {
        "min": 1000.0,
        "max": 3000000.0
    }
}


# =========================================================
# SINGLE TEST
# =========================================================

def check_test_plausibility(test: dict) -> dict:
    """
    Check one structurally valid CBC result.

    Returns:

        {
            "status": "PLAUSIBLE"
        }

    or:

        {
            "status": "VERIFY",
            "reason": "...",
            ...
        }
    """

    canonical_name = test.get(
        "canonical_name"
    )

    value = test.get(
        "value"
    )

    # -----------------------------------------------------
    # No rule available
    # -----------------------------------------------------

    bounds = PLAUSIBILITY_BOUNDS.get(
        canonical_name
    )

    if bounds is None:

        return {
            "status": "NOT_CHECKED",
            "test": canonical_name,
            "value": value,
            "reason": (
                "No plausibility rule is currently "
                "configured for this test."
            )
        }

    # -----------------------------------------------------
    # Value should already have passed Level 2.
    # Defensive check anyway.
    # -----------------------------------------------------

    if not isinstance(
        value,
        (int, float)
    ) or isinstance(value, bool):

        return {
            "status": "VERIFY",
            "test": canonical_name,
            "value": value,
            "reason": (
                "The extracted result is not numeric."
            )
        }

    minimum = bounds["min"]
    maximum = bounds["max"]

    # -----------------------------------------------------
    # Suspiciously low
    # -----------------------------------------------------

    if value < minimum:

        return {
            "status": "VERIFY",
            "test": canonical_name,
            "value": value,
            "expected_extraction_min": minimum,
            "expected_extraction_max": maximum,
            "reason": (
                "The extracted value is outside the "
                "configured extraction sanity bounds. "
                "Verify it against the original report."
            )
        }

    # -----------------------------------------------------
    # Suspiciously high
    # -----------------------------------------------------

    if value > maximum:

        return {
            "status": "VERIFY",
            "test": canonical_name,
            "value": value,
            "expected_extraction_min": minimum,
            "expected_extraction_max": maximum,
            "reason": (
                "The extracted value is outside the "
                "configured extraction sanity bounds. "
                "Verify it against the original report."
            )
        }

    return {
        "status": "PLAUSIBLE",
        "test": canonical_name,
        "value": value
    }


# =========================================================
# COMPLETE REPORT
# =========================================================

def check_report_plausibility(
    tests: list
) -> dict:
    """
    Run plausibility checks over structurally valid tests.
    """

    results = []
    verification_required = []

    for test in tests:

        result = check_test_plausibility(
            test
        )

        results.append(
            result
        )

        if result["status"] == "VERIFY":

            verification_required.append(
                result
            )

    return {
        "checked_tests": len(tests),
        "verification_required_count": len(
            verification_required
        ),
        "requires_verification": (
            len(verification_required) > 0
        ),
        "verification_required": (
            verification_required
        ),
        "results": results
    }