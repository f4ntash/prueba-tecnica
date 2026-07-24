from pathlib import Path

import fitz


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be opened or read."""


class EmptyPdfTextError(PdfExtractionError):
    """Raised when a PDF has no extractable text."""


def extract_text(pdf_path: str | Path) -> str:
    """Extract native text from every page in a PDF file."""
    path = Path(pdf_path)

    if not path.exists():
        raise FileNotFoundError(f"El archivo no existe: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"El archivo debe tener extension .pdf: {path}")

    try:
        with fitz.open(path) as document:
            page_texts = [page.get_text("text") for page in document]
    except Exception as exc:
        raise PdfExtractionError(f"No se pudo leer el PDF: {path}") from exc

    text = "\n".join(page_texts).strip()
    if not text:
        raise EmptyPdfTextError(f"El PDF no contiene texto extraible: {path}")

    return text
