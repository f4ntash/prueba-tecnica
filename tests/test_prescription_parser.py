from pathlib import Path

import fitz
import pytest

from src.classifier import DocumentType, classify_document
from src.extractor import extract_text
from src.parsers.prescription import (
    DocumentParseError,
    PrescriptionParser,
    normalize_extracted_text,
)


def parse_prescription(text: str):
    return PrescriptionParser().parse(text)


def complete_prescription_text() -> str:
    return """
    Dr/a. Camila Robles
    M.P. 92817
    Receta: 555
    Paciente:
    Tomas Alvarez
    CUIL: 20-12345678-9
    DNI: 12345678
    Sexo: Masculino
    F.Nacimiento: 05/03/1981
    Rp/.
    Envases
    2
    Losartan
    50 MG Comprimidos x 30
    Marca sugerida: CARDIOPLAN 50
    Diagnostico: Hipertension arterial
    Indicaciones: Tomar 1 comprimido por la manana
    Emitida: 14/07/2026
    Fecha de vigencia: 14/08/2026
    """


def test_parse_complete_prescription() -> None:
    document = parse_prescription(complete_prescription_text())

    assert document.document_type == DocumentType.PRESCRIPTION
    assert document.patient.name == "Tomas Alvarez"
    assert document.patient.dni == "12345678"
    assert document.patient.cuil == "20123456789"
    assert document.patient.gender == "Masculino"
    assert document.patient.birth_date.isoformat() == "1981-03-05"
    assert document.professional is not None
    assert document.professional.name == "Camila Robles"
    assert document.professional.license == "92817"
    assert document.diagnosis == "Hipertension arterial"
    assert document.issued_at is not None
    assert document.issued_at.isoformat() == "2026-07-14"
    assert document.valid_until is None
    assert document.warnings == []

    medication = document.medications[0]
    assert medication.name == "Losartan"
    assert medication.quantity == 2.0
    assert medication.dosage == "50 MG"
    assert medication.presentation == "Comprimidos x 30"
    assert medication.instructions == "Tomar 1 comprimido por la manana"


def test_parse_prescription_with_different_case() -> None:
    text = complete_prescription_text().lower()

    document = parse_prescription(text)

    assert document.patient.name == "tomas alvarez"
    assert document.medications[0].name == "losartan"


def test_parse_prescription_with_repeated_spaces() -> None:
    text = complete_prescription_text().replace("DNI:", "DNI:      ")

    document = parse_prescription(text)

    assert document.patient.dni == "12345678"


def test_valid_cuil_is_cleaned_and_kept() -> None:
    document = parse_prescription(complete_prescription_text())

    assert document.patient.cuil == "20123456789"


def test_invalid_cuil_returns_none_and_adds_warning() -> None:
    text = complete_prescription_text().replace("CUIL: 20-12345678-9", "CUIL: 123")

    document = parse_prescription(text)

    assert document.patient.cuil is None
    assert "CUIL esta presente pero tiene formato invalido." in document.warnings


def test_absent_cuil_stays_none_without_invalid_format_warning() -> None:
    text = complete_prescription_text().replace("CUIL: 20-12345678-9", "")

    document = parse_prescription(text)

    assert document.patient.cuil is None
    assert "CUIL esta presente pero tiene formato invalido." not in document.warnings


def test_professional_validity_date_is_not_document_valid_until() -> None:
    text = complete_prescription_text().replace(
        "M.P. 92817",
        "M.P. 92817\n    Licencia Sanitaria Federal: 777\n    Fecha de vigencia: 30/09/2026",
    )

    document = parse_prescription(text)

    assert document.valid_until is None


def test_invalid_date_adds_warning_and_returns_none() -> None:
    text = complete_prescription_text().replace("F.Nacimiento: 05/03/1981", "F.Nacimiento: 31/02/1981")

    document = parse_prescription(text)

    assert document.patient.birth_date is None
    assert "F.Nacimiento tiene una fecha invalida: 31/02/1981." in document.warnings


def test_missing_dni_adds_warning() -> None:
    text = complete_prescription_text().replace("DNI: 12345678", "")

    document = parse_prescription(text)

    assert document.patient.dni is None
    assert "No se pudo extraer el DNI del paciente." in document.warnings


def test_multiline_medication_block() -> None:
    text = complete_prescription_text().replace(
        "Losartan\n    50 MG Comprimidos x 30",
        "Metformina\n    850 MG Comprimidos recubiertos x 60",
    )

    document = parse_prescription(text)

    assert document.medications[0].name == "Metformina"
    assert document.medications[0].dosage == "850 MG"
    assert document.medications[0].presentation == "Comprimidos recubiertos x 60"


def test_rejects_text_that_is_not_a_prescription() -> None:
    with pytest.raises(DocumentParseError):
        parse_prescription("Informe clinico sin marcadores de receta.")


def test_suggested_brand_is_not_used_as_main_medication_name() -> None:
    document = parse_prescription(complete_prescription_text())

    assert document.medications[0].name == "Losartan"
    assert "CARDIOPLAN" not in document.medications[0].name


def test_known_damaged_text_is_normalized_and_warned() -> None:
    text = complete_prescription_text().replace(
        "Indicaciones: Tomar 1 comprimido por la manana",
        "Indicaciones: 1/d\ufffda",
    )

    document = parse_prescription(text)

    assert document.medications[0].instructions == "1/día"
    assert (
        "Indicaciones contenia caracteres danados y fue normalizada usando una correccion conocida."
        in document.warnings
    )


def test_unknown_damaged_text_is_preserved_and_warned() -> None:
    text = complete_prescription_text().replace(
        "Indicaciones: Tomar 1 comprimido por la manana",
        "Indicaciones: abc\ufffdxyz",
    )

    document = parse_prescription(text)

    assert document.medications[0].instructions == "abc\ufffdxyz"
    assert (
        "Indicaciones puede contener caracteres danados durante la extraccion."
        in document.warnings
    )


def test_normal_text_is_not_changed_or_warned() -> None:
    document = parse_prescription(complete_prescription_text())

    assert document.medications[0].instructions == "Tomar 1 comprimido por la manana"
    assert not any("Indicaciones" in warning for warning in document.warnings)


def test_normalize_extracted_text_only_applies_known_replacements() -> None:
    normalized_value, was_corrected = normalize_extracted_text("Paciente d\ufffda")
    unknown_value, unknown_was_corrected = normalize_extracted_text("abc\ufffdxyz")

    assert normalized_value == "Paciente día"
    assert was_corrected is True
    assert unknown_value == "abc\ufffdxyz"
    assert unknown_was_corrected is False


def test_damaged_text_in_one_field_does_not_modify_labels_or_other_fields() -> None:
    text = complete_prescription_text().replace("Tomas Alvarez", "Ana d\ufffda")

    document = parse_prescription(text)

    assert document.patient.name == "Ana día"
    assert document.patient.dni == "12345678"
    assert document.medications[0].instructions == "Tomar 1 comprimido por la manana"


def test_integration_with_temporary_pdf(tmp_path: Path) -> None:
    pdf_file = tmp_path / "prescription.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), complete_prescription_text())
        pdf.save(pdf_file)

    text = extract_text(pdf_file)
    document_type = classify_document(text)
    document = parse_prescription(text)

    assert document_type == DocumentType.PRESCRIPTION
    assert document.patient.name == "Tomas Alvarez"
    assert document.medications[0].name == "Losartan"
