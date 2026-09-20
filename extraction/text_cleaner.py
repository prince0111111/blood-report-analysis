import re


def clean_pdf_text(raw_text: str) -> str:
    """
    Clean PDF-extracted blood report text while preserving
    medically relevant structure.
    """

    text = raw_text

    # 1. Remove page markers added by pdf_reader.py
    text = re.sub(
        r"---\s*PAGE\s+\d+\s*---",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 2. Remove the strange separator characters seen in the PDF
    text = re.sub(r"¾{3,}", "", text)

    # 3. Remove "Page X of Y"
    text = re.sub(
        r"Page\s+\d+\s+of\s+\d+",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 4. Remove trailing/leading spaces from each line
    lines = [line.strip() for line in text.splitlines()]

    # 5. Remove empty lines
    lines = [line for line in lines if line]

    # 6. Rebuild text
    cleaned_text = "\n".join(lines)

    return cleaned_text