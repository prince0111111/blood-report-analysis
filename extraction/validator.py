import re


# =========================================================
# EXPECTED UNITS
# =========================================================
#
# These are extraction-validation aliases.
#
# We are NOT converting units yet.
# We are only checking whether the extracted unit makes
# sense for the biomarker we think we extracted.
#
# Everything is converted to lowercase before comparison.
# =========================================================

EXPECTED_UNITS = {

    "hemoglobin": {
        "g/dl"
    },

    "rbc": {
        "mill/cmm",
        "million/cmm",
        "million/ul",
        "mill/ul"
    },

    "hematocrit": {
        "%"
    },

    "mcv": {
        "fl",
        "femtolitre",
        "femtoliter"
    },

    "mch": {
        "pg"
    },

    "mchc": {
        "g/dl"
    },

    "rdw": {
        "%"
    },

    "wbc": {
        "/cmm",
        "/ul",
        "cells/cmm",
        "cells/ul"
    },

    "neutrophils": {
        "%"
    },

    "lymphocytes": {
        "%"
    },

    "eosinophils": {
        "%"
    },

    "monocytes": {
        "%"
    },

    "basophils": {
        "%"
    },

    "platelets": {
        "/ul",
        "/cmm"
    }
}


# =========================================================
# UNIT NORMALIZATION
# =========================================================

def normalize_unit(unit):
    """
    Normalize unit text for structural comparison.

    Example:

        " g/dL "  -> "g/dl"
        " /uL "   -> "/ul"

    This does NOT perform unit conversion.
    """

    if unit is None:
        return None

    normalized = str(unit).strip().lower()

    # Normalize micro symbols to simple "u"
    normalized = normalized.replace("µ", "u")
    normalized = normalized.replace("μ", "u")

    # Remove unnecessary spaces
    normalized = re.sub(
        r"\s+",
        "",
        normalized
    )

    return normalized


# =========================================================
# UNIT VALIDATION
# =========================================================

def validate_unit(
    canonical_name,
    unit
):
    """
    Check whether the extracted unit is recognized for
    the extracted biomarker.

    Returns:

        True
        False
        None

    None means we do not yet have unit rules for the test.
    """

    if not canonical_name:
        return False

    if not unit:
        return False

    expected = EXPECTED_UNITS.get(
        canonical_name
    )

    if expected is None:
        return None

    normalized = normalize_unit(
        unit
    )

    normalized_expected = {
        normalize_unit(item)
        for item in expected
    }

    return normalized in normalized_expected


# =========================================================
# REFERENCE RANGE PARSER
# =========================================================

def parse_simple_reference_range(reference_raw):
    """
    Parse simple laboratory reference ranges.

    Currently supported examples:

        [13.0-18.0]
        [42-52]
        [60  - 70]
        13 - 18
        13 to 18

    Returns:

        {
            "parsed": True,
            "min": 13.0,
            "max": 18.0
        }

    or:

        {
            "parsed": False,
            "min": None,
            "max": None
        }

    IMPORTANT:

    This parser intentionally handles ONLY simple
    min-max ranges for now.

    More complex ranges such as:

        < 150
        > 60
        Up to 34
        Male: 0.6 to 1.1
        Female: 0.5 to 0.9

    will be implemented separately later.
    """

    result = {
        "parsed": False,
        "min": None,
        "max": None
    }

    if not reference_raw:
        return result

    reference = str(
        reference_raw
    ).strip()

    # Remove square brackets
    reference = reference.replace(
        "[",
        ""
    )

    reference = reference.replace(
        "]",
        ""
    )

    # Convert "to" into "-"
    reference = re.sub(
        r"\bto\b",
        "-",
        reference,
        flags=re.IGNORECASE
    )

    # Match:
    #
    # 13-18
    # 13.0 - 18.0
    # 4000-10000
    #
    pattern = re.compile(
        r"^\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*-\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*$"
    )

    match = pattern.match(
        reference
    )

    if not match:
        return result

    try:

        minimum = float(
            match.group(1)
        )

        maximum = float(
            match.group(2)
        )

    except ValueError:
        return result

    result["parsed"] = True
    result["min"] = minimum
    result["max"] = maximum

    return result


# =========================================================
# VALUE VALIDATION
# =========================================================

def validate_numeric_value(value):
    """
    Validate that an extracted result is numeric.

    bool is rejected because Python treats bool as int.
    """

    if value is None:
        return False

    if isinstance(value, bool):
        return False

    if isinstance(
        value,
        (int, float)
    ):
        return True

    return False


# =========================================================
# INDIVIDUAL TEST VALIDATION
# =========================================================

