import argparse
import sys
from pathlib import Path

from src.classifier import classify_document
from src.extractor import EmptyPdfTextError, PdfExtractionError, extract_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detecta el tipo de documento medico a partir de un PDF."
    )
    parser.add_argument("pdf_path", type=Path, help="Ruta al archivo PDF")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = extract_text(args.pdf_path)
        document_type = classify_document(text)
    except (FileNotFoundError, ValueError, EmptyPdfTextError, PdfExtractionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Tipo detectado: {document_type.value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
