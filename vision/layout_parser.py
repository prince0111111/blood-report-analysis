"""
vision/layout_parser.py

General-purpose layout parser for blood report OCR text.

PURPOSE
-------
Accept raw OCR text (from any layout) and return a list of
test dicts in the canonical format already consumed by the
existing extraction pipeline:

    {
        "raw_name":       str,
        "canonical_name": str,
        "value":          float | None,
        "unit":           str | None,
        "reference_raw":  str | None,
        "abnormal_flag":  str | None,   # explicit in source only
        "layout":         str,          # which strategy matched
    }

SUPPORTED LAYOUTS
-----------------
1. Vertical (one token per line)
       Hemoglobin
       15.9
       g/dl
       13.0-18.0

2. Tabular — tab/space-separated columns
       Hemoglobin    15.9    g/dl    13.0-18.0

3. Inline — value and unit on the same line as the test name
       Hemoglobin: 15.9 g/dl  [13.0-18.0]

4. Parenthesised reference range
       Hemoglobin    15.9    g/dl    (13.0-18.0)

5. Explicit abnormal flag column
       Hemoglobin    15.9 H    g/dl    13.0-18.0

6. Multi-section (CBC / Liver / Kidney / Lipid)
       Sections are detected by header lines; each section
       is parsed independently with the same strategies.

7. Multi-page  — handled transparently; the caller joins
       pages with --- PAGE N --- markers before calling here.

DESIGN RULES
------------
- Does NOT hardcode one laboratory's layout.
- Does NOT add medical interpretation rules.
- Does NOT compute LOW / NORMAL / HIGH.
- Uses the existing TEST_ALIASES from extraction.parser for
  canonical name resolution.
- Preserves raw values; marks uncertainty via value=None.
- Abnormal flags are only preserved when explicitly present
  in the source text — never computed.
"""

from __future__ import annotations

import re
from typing import Optional

from extraction.parser import TEST_ALIASES


# =========================================================
# CONSTANTS
# =========================================================

# Regex: a numeric value, possibly negative, possibly decimal
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")

# Regex: reference range in any of these forms:
#   13.0-18.0   13 - 18   13 to 18   [13-18]   (13-18)
_REF_RE = re.compile(
    r"[\[\(]?\s*(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*[\]\)]?",
    re.IGNORECASE,
)

# Regex: explicit abnormal flag — H, HH, L, LL, *, A
# Must be surrounded by non-word chars or string boundaries
_FLAG_RE = re.compile(r"(?<!\w)(H{1,2}|L{1,2}|\*|A)(?!\w)")

# Section header keywords — lines that introduce a new panel
_SECTION_HEADERS = re.compile(
    r"^\s*(?:"
    r"complete\s+blood\s+count|cbc|haematology|hematology"
    r"|liver\s+function|lft|hepatic"
    r"|kidney\s+function|renal\s+function|rft"
    r"|lipid\s+profile|lipid\s+panel|cholesterol"
    r"|thyroid\s+function|tft"
    r"|diabetes|blood\s+sugar|glucose"
    r"|biochemistry|chemistry"
    r")\s*$",
    re.IGNORECASE,
)

# Lines that are clearly not test data
_SKIP_RE = re.compile(
    r"^\s*(?:"
    r"---\s*page\s+\d+\s*---"
    r"|page\s+\d+\s+of\s+\d+"
    r"|patient\s+name|patient\s+id|ref(?:erence)?\s+(?:no|number|#)"
    r"|date|lab(?:oratory)?\s+(?:name|report|no)"
    r"|doctor|physician|consultant"
    r"|test\s+name|test|result|unit|reference|normal\s+range"
    r"|investigation|parameter|analyte"
    r")\s*$",
    re.IGNORECASE,
)

# Minimum number of characters for a line to be worth parsing
# Set to 1 to preserve single-char units like "%"
_MIN_LINE_LEN = 1


# =========================================================
# ALIAS LOOKUP
# =========================================================

def _canonical(raw_name: str) -> Optional[str]:
    """
    Return the canonical test name for a raw name string,
    or None if not in the alias map.

    Strips trailing punctuation and normalises whitespace
    before lookup.
    """
    cleaned = raw_name.strip().rstrip(":").strip()
    return TEST_ALIASES.get(cleaned)


def _is_known_test(line: str) -> bool:
    return _canonical(line) is not None


# =========================================================
# VALUE / UNIT / REFERENCE EXTRACTION HELPERS
# =========================================================

def _extract_flag(token: str) -> tuple[str, Optional[str]]:
    """
    Strip an explicit abnormal flag from a value token.

    Returns (clean_value_str, flag | None).

    Example:
        "15.9 H"  → ("15.9", "H")
        "15.9"    → ("15.9", None)
    """
    m = _FLAG_RE.search(token)
    if m:
        flag = m.group(1)
        clean = token[: m.start()].strip() + token[m.end() :].strip()
        return clean.strip(), flag
    return token.strip(), None