def validate_single_test(test):
    """
    Perform completeness + Level 2 structural validation
    for one extracted blood test.
    """

    issues = []

    canonical_name = test.get(
        "canonical_name"
    )

    value = test.get(
        "value"
    )

    unit = test.get(
        "unit"
    )

    reference_raw = test.get(
        "reference_raw"
    )

    # -----------------------------------------------------
    # TEST NAME
    # -----------------------------------------------------

    if not canonical_name:

        issues.append(
            "missing_test_name"
        )

    # -----------------------------------------------------
    # VALUE
    # -----------------------------------------------------

    if value is None:

        issues.append(
            "missing_value"
        )

    elif not validate_numeric_value(value):

        issues.append(
            "invalid_numeric_value"
        )

    # -----------------------------------------------------
    # UNIT
    # -----------------------------------------------------

    if not unit:

        issues.append(
            "missing_unit"
        )

    elif canonical_name:

        unit_result = validate_unit(
            canonical_name,
            unit
        )

        if unit_result is False:

            issues.append(
                "unrecognized_unit"
            )

    # -----------------------------------------------------
    # REFERENCE RANGE
    # -----------------------------------------------------

    reference_parsed = {
        "parsed": False,
        "min": None,
        "max": None
    }

    if not reference_raw:

        issues.append(
            "missing_reference_range"
        )

    else:

        reference_parsed = (
            parse_simple_reference_range(
                reference_raw
            )
        )

        if not reference_parsed["parsed"]:

            issues.append(
                "unparsable_reference_range"
            )

        else:

            minimum = reference_parsed[
                "min"
            ]

            maximum = reference_parsed[
                "max"
            ]

            if minimum >= maximum:

                issues.append(
                    "invalid_reference_range"
                )

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "reference": reference_parsed
    }


# =========================================================
# ALL TESTS VALIDATION
# =========================================================

def validate_tests(tests: list) -> dict:
    """
    Validate all extracted blood tests.
    """

    issues = []
    valid_tests = []

    if not tests:

        return {
            "status": "UNSAFE_TO_ANALYZE",
            "total_tests": 0,
            "valid_test_count": 0,
            "valid_tests": [],
            "issues": [
                "No supported blood tests were detected."
            ]
        }

    for test in tests:

        result = validate_single_test(
            test
        )

        if result["valid"]:

            # Copy so validation metadata does not
            # unexpectedly modify parser output.

            validated_test = test.copy()

            validated_test[
                "reference_parsed"
            ] = result["reference"]

            valid_tests.append(
                validated_test
            )

        else:

            issues.append({
                "test": test.get(
                    "canonical_name"
                ),
                "raw_name": test.get(
                    "raw_name"
                ),
                "issues": result[
                    "issues"
                ]
            })

    # -----------------------------------------------------
    # OVERALL TEST STATUS
    # -----------------------------------------------------

    if len(valid_tests) == 0:

        status = (
            "UNSAFE_TO_ANALYZE"
        )

    elif len(issues) > 0:

        status = "PARTIAL"

    else:

        status = "VALID"

    return {
        "status": status,
        "total_tests": len(tests),
        "valid_test_count": len(
            valid_tests
        ),
        "valid_tests": valid_tests,
        "issues": issues
    }


# =========================================================
# PATIENT VALIDATION
# =========================================================

def validate_patient_context(
    patient: dict
) -> dict:
    """
    Validate patient context required for later
    interpretation.
    """

    issues = []

    age = patient.get(
        "age"
    )

    sex = patient.get(
        "sex"
    )

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    if age is None:

        issues.append(
            "missing_age"
        )

    elif not isinstance(
        age,
        int
    ):

        issues.append(
            "invalid_age"
        )

    elif age <= 0 or age > 120:

        issues.append(
            "invalid_age"
        )

    # -----------------------------------------------------
    # SEX
    # -----------------------------------------------------

    if sex is None:

        issues.append(
            "missing_sex"
        )

    elif sex not in [
        "male",
        "female"
    ]:

        issues.append(
            "invalid_sex"
        )

    return {
        "valid": len(issues) == 0,
        "issues": issues
    }


# =========================================================
# REPORT VALIDATION
# =========================================================

