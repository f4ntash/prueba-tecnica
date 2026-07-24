from pathlib import Path

import fitz
import pytest

from src.classifier import DocumentType, classify_document
from src.extractor import extract_text
from src.parsers.authorization import AuthorizationParseError, MedicationAuthorizationParser


def parse_authorization(text: str):
    return MedicationAuthorizationParser().parse(text)


def complete_authorization_text() -> str:
    return """
    AUTORIZACION DE
    PRESTACIONES AUTORIZADAS
    MEDICAMENTOS
    Nro. Autorizacion: ZX123
    Fecha de Autorizacion: 10/05/2026
    Fecha de Auditoria: 11/05/2026
    AFILIADO: 9988/77 Valeria Costa IVA EXENTO
    PLAN: BASE EDAD: 45 anos
    EMP.: 123
    CODIGO
    NOMBRE COMERCIAL
    MONODROGA
    COBERT.
    CANT. AUT.
    7 - 123456
    REMEDIN 10 mg caps. x 20
    DROGAX
    70 %
    3
    MEDICO SOLICITANTE: Lucia Perez
    DIAGNOSTICO: 8421 - Tratamiento controlado
    DNI Afiliado:
    __ __ __ __ __ __ __ __
    AUTORIZACION VALIDA HASTA EL: 25/05/2026
    Fecha de Emision: 12/05/2026
    """


def test_parse_complete_authorization() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.document_type == DocumentType.MEDICATION_AUTHORIZATION
    assert document.patient.name == "Valeria Costa"
    assert document.patient.dni is None
    assert document.patient.cuil is None
    assert document.professional is not None
    assert document.professional.name == "Lucia Perez"
    assert document.professional.license is None
    assert document.diagnosis == "Tratamiento controlado"
    assert document.issued_at is not None
    assert document.issued_at.isoformat() == "2026-05-10"
    assert document.valid_until is not None
    assert document.valid_until.isoformat() == "2026-05-25"
    assert document.warnings == []

    medication = document.medications[0]
    assert medication.name == "REMEDIN"
    assert medication.active_ingredient == "DROGAX"
    assert medication.dosage == "10 mg"
    assert medication.presentation == "caps. x 20"
    assert medication.coverage_percentage == 70.0
    assert medication.quantity == 3.0
    assert medication.instructions is None


def test_parse_authorization_with_case_and_accents() -> None:
    text = complete_authorization_text().replace("AUTORIZACION", "Autorización").lower()

    document = parse_authorization(text)

    assert document.document_type == DocumentType.MEDICATION_AUTHORIZATION
    assert document.patient.name == "valeria costa"


def test_patient_name_is_delimited_by_structural_markers() -> None:
    text = complete_authorization_text().replace(
        "AFILIADO: 9988/77 Valeria Costa IVA EXENTO",
        "AFILIADO: 1122/33 Martina Ruiz OBLIG. IVA EXENTO",
    )

    document = parse_authorization(text)

    assert document.patient.name == "Martina Ruiz"


def test_ambiguous_patient_adds_warning_and_returns_none() -> None:
    text = complete_authorization_text().replace(
        "AFILIADO: 9988/77 Valeria Costa IVA EXENTO",
        "AFILIADO: 1122/33 Martina Ruiz",
    )

    document = parse_authorization(text)

    assert document.patient.name is None
    assert "No se pudo aislar el nombre del afiliado con confianza." in document.warnings


def test_empty_dni_stays_none() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.patient.dni is None


def test_medication_row_fields_are_reconstructed() -> None:
    document = parse_authorization(complete_authorization_text())
    medication = document.medications[0]

    assert medication.name == "REMEDIN"
    assert medication.active_ingredient == "DROGAX"
    assert medication.dosage == "10 mg"
    assert medication.presentation == "caps. x 20"
    assert medication.coverage_percentage == 70.0
    assert medication.quantity == 3.0


def test_invalid_percentage_adds_warning() -> None:
    text = complete_authorization_text().replace("70 %", "setenta %")

    document = parse_authorization(text)

    assert document.medications == []
    assert "Cobertura tiene formato invalido: setenta %." in document.warnings


def test_invalid_quantity_adds_warning() -> None:
    text = complete_authorization_text().replace("\n    3\n", "\n    tres\n")

    document = parse_authorization(text)

    assert document.medications[0].quantity is None
    assert "Cantidad autorizada tiene formato invalido: tres." in document.warnings


def test_authorization_date_is_used_and_audit_date_is_ignored() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.issued_at is not None
    assert document.issued_at.isoformat() == "2026-05-10"


def test_valid_until_date_is_used() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.valid_until is not None
    assert document.valid_until.isoformat() == "2026-05-25"


def test_professional_and_diagnosis_are_extracted() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.professional is not None
    assert document.professional.name == "Lucia Perez"
    assert document.diagnosis == "Tratamiento controlado"


def test_professional_name_trailing_period_is_removed() -> None:
    text = complete_authorization_text().replace(
        "MEDICO SOLICITANTE: Lucia Perez",
        "MEDICO SOLICITANTE: Pedro Gomez.",
    )

    document = parse_authorization(text)

    assert document.professional is not None
    assert document.professional.name == "Pedro Gomez"


