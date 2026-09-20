"""
CBC extraction coverage checking.

PURPOSE
-------
This module answers:

    "How many of the CBC markers that our CURRENT parser
    is designed to extract were actually extracted?"

This is NOT medical interpretation.

It does NOT:
- diagnose anything
- determine whether a CBC is medically sufficient
- decide whether a missing test should have been ordered
- assume every laboratory in the future must contain
  exactly these markers

For the current development scope, our parser supports
14 CBC markers from the first report.
"""


# =========================================================
# CURRENT CBC PROFILE
# =========================================================
#
# These names must correspond to the canonical names
# produced by parser.py.
#
# IMPORTANT:
# This is our CURRENT parser coverage profile.
# It is not a universal definition of every CBC panel.
# =========================================================

SUPPORTED_CBC_MARKERS = {
    "hemoglobin",
    "rbc",
    "hematocrit",
    "mcv",
    "mch",
    "mchc",
    "rdw",
    "wbc",
    "neutrophils",
    "lymphocytes",
    "eosinophils",
    "monocytes",
    "basophils",
    "platelets"
}


# =========================================================
# COVERAGE CHECK
# =========================================================

def check_cbc_coverage(tests: list) -> dict:
    """
    Compare extracted CBC markers against the CBC markers
    currently supported by our parser.

    Returns information about:

    - expected markers
    - detected markers
    - missing markers
    - duplicate markers
    - unknown markers
    - coverage percentage
    """

    detected_markers = []
    unknown_markers = []

    # -----------------------------------------------------
    # Collect canonical names
    # -----------------------------------------------------

    for test in tests:

        canonical_name = test.get(
            "canonical_name"
        )

        if not canonical_name:
            continue

        if canonical_name in SUPPORTED_CBC_MARKERS:

            detected_markers.append(
                canonical_name
            )

        else:

            unknown_markers.append(
                canonical_name
            )

    # -----------------------------------------------------
    # Detect duplicates
    # -----------------------------------------------------

    duplicate_markers = []

    seen = set()

    for marker in detected_markers:

        if marker in seen:

            if marker not in duplicate_markers:
                duplicate_markers.append(
                    marker
                )

        else:

            seen.add(
                marker
            )

    # -----------------------------------------------------
    # Unique detected supported markers
    # -----------------------------------------------------

    unique_detected = set(
        detected_markers
    )

    # -----------------------------------------------------
    # Missing supported markers
    # -----------------------------------------------------

    missing_markers = (
        SUPPORTED_CBC_MARKERS
        - unique_detected
    )

    # -----------------------------------------------------
    # Counts
    # -----------------------------------------------------

    expected_count = len(
        SUPPORTED_CBC_MARKERS
    )

    detected_count = len(
        unique_detected
    )

    missing_count = len(
        missing_markers
    )

    # -----------------------------------------------------
    # Coverage percentage
    # -----------------------------------------------------

    if expected_count == 0:

        coverage_percent = 0.0

    else:

        coverage_percent = round(
            (
                detected_count
                / expected_count
            )
            * 100,
            2
        )

    # -----------------------------------------------------
    # Coverage status
    # -----------------------------------------------------

    if detected_count == expected_count:

        status = "COMPLETE"

    elif detected_count == 0:

        status = "NO_COVERAGE"

    else:

        status = "INCOMPLETE"

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    return {
        "status": status,

        "expected_count": expected_count,

        "detected_count": detected_count,

        "missing_count": missing_count,

        "coverage_percent": coverage_percent,

        "detected_markers": sorted(
            unique_detected
        ),

        "missing_markers": sorted(
            missing_markers
        ),

        "duplicate_markers": sorted(
            duplicate_markers
        ),

        "unknown_markers": sorted(
            set(unknown_markers)
        )
    }