def validate_report(
    patient: dict,
    tests: list
) -> dict:
    """
    Perform complete report-level validation.
    """

    patient_result = (
        validate_patient_context(
            patient
        )
    )

    test_result = (
        validate_tests(
            tests
        )
    )

    issues = []
    user_questions = []

    # =====================================================
    # PATIENT ISSUES
    # =====================================================

    for issue in patient_result[
        "issues"
    ]:

        if issue == "missing_age":

            issues.append({
                "type":
                    "USER_INPUT_REQUIRED",

                "field":
                    "age",

                "message":
                    "We couldn't find your age "
                    "in the report."
            })

            user_questions.append({
                "field":
                    "age",

                "question":
                    "Please enter your age:"
            })

        elif issue == "invalid_age":

            issues.append({
                "type":
                    "USER_INPUT_REQUIRED",

                "field":
                    "age",

                "message":
                    "The age extracted from the "
                    "report appears invalid."
            })

            user_questions.append({
                "field":
                    "age",

                "question":
                    "Please confirm your age:"
            })

        elif issue == "missing_sex":

            issues.append({
                "type":
                    "USER_INPUT_REQUIRED",

                "field":
                    "sex",

                "message":
                    "We couldn't find your sex "
                    "in the report."
            })

            user_questions.append({
                "field":
                    "sex",

                "question":
                    "Please enter sex "
                    "(male/female):"
            })

        elif issue == "invalid_sex":

            issues.append({
                "type":
                    "USER_INPUT_REQUIRED",

                "field":
                    "sex",

                "message":
                    "The sex extracted from the "
                    "report could not be recognized."
            })

            user_questions.append({
                "field":
                    "sex",

                "question":
                    "Please confirm sex "
                    "(male/female):"
            })

    # =====================================================
    # TEST ISSUES
    # =====================================================

    for issue in test_result[
        "issues"
    ]:

        if isinstance(
            issue,
            str
        ):

            issues.append({
                "type":
                    "EXTRACTION_ERROR",

                "field":
                    "blood_tests",

                "message":
                    issue
            })

            continue

        test_name = (
            issue.get("raw_name")
            or issue.get("test")
            or "Unknown test"
        )

        for problem in issue.get(
            "issues",
            []
        ):

            # ---------------------------------------------
            # Human-readable messages
            # ---------------------------------------------

            messages = {

                "missing_test_name":
                    "test name is missing",

                "missing_value":
                    "result value is missing",

                "invalid_numeric_value":
                    "result value is not numeric",

                "missing_unit":
                    "unit is missing",

                "unrecognized_unit":
                    "unit could not be recognized",

                "missing_reference_range":
                    "reference range is missing",

                "unparsable_reference_range":
                    "reference range could not be parsed",

                "invalid_reference_range":
                    "reference range appears invalid"
            }

            readable_problem = (
                messages.get(
                    problem,
                    problem.replace(
                        "_",
                        " "
                    )
                )
            )

            issues.append({
                "type":
                    "TEST_DATA_INVALID",

                "test":
                    issue.get("test"),

                "field":
                    problem,

                "message":
                    f"{test_name}: "
                    f"{readable_problem}."
            })

    # =====================================================
    # FINAL STATUS
    # =====================================================

    if test_result[
        "status"
    ] == "UNSAFE_TO_ANALYZE":

        status = (
            "UNSAFE_TO_ANALYZE"
        )

        can_analyze = False

    elif not patient_result[
        "valid"
    ]:

        status = (
            "NEEDS_USER_INPUT"
        )

        can_analyze = False

    elif test_result[
        "status"
    ] == "PARTIAL":

        status = "PARTIAL"

        can_analyze = True

    else:

        status = "VALID"

        can_analyze = True

    return {
        "status":
            status,

        "can_analyze":
            can_analyze,

        "patient":
            patient,

        "tests_detected":
            test_result[
                "total_tests"
            ],

        "valid_tests":
            test_result[
                "valid_test_count"
            ],

        "validated_test_data":
            test_result[
                "valid_tests"
            ],

        "issues":
            issues,

        "user_questions":
            user_questions
    }


# =========================================================
# USER CORRECTIONS
# =========================================================

def apply_patient_corrections(
    patient: dict,
    corrections: dict
) -> dict:
    """
    Apply user-provided corrections without repeating
    PDF extraction.
    """

    updated_patient = (
        patient.copy()
    )

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    if "age" in corrections:

        age = corrections[
            "age"
        ]

        try:

            age = int(
                age
            )

            if 0 < age <= 120:

                updated_patient[
                    "age"
                ] = age

        except (
            TypeError,
            ValueError
        ):
            pass

    # -----------------------------------------------------
    # SEX
    # -----------------------------------------------------

    if "sex" in corrections:

        sex = str(
            corrections["sex"]
        ).strip().lower()

        aliases = {
            "m": "male",
            "male": "male",
            "f": "female",
            "female": "female"
        }

        if sex in aliases:

            updated_patient[
                "sex"
            ] = aliases[
                sex
            ]

    return updated_patient