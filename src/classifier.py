from enum import StrEnum
import re
import unicodedata


class DocumentType(StrEnum):
    """Supported document categories."""

    PRESCRIPTION = "prescription"
    MEDICATION_AUTHORIZATION = "medication_authorization"
    UNKNOWN = "unknown"


def normalize_text(text: str) -> str:
    """Normalize text for deterministic keyword-based matching."""
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    upper_text = without_accents.upper()
    return re.sub(r"\s+", " ", upper_text).strip()


def classify_document(text: str) -> DocumentType:
    """Classify a medical document from its extracted text."""
    normalized_text = normalize_text(text)

    if not normalized_text:
        return DocumentType.UNKNOWN

    if "AUTORIZACION DE MEDICAMENTOS" in normalized_text or (
        "AUTORIZACION DE" in normalized_text and "MEDICAMENTOS" in normalized_text
    ):
        return DocumentType.MEDICATION_AUTHORIZATION

    if "RECETA:" in normalized_text or "RP/." in normalized_text:
        return DocumentType.PRESCRIPTION

    return DocumentType.UNKNOWN
