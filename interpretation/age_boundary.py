import math


SUPPORTED_AGE_UNITS = {
    "days",
    "weeks",
    "months",
    "years",
}


# =========================================================
# UNIT NORMALIZATION
# =========================================================

def normalize_age_unit(unit):
    if unit is None:
        return None

    value = str(unit).strip().lower()

    aliases = {
        "day": "days",
        "days": "days",

        "week": "weeks",
        "weeks": "weeks",
        "wk": "weeks",
        "wks": "weeks",

        "month": "months",
        "months": "months",
        "mon": "months",
        "mons": "months",

        "year": "years",
        "years": "years",
        "yr": "years",
        "yrs": "years",
    }

    return aliases.get(value)


# =========================================================
# AGE POINT
# =========================================================

def normalize_age_point(age):
    """
    Normalize an age point.

    Example:

        {
            "value": 15,
            "unit": "days"
        }
    """

    if not isinstance(age, dict):
        return None

    value = age.get("value")
    unit = normalize_age_unit(age.get("unit"))

    if value is None or unit is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(value):
        return None

    if value < 0:
        return None

    return {
        "value": value,
        "unit": unit,
    }


# =========================================================
# EXACT CONVERSION
# =========================================================

def convert_exact_age(age, target_unit):
    """
    Perform ONLY exact conversions.

    Currently safe:

        1 week = 7 days
        14 days = 2 weeks

    We deliberately DO NOT convert:

        months <-> days
        months <-> weeks
        years  <-> days
        years  <-> months

    because calendar months and years do not have fixed
    lengths without date-of-birth/specimen-date context.
    """

    age = normalize_age_point(age)
    target_unit = normalize_age_unit(target_unit)

    if age is None or target_unit is None:
        return None

    value = age["value"]
    source_unit = age["unit"]

    if source_unit == target_unit:
        return {
            "value": value,
            "unit": target_unit,
        }

    # Weeks -> days is exact.
    if source_unit == "weeks" and target_unit == "days":
        return {
            "value": value * 7,
            "unit": "days",
        }

    # Days -> weeks is exact only when the day count
    # represents an exact whole number of weeks.
    if source_unit == "days" and target_unit == "weeks":
        if value % 7 != 0:
            return None

        return {
            "value": value / 7,
            "unit": "weeks",
        }

    return None


# =========================================================
# AGE COMPARISON
# =========================================================

def compare_age_points(left, right):
    """
    Compare two age points.

    Returns:

        -1  -> left < right
         0  -> left == right
         1  -> left > right
         None -> comparison cannot be made safely

    Exact days/weeks conversion is allowed.

    Months/years are only compared when both sides use
    the same unit.
    """

    left = normalize_age_point(left)
    right = normalize_age_point(right)

    if left is None or right is None:
        return None

    # -----------------------------------------------------
    # Same units
    # -----------------------------------------------------

    if left["unit"] == right["unit"]:
        if left["value"] < right["value"]:
            return -1

        if left["value"] > right["value"]:
            return 1

        return 0

    # -----------------------------------------------------
    # Days / weeks can safely be compared in days.
    # -----------------------------------------------------

    exact_units = {
        "days",
        "weeks",
    }

    if (
        left["unit"] in exact_units
        and right["unit"] in exact_units
    ):
        left_days = convert_exact_age(
            left,
            "days",
        )

        right_days = convert_exact_age(
            right,
            "days",
        )

        if left_days is None or right_days is None:
            return None

        if left_days["value"] < right_days["value"]:
            return -1

        if left_days["value"] > right_days["value"]:
            return 1

        return 0

    # -----------------------------------------------------
    # Unsafe cross-unit comparison.
    # -----------------------------------------------------

    return None


# =========================================================
# BOUNDARY VALIDATION
# =========================================================

def validate_age_band(
    min_age,
    max_age,
):
    """
    Validate that an age band itself is logically ordered.

    Example:

        15 days -> 4 weeks

    is valid because:

        15 days < 28 days
    """

    min_age = normalize_age_point(min_age)
    max_age = normalize_age_point(max_age)

    if min_age is None or max_age is None:
        return {
            "valid": False,
            "reason": "Age boundary is missing or invalid.",
        }

    comparison = compare_age_points(
        min_age,
        max_age,
    )

    if comparison is None:
        return {
            "valid": False,
            "reason": (
                "The age-band boundaries use units that "
                "cannot be compared safely."
            ),
        }

    if comparison > 0:
        return {
            "valid": False,
            "reason": (
                "The minimum age boundary is greater than "
                "the maximum age boundary."
            ),
        }

    return {
        "valid": True,
        "reason": None,
    }


# =========================================================
# PATIENT VS LOWER BOUNDARY
# =========================================================

def check_lower_boundary(
    patient_age,
    min_age,
):
    """
    Check:

        patient_age >= min_age

    Returns:

        True
        False
        None -> unsafe comparison
    """

    comparison = compare_age_points(
        patient_age,
        min_age,
    )

    if comparison is None:
        return None

    return comparison >= 0


# =========================================================
# PATIENT VS UPPER BOUNDARY
# =========================================================

def check_upper_boundary(
    patient_age,
    max_age,
):
    """
    Check:

        patient_age <= max_age

    Returns:

        True
        False
        None -> unsafe comparison
    """

    comparison = compare_age_points(
        patient_age,
        max_age,
    )

    if comparison is None:
        return None

    return comparison <= 0


# =========================================================
# AGE BAND MATCHING
# =========================================================

def match_age_band(
    patient_age,
    min_age,
    max_age,
):
    """
    Determine whether the patient belongs to an age band.

    Example:

        Patient:
            20 days

        Range:
            15 days -> 4 weeks

        Result:
            MATCH
    """

    patient_age = normalize_age_point(
        patient_age
    )

    min_age = normalize_age_point(
        min_age
    )

    max_age = normalize_age_point(
        max_age
    )

    if patient_age is None:
        return {
            "status": "UNRESOLVED",
            "matches": False,
            "reason": "Patient age is missing or invalid.",
        }

    validation = validate_age_band(
        min_age,
        max_age,
    )

    if not validation["valid"]:
        return {
            "status": "UNRESOLVED",
            "matches": False,
            "reason": validation["reason"],
        }

    lower_result = check_lower_boundary(
        patient_age,
        min_age,
    )

    upper_result = check_upper_boundary(
        patient_age,
        max_age,
    )

    # -----------------------------------------------------
    # Patient age cannot safely be compared with one or
    # both boundaries.
    # -----------------------------------------------------

    if (
        lower_result is None
        or upper_result is None
    ):
        return {
            "status": "UNRESOLVED",
            "matches": False,
            "reason": (
                "Patient age cannot be safely compared "
                "with this age band without approximate "
                "calendar-unit conversion."
            ),
        }

    # -----------------------------------------------------
    # Match
    # -----------------------------------------------------

    if (
        lower_result is True
        and upper_result is True
    ):
        return {
            "status": "MATCH",
            "matches": True,
            "reason": None,
        }

    # -----------------------------------------------------
    # Comparable but outside range
    # -----------------------------------------------------

    return {
        "status": "NO_MATCH",
        "matches": False,
        "reason": None,
    }