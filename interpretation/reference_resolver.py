import re
from typing import Optional


# =========================================================
# CONSTANTS
# =========================================================

SUPPORTED_AGE_UNITS = {
    "days",
    "weeks",
    "months",
    "years"
}


# =========================================================
# RESULT HELPERS
# =========================================================

def unresolved(reason: str) -> dict:

    return {
        "resolved": False,
        "min": None,
        "max": None,
        "matched_by": None,

        "matched_age": None,
        "matched_age_value": None,
        "matched_age_unit": None,

        "matched_sex": None,

        "source": "laboratory_report",
        "reason": reason
    }


def resolved(
    minimum: float,
    maximum: float,
    matched_by: str,
    age=None,
    age_value=None,
    age_unit=None,
    sex=None
) -> dict:

    return {
        "resolved": True,
        "min": float(minimum),
        "max": float(maximum),

        "matched_by": matched_by,

        # Legacy field
        "matched_age": age,

        # New precise fields
        "matched_age_value": age_value,
        "matched_age_unit": age_unit,

        "matched_sex": sex,

        "source": "laboratory_report",
        "reason": None
    }


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_reference_text(
    reference_raw
) -> str:

    if reference_raw is None:
        return ""

    text = str(reference_raw)

    # Normalize dash variants.
    text = text.replace("–", "-")
    text = text.replace("—", "-")

    # Normalize line endings.
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Remove brackets commonly surrounding ranges.
    text = text.replace("[", "")
    text = text.replace("]", "")

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


# =========================================================
# BASIC VALUE RANGE
# =========================================================

def parse_min_max(text: str):
    """
    Parse a direct laboratory value interval.

    Examples:

        13 - 18
        13.0 - 18.0
        13 to 18
    """

    if not text:
        return None

    pattern = re.compile(
        r"^\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*(?:-|to)\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*$",
        re.IGNORECASE
    )

    match = pattern.match(
        text.strip()
    )

    if not match:
        return None

    minimum = float(
        match.group(1)
    )

    maximum = float(
        match.group(2)
    )

    if minimum >= maximum:
        return None

    return (
        minimum,
        maximum
    )


# =========================================================
# SEX NORMALIZATION
# =========================================================

def normalize_sex(sex):

    if sex is None:
        return None

    value = str(
        sex
    ).strip().lower()

    aliases = {
        "m": "male",
        "male": "male",

        "f": "female",
        "female": "female"
    }

    return aliases.get(
        value
    )


# =========================================================
# AGE UNIT NORMALIZATION
# =========================================================

def normalize_age_unit(unit):

    if unit is None:
        return None

    value = str(
        unit
    ).strip().lower()

    aliases = {
        # Days
        "day": "days",
        "days": "days",

        # Weeks
        "week": "weeks",
        "weeks": "weeks",
        "wk": "weeks",
        "wks": "weeks",

        # Months
        "month": "months",
        "months": "months",
        "mon": "months",
        "mons": "months",

        # Years
        "year": "years",
        "years": "years",
        "yr": "years",
        "yrs": "years"
    }

    return aliases.get(
        value
    )


# =========================================================
# PATIENT AGE NORMALIZATION
# =========================================================

def get_patient_age(
    patient: dict
) -> dict:
    """
    Return patient age using the new representation:

        age_value
        age_unit

    while remaining backward compatible with:

        age
    """

    if not patient:

        return {
            "value": None,
            "unit": None,
            "legacy_age": None
        }

    age_value = patient.get(
        "age_value"
    )

    age_unit = normalize_age_unit(
        patient.get(
            "age_unit"
        )
    )

    legacy_age = patient.get(
        "age"
    )

    # -----------------------------------------------------
    # Prefer new representation
    # -----------------------------------------------------

    if (
        age_value is not None
        and age_unit is not None
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
            and age_value >= 0
        ):

            return {
                "value": age_value,
                "unit": age_unit,
                "legacy_age": (
                    age_value
                    if age_unit == "years"
                    else None
                )
            }

    # -----------------------------------------------------
    # Backward compatibility
    # -----------------------------------------------------

    if legacy_age is not None:

        try:

            legacy_age = int(
                legacy_age
            )

        except (
            TypeError,
            ValueError
        ):

            legacy_age = None

        if (
            legacy_age is not None
            and legacy_age >= 0
        ):

            return {
                "value": legacy_age,
                "unit": "years",
                "legacy_age": legacy_age
            }

    return {
        "value": None,
        "unit": None,
        "legacy_age": None
    }


# =========================================================
# DIRECT RANGE
# =========================================================

def resolve_direct_range(
    reference_text: str,
    patient: dict
):

    parsed = parse_min_max(
        reference_text
    )

    if parsed is None:
        return None

    minimum, maximum = parsed

    age = get_patient_age(
        patient
    )

    sex = normalize_sex(
        patient.get("sex")
    )

    return resolved(
        minimum=minimum,
        maximum=maximum,
        matched_by="report_direct",

        age=age["legacy_age"],
        age_value=age["value"],
        age_unit=age["unit"],

        sex=sex
    )


# =========================================================
# SEX-SPECIFIC RANGE
# =========================================================

