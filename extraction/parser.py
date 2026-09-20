import re


# =========================================================
# TEST ALIASES
# =========================================================
#
# These are OCR variations that can represent the same
# canonical laboratory marker.
#
# IMPORTANT:
# This parser consumes TEXT.
# OCR is responsible only for producing the text.
# =========================================================

TEST_ALIASES = {
    "hemoglobin": "hemoglobin",

    "total rbc count": "rbc",
    "rbc count": "rbc",
    "rbc": "rbc",

    "p.c.v": "hematocrit",
    "pcv": "hematocrit",
    "packed cell volume": "hematocrit",
    "hematocrit": "hematocrit",
    "hematrocrit": "hematocrit",

    "m.c.v": "mcv",
    "m.c.v.": "mcv",
    "mc v": "mcv",
    "mcv": "mcv",

    "m.c.h": "mch",
    "m.c.h.": "mch",
    "mch": "mch",

    "m.c.h.c": "mchc",
    "m.c.h.c.": "mchc",
    "mchc": "mchc",

    "r.d.w": "rdw",
    "r.d.w.": "rdw",
    "rdw": "rdw",
    "rdw cv": "rdw",
    "rdw-cv": "rdw",

    "total wbc count": "wbc",
    "total count (wbc)": "wbc",
    "wbc count": "wbc",
    "wbc": "wbc",

    "neutrophils": "neutrophils",
    "neutrophils (%)": "neutrophils",

    "lymphocytes": "lymphocytes",
    "lymphocytes (%)": "lymphocytes",

    "eosinophils": "eosinophils",
    "eosinophils (%)": "eosinophils",

    "monocytes": "monocytes",
    "monocytes (%)": "monocytes",

    "basophils": "basophils",
    "basophils (%)": "basophils",

    "platelet count": "platelets",
    "platelet": "platelets",
    "platelet count": "platelets",
    "platelets": "platelets",
}


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_test_name(name: str) -> str:
    """
    Normalize OCR test names so harmless OCR/layout
    variations do not prevent matching.
    """

    name = str(name).strip().lower()

    # Normalize whitespace
    name = re.sub(r"\s+", " ", name)

    # Remove trailing punctuation
    name = name.strip(" :")

    return name


# =========================================================
# TEST LOOKUP
# =========================================================

def get_canonical_name(raw_name: str):
    """
    Convert an OCR test name into our canonical name.
    """

    normalized = normalize_test_name(raw_name)

    return TEST_ALIASES.get(normalized)


# =========================================================
# VALUE / REFERENCE HELPERS
# =========================================================

NUMBER_PATTERN = re.compile(
    r"^\s*-?\d+(?:\.\d+)?\s*$"
)


REFERENCE_PATTERN = re.compile(
    r"^\s*"
    r"-?\d+(?:\.\d+)?"
    r"\s*"
    r"(?:-|to)"
    r"\s*"
    r"-?\d+(?:\.\d+)?"
    r"\s*$",
    re.IGNORECASE
)


def parse_numeric(value: str):
    """
    Parse a simple numeric OCR value.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not NUMBER_PATTERN.match(value):
        return None

    try:
        return float(value)

    except ValueError:
        return None


def looks_like_reference(value: str) -> bool:
    """
    Check whether a line looks like a biological
    reference interval.
    """

    if value is None:
        return False

    return bool(
        REFERENCE_PATTERN.match(
            str(value).strip()
        )
    )


# =========================================================
# CBC PARSER
# =========================================================

def parse_cbc(cleaned_text: str) -> list:
    """
    Parse CBC test results from cleaned OCR/PDF text.

    The parser accepts multiple laboratory/OCR naming
    variations but produces the same canonical structure.

    Expected general structure:

        TEST NAME
        VALUE
        UNIT
        REFERENCE

    The parser intentionally looks only at nearby lines
    because different laboratories may insert additional
    metadata between fields.
    """

    if not cleaned_text:
        return []

    lines = [
        line.strip()
        for line in str(cleaned_text).splitlines()
        if line.strip()
    ]

    tests = []

    for index, line in enumerate(lines):

        canonical_name = get_canonical_name(line)

        if canonical_name is None:
            continue

        result = {
            "raw_name": line,
            "canonical_name": canonical_name,
            "value": None,
            "unit": None,
            "reference_raw": None
        }

        # -------------------------------------------------
        # Search the following lines.
        #
        # We do NOT assume every laboratory has exactly
        # three lines after the test name.
        # -------------------------------------------------

        window = lines[index + 1:index + 7]

        value_index = None

        # -------------------------------------------------
        # Find first numeric value.
        # -------------------------------------------------

        for offset, candidate in enumerate(window):

            numeric_value = parse_numeric(candidate)

            if numeric_value is not None:

                result["value"] = numeric_value
                value_index = offset

                break

        if value_index is None:
            tests.append(result)
            continue

        # -------------------------------------------------
        # Find unit.
        #
        # Usually immediately after the value.
        # -------------------------------------------------

        if value_index + 1 < len(window):

            candidate = window[value_index + 1]

            if not looks_like_reference(candidate):

                result["unit"] = candidate

        # -------------------------------------------------
        # Find reference interval.
        #
        # Search several lines after the value because
        # some reports insert extra text.
        # -------------------------------------------------

        for candidate in window[value_index + 1:]:

            if looks_like_reference(candidate):

                result["reference_raw"] = candidate

                break

        tests.append(result)

    return tests