def test_professional_name_internal_initial_is_preserved() -> None:
    text = complete_authorization_text().replace(
        "MEDICO SOLICITANTE: Lucia Perez",
        "MEDICO SOLICITANTE: JUAN P. PEREZ.",
    )

    document = parse_authorization(text)

    assert document.professional is not None
    assert document.professional.name == "JUAN P. PEREZ"


def test_professional_name_without_trailing_punctuation_is_unchanged() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.professional is not None
    assert document.professional.name == "Lucia Perez"


def test_optional_professional_absent() -> None:
    text = complete_authorization_text().replace("MEDICO SOLICITANTE: Lucia Perez", "")

    document = parse_authorization(text)

    assert document.professional is None


def test_two_medications_are_reconstructed() -> None:
    text = complete_authorization_text().replace(
        "7 - 123456\n    REMEDIN 10 mg caps. x 20\n    DROGAX\n    70 %\n    3",
        "7 - 123456\n    REMEDIN 10 mg caps. x 20\n    DROGAX\n    70 %\n    3\n"
        "    8 - 555999\n    CURAX 5 mg comp. x 15\n    SUSTANCIAX\n    20 %\n    1.5",
    )

    document = parse_authorization(text)

    assert len(document.medications) == 2
    assert document.medications[0].name == "REMEDIN"
    assert document.medications[1].name == "CURAX"
    assert document.medications[1].quantity == 1.5


def test_split_presentation_lines_are_joined_before_monodrug() -> None:
    text = complete_authorization_text().replace(
        "REMEDIN 10 mg caps. x 20\n    DROGAX",
        "REMEDIN 10 mg\n    caps. x 20\n    DROGAX",
    )

    document = parse_authorization(text)

    assert document.medications[0].name == "REMEDIN"
    assert document.medications[0].dosage == "10 mg"
    assert document.medications[0].presentation == "caps. x 20"
    assert document.medications[0].active_ingredient == "DROGAX"


def test_blank_lines_inside_table_do_not_break_reconstruction() -> None:
    text = complete_authorization_text().replace(
        "REMEDIN 10 mg caps. x 20\n    DROGAX",
        "REMEDIN 10 mg caps. x 20\n\n\n    DROGAX",
    )

    document = parse_authorization(text)

    assert document.medications[0].name == "REMEDIN"
    assert document.medications[0].active_ingredient == "DROGAX"


def test_incomplete_row_warns_and_next_valid_row_is_parsed() -> None:
    text = complete_authorization_text().replace(
        "7 - 123456\n    REMEDIN 10 mg caps. x 20\n    DROGAX\n    70 %\n    3",
        "7 - 123456\n    REMEDIN 10 mg caps. x 20\n"
        "    8 - 555999\n    CURAX 5 mg comp. x 15\n    SUSTANCIAX\n    20 %\n    1",
    )

    document = parse_authorization(text)

    assert len(document.medications) == 1
    assert document.medications[0].name == "CURAX"
    assert "No se pudo reconstruir una fila completa de medicamento." in document.warnings


def test_repeated_headers_inside_table_are_ignored() -> None:
    text = complete_authorization_text().replace(
        "7 - 123456",
        "CODIGO\n    NOMBRE COMERCIAL\n    MONODROGA\n    COBERT.\n    CANT. AUT.\n    7 - 123456",
    )

    document = parse_authorization(text)

    assert len(document.medications) == 1
    assert document.medications[0].name == "REMEDIN"


def test_quantity_does_not_use_product_code_or_percentage() -> None:
    document = parse_authorization(complete_authorization_text())

    assert document.medications[0].quantity == 3.0
    assert document.medications[0].quantity != 123456
    assert document.medications[0].quantity != document.medications[0].coverage_percentage


def test_coverage_zero_and_one_hundred_are_valid() -> None:
    zero_text = complete_authorization_text().replace("70 %", "0 %")
    hundred_text = complete_authorization_text().replace("70 %", "100 %")

    zero_document = parse_authorization(zero_text)
    hundred_document = parse_authorization(hundred_text)

    assert zero_document.medications[0].coverage_percentage == 0.0
    assert hundred_document.medications[0].coverage_percentage == 100.0


def test_coverage_over_one_hundred_is_invalid() -> None:
    text = complete_authorization_text().replace("70 %", "150 %")

    document = parse_authorization(text)

    assert document.medications[0].coverage_percentage is None
    assert "Cobertura fuera de rango: 150 %." in document.warnings


def test_rejects_text_that_is_not_authorization() -> None:
    with pytest.raises(AuthorizationParseError):
        parse_authorization("Receta comun sin tabla de autorizacion.")


def test_integration_with_temporary_pdf(tmp_path: Path) -> None:
    pdf_file = tmp_path / "authorization.pdf"
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((72, 72), complete_authorization_text())
        pdf.save(pdf_file)

    text = extract_text(pdf_file)
    document_type = classify_document(text)
    document = parse_authorization(text)

    assert document_type == DocumentType.MEDICATION_AUTHORIZATION
    assert document.patient.name == "Valeria Costa"
    assert document.medications[0].name == "REMEDIN"