def _parse_value(token: str) -> Optional[float]:
    """Parse a numeric value from a token string."""
    m = _NUM_RE.fullmatch(token.strip())
    if m:
        try:
            return float(m.group())
        except ValueError:
            pass
    return None


def _parse_reference(token: str) -> Optional[str]:
    """
    Return the raw reference range string if the token
    looks like a reference range, else None.
    """
    if _REF_RE.search(token):
        return token.strip()
    return None


# =========================================================
# STRATEGY 1 — VERTICAL (one token per line)
# =========================================================

def _parse_vertical(lines: list[str]) -> list[dict]:
    """
    Parse a vertical layout where each test occupies
    consecutive lines:

        TestName
        value
        unit
        reference_range

    The window after the test name is scanned for value,
    unit, and reference in that order.
    """
    results = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        canonical = _canonical(line)
        if canonical is None:
            i += 1
            continue

        raw_name = line
        value: Optional[float] = None
        unit: Optional[str] = None
        reference_raw: Optional[str] = None
        flag: Optional[str] = None

        window = lines[i + 1 : i + 6]
        j = 0

        # value (possibly with flag)
        if j < len(window):
            tok, f = _extract_flag(window[j].strip())
            v = _parse_value(tok)
            if v is not None:
                value = v
                flag = f
                j += 1

        # unit
        if j < len(window):
            candidate = window[j].strip()
            if not _is_known_test(candidate) and not _parse_value(candidate):
                ref = _parse_reference(candidate)
                if ref:
                    reference_raw = ref
                    j += 1
                else:
                    unit = candidate
                    j += 1

        # reference range
        if j < len(window) and reference_raw is None:
            candidate = window[j].strip()
            ref = _parse_reference(candidate)
            if ref:
                reference_raw = ref

        results.append(_make_result(raw_name, canonical, value, unit, reference_raw, flag, "vertical"))
        i += 1

    return results


# =========================================================
# STRATEGY 2 — TABULAR (columns on one line)
# =========================================================

# Separator: two or more spaces, or a tab
_COL_SEP = re.compile(r"\t|  +")


def _parse_tabular(lines: list[str]) -> list[dict]:
    """
    Parse a tabular layout where each row contains
    multiple columns separated by tabs or multiple spaces:

        Hemoglobin    15.9    g/dl    13.0-18.0
        Hemoglobin    15.9 H  g/dl    13.0-18.0
    """
    results = []
    for line in lines:
        cols = [c.strip() for c in _COL_SEP.split(line) if c.strip()]
        if len(cols) < 2:
            continue

        canonical = _canonical(cols[0])
        if canonical is None:
            continue

        raw_name = cols[0]
        value: Optional[float] = None
        unit: Optional[str] = None
        reference_raw: Optional[str] = None
        flag: Optional[str] = None

        # col 1 — value (possibly with flag)
        if len(cols) > 1:
            tok, f = _extract_flag(cols[1])
            v = _parse_value(tok)
            if v is not None:
                value = v
                flag = f

        # col 2 — unit or reference
        if len(cols) > 2:
            ref = _parse_reference(cols[2])
            if ref:
                reference_raw = ref
            else:
                unit = cols[2]

        # col 3 — reference range
        if len(cols) > 3 and reference_raw is None:
            ref = _parse_reference(cols[3])
            if ref:
                reference_raw = ref

        # col 4 — sometimes flag is in its own column
        if len(cols) > 4 and flag is None:
            _, f = _extract_flag(cols[4])
            if f:
                flag = f

        results.append(_make_result(raw_name, canonical, value, unit, reference_raw, flag, "tabular"))

    return results


# =========================================================
# STRATEGY 3 — INLINE (value/unit on same line as name)
# =========================================================

# Pattern: TestName: value unit  [ref] or (ref)
_INLINE_RE = re.compile(
    r"^(.+?)\s*:?\s+"                          # test name
    r"(-?\d+(?:\.\d+)?)\s*"                    # value
    r"(H{1,2}|L{1,2}|\*|A)?\s*"               # optional flag
    r"([^\d\[\(]*?)\s*"                        # unit (non-numeric prefix)
    r"(?:[\[\(]\s*(-?\d+(?:\.\d+)?)\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)\s*[\]\)])?"  # ref
    r"\s*$",
    re.IGNORECASE,
)


