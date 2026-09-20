import re


# =========================================================
# AGE UNIT NORMALIZATION
# =========================================================

def normalize_age_unit(unit):
    """
    Convert different age-unit spellings into one
    canonical representation.

    Examples:

        Year   -> years
        Years  -> years
        Yr     -> years
        Month  -> months
        Day    -> days
        Week   -> weeks
    """

    if unit is None:
        return None

    unit = str(unit).strip().lower()

    aliases = {
        # Years
        "year": "years",
        "years": "years",
        "yr": "years",
        "yrs": "years",

        # Months
        "month": "months",
        "months": "months",
        "mon": "months",
        "mons": "months",

        # Weeks
        "week": "weeks",
        "weeks": "weeks",
        "wk": "weeks",
        "wks": "weeks",

        # Days
        "day": "days",
        "days": "days"
    }

    return aliases.get(unit)


# =========================================================
# SEX NORMALIZATION
# =========================================================

def normalize_sex(sex):
    """
    Normalize common sex labels.
    """

    if sex is None:
        return None

    sex = str(sex).strip().lower()

    aliases = {
        "m": "male",
        "male": "male",

        "f": "female",
        "female": "female"
    }

    return aliases.get(sex)


# =========================================================
# AGE VALIDATION
# =========================================================

def is_reasonable_age(
    age_value,
    age_unit
):
    """
    Basic extraction sanity check.

    These are NOT medical reference ranges.

    They only prevent obviously invalid extracted ages.
    """

    if age_value is None:
        return False

    if age_unit is None:
        return False

    if age_value < 0:
        return False

    limits = {
        "days": 36600,
        "weeks": 5220,
        "months": 1440,
        "years": 120
    }

    maximum = limits.get(
        age_unit
    )

    if maximum is None:
        return False

    return age_value <= maximum


# =========================================================
# PATIENT RESULT
# =========================================================

def build_patient_result(
    age_value=None,
    age_unit=None,
    sex=None
):
    """
    Create the standard patient-context structure.

    `age` is retained for backward compatibility.

    IMPORTANT:

    For patients measured in months/weeks/days,
    `age` remains None.

    We do NOT convert:

        6 months -> 0 years

    because that would lose clinically important age
    information.
    """

    patient = {
        "age": None,
        "age_value": None,
        "age_unit": None,
        "sex": None
    }

    normalized_unit = normalize_age_unit(
        age_unit
    )

    normalized_sex = normalize_sex(
        sex
    )

    if (
        age_value is not None
        and normalized_unit is not None
    ):

        try:
            age_value = int(
                age_value
            )

        except (
            TypeError,
            ValueError
        ):
            age_value = None

    if (
        age_value is not None
        and is_reasonable_age(
            age_value,
            normalized_unit
        )
    ):

        patient["age_value"] = age_value
        patient["age_unit"] = normalized_unit

        # ---------------------------------------------
        # Backward-compatible age field
        # ---------------------------------------------

        if normalized_unit == "years":

            patient["age"] = age_value

    patient["sex"] = normalized_sex

    return patient


# =========================================================
# PATIENT EXTRACTION
# =========================================================

def extract_patient_context(
    cleaned_text: str
) -> dict:
    """
    Extract patient age and sex from cleaned report text.

    Supported examples include:

        Age / Gender : 34 Years/Male
        Age/Gender: 6 Months/Female
        Age / Sex : 15 Days / Male
        Age/Sex: 3 Weeks/Female

    Returned structure:

        {
            "age": 34,
            "age_value": 34,
            "age_unit": "years",
            "sex": "male"
        }

    For an infant:

        {
            "age": None,
            "age_value": 6,
            "age_unit": "months",
            "sex": "female"
        }
    """

    empty_patient = build_patient_result()

    if not cleaned_text:
        return empty_patient

    # -----------------------------------------------------
    # Flatten PDF line breaks.
    # -----------------------------------------------------

    searchable_text = " ".join(
        str(cleaned_text).splitlines()
    )

    searchable_text = re.sub(
        r"\s+",
        " ",
        searchable_text
    ).strip()

    # =====================================================
    # AGE + SEX / GENDER
    # =====================================================
    #
    # Examples:
    #
    # Age / Gender : 34 Years/Male
    # Age/Gender: 6 Months/Female
    # Age / Sex : 15 Days / Male
    # Age/Sex: 3 Weeks/Female
    #
    # =====================================================

    combined_pattern = re.compile(
        r"\bAge\s*/\s*(?:Gender|Sex)"
        r"\s*:?\s*"
        r"(\d+)"
        r"\s*"
        r"(Years?|Yrs?|Months?|Mons?|Weeks?|Wks?|Days?)"
        r"\s*/\s*"
        r"(Male|Female|M|F)\b",
        re.IGNORECASE
    )

    match = combined_pattern.search(
        searchable_text
    )

    if match:

        return build_patient_result(
            age_value=match.group(1),
            age_unit=match.group(2),
            sex=match.group(3)
        )

    # =====================================================
    # FALLBACK — AGE AND SEX SEPARATELY
    # =====================================================

    age_value = None
    age_unit = None
    sex = None

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    age_pattern = re.compile(
        r"\bAge\b"
        r"\s*:?\s*"
        r"(\d+)"
        r"\s*"
        r"(Years?|Yrs?|Months?|Mons?|Weeks?|Wks?|Days?)"
        r"\b",
        re.IGNORECASE
    )

    age_match = age_pattern.search(
        searchable_text
    )

    if age_match:

        age_value = age_match.group(1)
        age_unit = age_match.group(2)

    # -----------------------------------------------------
    # SEX / GENDER
    # -----------------------------------------------------

    sex_pattern = re.compile(
        r"\b(?:Sex|Gender)\b"
        r"\s*:?\s*"
        r"(Male|Female|M|F)\b",
        re.IGNORECASE
    )

    sex_match = sex_pattern.search(
        searchable_text
    )

    if sex_match:

        sex = sex_match.group(1)

    return build_patient_result(
        age_value=age_value,
        age_unit=age_unit,
        sex=sex
    )