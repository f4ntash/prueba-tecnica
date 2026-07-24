import argparse
import sys
from pathlib import Path

from src.classifier import DocumentType, classify_document
from src.extractor import EmptyPdfTextError, PdfExtractionError, extract_text
from src.parsers.authorization import AuthorizationParseError, MedicationAuthorizationParser
from src.parsers.prescription import DocumentParseError, PrescriptionParser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detecta el tipo de documento medico a partir de un PDF."
    )
    parser.add_argument("pdf_path", type=Path, help="Ruta al archivo PDF")
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        text = extract_text(args.pdf_path)
        document_type = classify_document(text)

        if document_type == DocumentType.PRESCRIPTION:
            medical_document = PrescriptionParser().parse(text)
            print(medical_document.model_dump_json(indent=2))
            return 0

        if document_type == DocumentType.MEDICATION_AUTHORIZATION:
            medical_document = MedicationAuthorizationParser().parse(text)
            print(medical_document.model_dump_json(indent=2))
            return 0

        print("Error: no se reconoce el tipo de documento.", file=sys.stderr)
        return 1
    except (
        FileNotFoundError,
        ValueError,
        EmptyPdfTextError,
        PdfExtractionError,
        AuthorizationParseError,
        DocumentParseError,
    ) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
