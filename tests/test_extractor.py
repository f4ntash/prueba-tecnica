from pathlib import Path

import fitz
import pytest

from src.extractor import EmptyPdfTextError, extract_text


def create_pdf(path: Path, text: str | None = None) -> None:
    with fitz.open() as document:
        page = document.new_page()
        if text is not None:
            page.insert_text((72, 72), text)
        document.save(path)


def test_file_does_not_exist(tmp_path: Path) -> None:
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError):
        extract_text(missing_pdf)


def test_invalid_extension(tmp_path: Path) -> None:
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("not a pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="extension .pdf"):
        extract_text(txt_file)


def test_valid_pdf_with_text(tmp_path: Path) -> None:
    pdf_file = tmp_path / "document.pdf"
    create_pdf(pdf_file, "Receta: paracetamol")

    assert "Receta: paracetamol" in extract_text(pdf_file)


def test_valid_pdf_without_text(tmp_path: Path) -> None:
    pdf_file = tmp_path / "empty.pdf"
    create_pdf(pdf_file)

    with pytest.raises(EmptyPdfTextError):
        extract_text(pdf_file)
