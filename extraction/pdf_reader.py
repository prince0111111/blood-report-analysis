from pathlib import Path
import fitz


def extract_pdf_text(pdf_path: str) -> str:
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are currently supported.")

    document = fitz.open(path)

    pages = []

    for page_number, page in enumerate(document):
        text = page.get_text("text")

        pages.append(
            f"\n--- PAGE {page_number + 1} ---\n{text}"
        )

    document.close()

    full_text = "\n".join(pages)

    if not full_text.strip():
        raise ValueError(
            "No embedded text detected. "
            "This may be a scanned/image-based PDF."
        )

    return full_text