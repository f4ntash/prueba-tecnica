from src.classifier import DocumentType, classify_document, normalize_text


def test_detects_prescription_with_receta() -> None:
    assert classify_document("Datos del paciente\nReceta: ibuprofeno") == DocumentType.PRESCRIPTION


def test_detects_prescription_with_rp() -> None:
    assert classify_document("Rp/.\nAmoxicilina 500 mg") == DocumentType.PRESCRIPTION


def test_detects_authorization_without_accent() -> None:
    text = "AUTORIZACION DE MEDICAMENTOS\nPaciente: Juan Perez"
    assert classify_document(text) == DocumentType.MEDICATION_AUTHORIZATION


def test_detects_authorization_with_accent() -> None:
    text = "AUTORIZACION DE MEDICAMENTOS".replace("AUTORIZACION", "AUTORIZACIÓN")
    assert classify_document(text) == DocumentType.MEDICATION_AUTHORIZATION


def test_ignores_case() -> None:
    text = "autorizacion de medicamentos"
    assert classify_document(text) == DocumentType.MEDICATION_AUTHORIZATION


def test_tolerates_repeated_spaces() -> None:
    text = "AUTORIZACION     DE      MEDICAMENTOS"
    assert classify_document(text) == DocumentType.MEDICATION_AUTHORIZATION


def test_detects_authorization_when_title_is_split_by_layout_text() -> None:
    text = "AUTORIZACION DE\nNro. Autorizacion: 123\nPRESTACIONES AUTORIZADAS\nMEDICAMENTOS"
    assert classify_document(text) == DocumentType.MEDICATION_AUTHORIZATION


def test_returns_unknown_for_unrecognized_text() -> None:
    assert classify_document("Informe sin palabras clave") == DocumentType.UNKNOWN


def test_empty_text_returns_unknown() -> None:
    assert classify_document("") == DocumentType.UNKNOWN


def test_normalize_text_removes_accents_and_extra_spaces() -> None:
    assert normalize_text("  Autorización   de\nMedicamentos ") == "AUTORIZACION DE MEDICAMENTOS"