def _parse_inline(lines: list[str]) -> list[dict]:
    """
    Parse an inline layout where the test name, value,
    unit, and reference range all appear on one line:

        Hemoglobin: 15.9 g/dl [13.0-18.0]
        Hemoglobin 15.9 H g/dl (13.0-18.0)
    """
    results = []
    for line in lines:
        m = _INLINE_RE.match(line.strip())
        if not m:
            continue

        raw_name_candidate = m.group(1).strip().rstrip(":").strip()
        canonical = _canonical(raw_name_candidate)
        if canonical is None:
            continue

        value_str = m.group(2)
        flag = m.group(3) or None
        unit = (m.group(4) or "").strip() or None
        ref_min = m.group(5)
        ref_max = m.group(6)

        value = _parse_value(value_str)
        reference_raw = f"{ref_min}-{ref_max}" if ref_min and ref_max else None

        results.append(_make_result(raw_name_candidate, canonical, value, unit, reference_raw, flag, "inline"))

    return results


# =========================================================
# RESULT BUILDER
# =========================================================

def _make_result(
    raw_name: str,
    canonical_name: str,
    value: Optional[float],
    unit: Optional[str],
    reference_raw: Optional[str],
    abnormal_flag: Optional[str],
    layout: str,
) -> dict:
    return {
        "raw_name": raw_name,
        "canonical_name": canonical_name,
        "value": value,
        "unit": unit if unit else None,
        "reference_raw": reference_raw,
        "abnormal_flag": abnormal_flag,
        "layout": layout,
    }


# =========================================================
# SECTION SPLITTER
# =========================================================

def _split_sections(lines: list[str]) -> list[tuple[str, list[str]]]:
    """
    Split lines into named sections based on header keywords.

    Returns a list of (section_name, lines) tuples.
    Lines before the first header are placed in a
    "default" section.
    """
    sections: list[tuple[str, list[str]]] = []
    current_name = "default"
    current_lines: list[str] = []

    for line in lines:
        if _SECTION_HEADERS.match(line):
            if current_lines:
                sections.append((current_name, current_lines))
            current_name = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_name, current_lines))

    return sections if sections else [("default", lines)]


# =========================================================
# DEDUPLICATION
# =========================================================

def _deduplicate(results: list[dict]) -> list[dict]:
    """
    Remove duplicate canonical names, keeping the first
    occurrence (highest-confidence strategy result).
    """
    seen: set[str] = set()
    out = []
    for r in results:
        key = r["canonical_name"]
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


# =========================================================
# STRATEGY RUNNER
# =========================================================

def _run_strategies(lines: list[str]) -> list[dict]:
    """
    Run all three strategies on a block of lines and
    return the best combined result.

    Priority: tabular > inline > vertical
    (tabular and inline are more specific; vertical is
    the fallback for one-token-per-line formats).

    Results are deduplicated so each canonical name
    appears at most once.
    """
    tabular = _parse_tabular(lines)
    inline = _parse_inline(lines)
    vertical = _parse_vertical(lines)

    # Merge: prefer tabular, then inline, then vertical
    combined = tabular + inline + vertical
    return _deduplicate(combined)


# =========================================================
# LINE PREPROCESSOR
# =========================================================

def _clean_lines(raw_text: str) -> list[str]:
    """
    Normalise raw OCR text into a clean list of lines.

    - Strips page markers
    - Strips leading/trailing whitespace per line
    - Drops empty lines and known-skip lines
    - Normalises unicode dashes to ASCII hyphen
    """
    text = raw_text
    # Normalise dash variants
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    # Remove page markers (keep content)
    text = re.sub(r"---\s*PAGE\s+\d+\s*---", "", text, flags=re.IGNORECASE)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < _MIN_LINE_LEN:
            continue
        if _SKIP_RE.match(line):
            continue
        lines.append(line)

    return lines


# =========================================================
# PUBLIC API
# =========================================================

def parse_ocr_text(raw_text: str) -> list[dict]:
    """
    Parse raw OCR text from any supported blood report
    layout and return a list of canonical test dicts.

    Parameters
    ----------
    raw_text : str
        Raw text as produced by the OCR engine or
        extraction.pipeline (may contain --- PAGE N ---
        markers for multi-page documents).

    Returns
    -------
    list[dict]
        Each dict has keys:
            raw_name, canonical_name, value, unit,
            reference_raw, abnormal_flag, layout

    Notes
    -----
    - Multi-section reports are handled automatically.
    - Multi-page text is handled transparently.
    - Does NOT compute LOW / NORMAL / HIGH.
    - Does NOT add medical interpretation rules.
    """
    lines = _clean_lines(raw_text)
    sections = _split_sections(lines)

    all_results: list[dict] = []
    for _section_name, section_lines in sections:
        results = _run_strategies(section_lines)
        all_results.extend(results)

    return _deduplicate(all_results)