def extract_sex_specific_ranges(
    reference_text: str
) -> dict:

    results = {}

    pattern = re.compile(
        r"\b(male|female)\b"
        r"\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*(?:-|to)\s*"
        r"(-?\d+(?:\.\d+)?)",
        re.IGNORECASE
    )

    for match in pattern.finditer(
        reference_text
    ):

        sex = match.group(1).lower()

        minimum = float(
            match.group(2)
        )

        maximum = float(
            match.group(3)
        )

        if minimum >= maximum:
            continue

        results[sex] = {
            "min": minimum,
            "max": maximum
        }

    return results


def resolve_sex_specific_range(
    reference_text: str,
    patient: dict
):

    ranges = extract_sex_specific_ranges(
        reference_text
    )

    if not ranges:
        return None

    sex = normalize_sex(
        patient.get("sex")
    )

    if sex is None:

        return unresolved(
            "The report contains sex-specific reference "
            "intervals, but patient sex is unavailable "
            "or invalid."
        )

    selected = ranges.get(
        sex
    )

    if selected is None:

        return unresolved(
            "The report contains sex-specific reference "
            "intervals, but no interval matched the "
            "patient."
        )

    age = get_patient_age(
        patient
    )

    return resolved(
        minimum=selected["min"],
        maximum=selected["max"],
        matched_by="sex",

        age=age["legacy_age"],
        age_value=age["value"],
        age_unit=age["unit"],

        sex=sex
    )


# =========================================================
# AGE BAND EXTRACTION
# =========================================================

def extract_age_ranges(
    text: str
) -> list:
    """
    Supported formats:

        0-7 days: 10-20
        8-30 days: 11-21

        1-6 months: 10-15
        7-12 months: 11-16

        2-4 weeks: 12-18

        1-5 years: 11-14
        6-12 years: 12-15

    The age-band unit is preserved.
    """

    rules = []

    pattern = re.compile(
        r"(\d+(?:\.\d+)?)"
        r"\s*(?:-|to)\s*"
        r"(\d+(?:\.\d+)?)"
        r"\s*"
        r"(days?|weeks?|wks?|months?|mons?|years?|yrs?)"
        r"\s*:?\s*"
        r"(-?\d+(?:\.\d+)?)"
        r"\s*(?:-|to)\s*"
        r"(-?\d+(?:\.\d+)?)",
        re.IGNORECASE
    )

    for match in pattern.finditer(
        text
    ):

        age_min = float(
            match.group(1)
        )

        age_max = float(
            match.group(2)
        )

        age_unit = normalize_age_unit(
            match.group(3)
        )

        value_min = float(
            match.group(4)
        )

        value_max = float(
            match.group(5)
        )

        if age_unit is None:
            continue

        if age_min > age_max:
            continue

        if value_min >= value_max:
            continue

        rules.append({
            "age_min": age_min,
            "age_max": age_max,
            "age_unit": age_unit,

            "min": value_min,
            "max": value_max
        })

    return rules


# =========================================================
# AGE MATCHING
# =========================================================

def age_rule_matches(
    patient_age: dict,
    rule: dict
) -> bool:
    """
    Safely compare patient age to an age-band rule.

    IMPORTANT:

    We only directly compare matching units.

    Example:

        patient = 6 months
        rule = 1-6 months
        -> safe

    But:

        patient = 6 months
        rule = 0-1 years
        -> not automatically converted

    This avoids approximate conversions.
    """

    patient_value = patient_age.get(
        "value"
    )

    patient_unit = patient_age.get(
        "unit"
    )

    rule_unit = rule.get(
        "age_unit"
    )

    if patient_value is None:
        return False

    if patient_unit is None:
        return False

    if rule_unit is None:
        return False

    # -----------------------------------------------------
    # SAFE RULE:
    # compare only identical age units
    # -----------------------------------------------------

    if patient_unit != rule_unit:
        return False

    return (
        patient_value
        >= rule["age_min"]
        and patient_value
        <= rule["age_max"]
    )


# =========================================================
# AGE RULE RESOLUTION
# =========================================================

def resolve_from_age_rules(
    rules: list,
    patient: dict,
    matched_by: str,
    sex=None
):
    """
    Shared resolver for age-only and age+sex rules.
    """

    patient_age = get_patient_age(
        patient
    )

    if (
        patient_age["value"] is None
        or patient_age["unit"] is None
    ):

        return unresolved(
            "The report contains age-specific reference "
            "intervals, but patient age is unavailable "
            "or invalid."
        )

    # -----------------------------------------------------
    # Check whether report even contains the patient's
    # age unit.
    # -----------------------------------------------------

    available_units = {
        rule["age_unit"]
        for rule in rules
    }

    if patient_age["unit"] not in available_units:

        return unresolved(
            "The report contains age-specific reference "
            "intervals, but none use the patient's age "
            f"unit ({patient_age['unit']}). Safe "
            "cross-unit age conversion was not attempted."
        )

    matches = []

    for rule in rules:

        if age_rule_matches(
            patient_age,
            rule
        ):

            matches.append(
                rule
            )

    if not matches:

        return unresolved(
            "No age-specific reference interval matched "
            "the patient's age."
        )

    if len(matches) > 1:

        return unresolved(
            "More than one age-specific reference "
            "interval matched the patient. The report "
            "reference is ambiguous."
        )

    selected = matches[0]

    return resolved(
        minimum=selected["min"],
        maximum=selected["max"],
        matched_by=matched_by,

        age=patient_age["legacy_age"],
        age_value=patient_age["value"],
        age_unit=patient_age["unit"],

        sex=sex
    )


# =========================================================
# SEX SECTION EXTRACTION
# =========================================================

def extract_sex_section(
    reference_text: str,
    sex: str
):
    """
    Example:

        Male:
        1-6 months: 10-15
        7-12 months: 11-16
        18-60 years: 13-17

        Female:
        1-6 months: 10-14
        7-12 months: 11-15
        18-60 years: 12-15
    """

    opposite = (
        "female"
        if sex == "male"
        else "male"
    )

    pattern = re.compile(
        rf"\b{sex}\b\s*:?"
        rf"(.*?)"
        rf"(?=\b{opposite}\b\s*:|$)",
        re.IGNORECASE | re.DOTALL
    )

    match = pattern.search(
        reference_text
    )

    if not match:
        return None

    return match.group(1).strip()


# =========================================================
# AGE + SEX RANGE
# =========================================================

def resolve_age_and_sex_range(
    reference_text: str,
    patient: dict
):

    contains_sex = bool(
        re.search(
            r"\b(male|female)\b",
            reference_text,
            re.IGNORECASE
        )
    )

    contains_age_band = bool(
        re.search(
            r"\d+(?:\.\d+)?"
            r"\s*(?:-|to)\s*"
            r"\d+(?:\.\d+)?"
            r"\s*"
            r"(?:days?|weeks?|wks?|months?|mons?|years?|yrs?)",
            reference_text,
            re.IGNORECASE
        )
    )

    if not (
        contains_sex
        and contains_age_band
    ):

        return None

    sex = normalize_sex(
        patient.get("sex")
    )

    if sex is None:

        return unresolved(
            "The report contains age- and sex-specific "
            "reference intervals, but patient sex is "
            "unavailable or invalid."
        )

    patient_age = get_patient_age(
        patient
    )

    if (
        patient_age["value"] is None
        or patient_age["unit"] is None
    ):

        return unresolved(
            "The report contains age- and sex-specific "
            "reference intervals, but patient age is "
            "unavailable or invalid."
        )

    section = extract_sex_section(
        reference_text,
        sex
    )

    if section is None:

        return unresolved(
            "No reference section matched the "
            "patient's sex."
        )

    age_rules = extract_age_ranges(
        section
    )

    if not age_rules:

        return unresolved(
            "The matching sex section did not contain "
            "a supported age-specific reference interval."
        )

    return resolve_from_age_rules(
        rules=age_rules,
        patient=patient,
        matched_by="age_and_sex",
        sex=sex
    )


# =========================================================
# AGE-ONLY RANGE
# =========================================================

def resolve_age_specific_range(
    reference_text: str,
    patient: dict
):

    # Age + sex structures belong to the previous resolver.
    if re.search(
        r"\b(male|female)\b",
        reference_text,
        re.IGNORECASE
    ):

        return None

    rules = extract_age_ranges(
        reference_text
    )

    if not rules:
        return None

    sex = normalize_sex(
        patient.get("sex")
    )

    return resolve_from_age_rules(
        rules=rules,
        patient=patient,
        matched_by="age",
        sex=sex
    )


# =========================================================
# MAIN RESOLVER
# =========================================================

def resolve_reference_range(
    reference_raw,
    patient: dict
) -> dict:
    """
    Resolve the laboratory reference interval applicable
    to the current patient.

    Priority:

        1. Age + sex
        2. Sex
        3. Age
        4. Direct range

    IMPORTANT:

    This module does NOT use an external medical database.

    It only resolves reference intervals printed in the
    laboratory report.

    It also refuses unsafe age-unit guessing.
    """

    if patient is None:
        patient = {}

    reference_text = normalize_reference_text(
        reference_raw
    )

    if not reference_text:

        return unresolved(
            "Reference interval is missing from "
            "the laboratory report."
        )

    # =====================================================
    # 1. AGE + SEX
    # =====================================================

    result = resolve_age_and_sex_range(
        reference_text,
        patient
    )

    if result is not None:
        return result

    # =====================================================
    # 2. SEX
    # =====================================================

    result = resolve_sex_specific_range(
        reference_text,
        patient
    )

    if result is not None:
        return result

    # =====================================================
    # 3. AGE
    # =====================================================

    result = resolve_age_specific_range(
        reference_text,
        patient
    )

    if result is not None:
        return result

    # =====================================================
    # 4. DIRECT
    # =====================================================

    result = resolve_direct_range(
        reference_text,
        patient
    )

    if result is not None:
        return result

    # =====================================================
    # UNSUPPORTED
    # =====================================================

    return unresolved(
        "The laboratory reference interval could not "
        "be safely resolved for this patient."
    )