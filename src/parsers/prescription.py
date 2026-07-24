from datetime import date, datetime
import re

from src.classifier import DocumentType, normalize_text
from src.models import MedicalDocument, Medication, Patient, Professional
from src.parsers.base import DocumentParser


class DocumentParseError(Exception):
    """Raised when extracted text cannot be parsed as the expected document."""


_KNOWN_LABELS = (
    "PACIENTE:",
    "DNI:",
    "CUIL:",
    "SEXO:",
    "F.NACIMIENTO:",
    "DIAGNOSTICO:",
    "INDICACIONES:",
    "EMITIDA:",
    "RECETA:",
    "M.P.",
    "RP/.",
    "FECHA DE VIGENCIA:",
)

_MEDICATION_STOP_LABELS = (
    "DIAGNOSTICO:",
    "INDICACIONES:",
    "EMITIDA:",
    "FECHA DE VIGENCIA:",
    "CENTRO ASISTENCIAL",
    "BENEFICIARIO:",
)

KNOWN_TEXT_REPLACEMENTS = {
    "d\ufffda": "día",
}


class PrescriptionParser(DocumentParser):
    def parse(self, text: str) -> MedicalDocument:
        lines = _clean_lines(text)
        normalized_text = normalize_text(text)
        warnings: list[str] = []

        if not _looks_like_prescription(normalized_text):
            raise DocumentParseError("El texto no contiene senales suficientes de una receta.")

        patient = _parse_patient(lines, warnings)
        professional = _parse_professional(lines, warnings)
        medication = _parse_medication(lines, warnings)

        document = MedicalDocument(
            document_type=DocumentType.PRESCRIPTION,
            patient=patient,
            professional=professional,
            medications=[medication] if medication else [],
            diagnosis=_extract_text_field(lines, "Diagnostico:", "Diagnostico", warnings),
            issued_at=_parse_date_field(
                _find_label_value(lines, "Emitida:"), "Emitida", warnings
            ),
            valid_until=None,
            warnings=warnings,
        )

        _add_required_field_warnings(document, warnings)
        document.warnings = warnings
        return document


def _parse_patient(lines: list[str], warnings: list[str]) -> Patient:
    return Patient(
        name=_extract_text_field(lines, "Paciente:", "Paciente", warnings),
        dni=_extract_text_field(lines, "DNI:", "DNI", warnings),
        cuil=_parse_cuil(_find_label_value(lines, "CUIL:"), warnings),
        birth_date=_parse_date_field(
            _find_label_value(lines, "F.Nacimiento:"), "F.Nacimiento", warnings
        ),
        gender=_extract_text_field(lines, "Sexo:", "Sexo", warnings),
    )


def _parse_professional(lines: list[str], warnings: list[str]) -> Professional:
    name = _find_professional_name(lines)
    name = _normalize_text_field("Profesional", name, warnings)

    return Professional(
        name=name,
        license=_extract_text_field(lines, "M.P.", "M.P.", warnings),
    )


def _parse_medication(lines: list[str], warnings: list[str]) -> Medication | None:
    block = _medication_block(lines)
    if not block:
        _add_warning(warnings, "No se encontro el bloque de medicamento debajo de Rp/.")
        return None

    quantity = _extract_quantity(block, warnings)
    medication_lines = _remove_quantity_and_brand_lines(block)

    name = medication_lines[0] if medication_lines else None
    dosage, presentation = _split_dosage_and_presentation(
        medication_lines[1] if len(medication_lines) > 1 else None
    )
    instructions = _extract_text_field(lines, "Indicaciones:", "Indicaciones", warnings)

    name = _normalize_text_field("Medicamento", name, warnings)
    dosage = _normalize_text_field("Dosis", dosage, warnings)
    presentation = _normalize_text_field("Presentacion", presentation, warnings)

    return Medication(
        name=name,
        dosage=dosage,
        presentation=presentation,
        quantity=quantity,
        instructions=instructions,
    )


def _clean_lines(text: str) -> list[str]:
    return [_clean_spaces(line) for line in text.splitlines() if _clean_spaces(line)]


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _looks_like_prescription(normalized_text: str) -> bool:
    has_prescription_marker = "RECETA:" in normalized_text or "RP/." in normalized_text
    has_medical_context = "PACIENTE:" in normalized_text or "M.P." in normalized_text
    return has_prescription_marker and has_medical_context


def _extract_text_field(
    lines: list[str], label: str, field_name: str, warnings: list[str]
) -> str | None:
    value = _find_label_value(lines, label)
    return _normalize_text_field(field_name, value, warnings)


def _find_label_value(lines: list[str], label: str) -> str | None:
    normalized_label = normalize_text(label)

    for index, line in enumerate(lines):
        normalized_line = normalize_text(line)
        if not normalized_line.startswith(normalized_label):
            continue

        value = line[len(label) :].strip()
        if value:
            return value

        return _next_value_line(lines, index + 1)

    return None


def _next_value_line(lines: list[str], start_index: int) -> str | None:
    for line in lines[start_index:]:
        if _is_known_label(line):
            return None
        return line
    return None


def _is_known_label(line: str) -> bool:
    normalized_line = normalize_text(line)
    return any(normalized_line.startswith(label) for label in _KNOWN_LABELS)


def _parse_date_field(value: str | None, field_name: str, warnings: list[str]) -> date | None:
    if not value:
        return None

    match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", value)
    if not match:
        _add_warning(warnings, f"{field_name} esta presente pero no tiene formato DD/MM/YYYY.")
        return None

    try:
        return datetime.strptime(match.group(1), "%d/%m/%Y").date()
    except ValueError:
        _add_warning(warnings, f"{field_name} tiene una fecha invalida: {match.group(1)}.")
        return None


def _parse_cuil(value: str | None, warnings: list[str]) -> str | None:
    if not value:
        return None

    value = _normalize_text_field("CUIL", value, warnings)
    cleaned_cuil = re.sub(r"[\s-]+", "", value)
    if re.fullmatch(r"\d{11}", cleaned_cuil):
        return cleaned_cuil

    _add_warning(warnings, "CUIL esta presente pero tiene formato invalido.")
    return None


def _find_professional_name(lines: list[str]) -> str | None:
    for line in lines:
        match = re.match(r"^(?:DR/A\.?|DRA\.?|DR\.?)\s+(.+)$", line, flags=re.IGNORECASE)
        if match:
            return _clean_spaces(match.group(1))
    return None


def _medication_block(lines: list[str]) -> list[str]:
    start_index = _find_line_index(lines, "Rp/.")
    if start_index is None:
        return []

    block: list[str] = []
    for line in lines[start_index + 1 :]:
        normalized_line = normalize_text(line)
        if any(normalized_line.startswith(label) for label in _MEDICATION_STOP_LABELS):
            break
        block.append(line)
    return block


def _find_line_index(lines: list[str], marker: str) -> int | None:
    normalized_marker = normalize_text(marker)
    for index, line in enumerate(lines):
        if normalize_text(line).startswith(normalized_marker):
            return index
    return None


def _extract_quantity(block: list[str], warnings: list[str]) -> float | None:
    envases_index = _find_line_index(block, "Envases")
    if envases_index is None or envases_index + 1 >= len(block):
        return None

    raw_quantity = block[envases_index + 1].replace(",", ".")
    try:
        return float(raw_quantity)
    except ValueError:
        _add_warning(
            warnings,
            f"Envases esta presente pero la cantidad es invalida: {block[envases_index + 1]}.",
        )
        return None


def _remove_quantity_and_brand_lines(block: list[str]) -> list[str]:
    result: list[str] = []
    skip_next_quantity = False

    for line in block:
        normalized_line = normalize_text(line)
        if normalized_line == "ENVASES":
            skip_next_quantity = True
            continue
        if skip_next_quantity:
            skip_next_quantity = False
            continue
        if normalized_line.startswith("MARCA SUGERIDA:"):
            continue
        result.append(line)

    return result


def _split_dosage_and_presentation(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None

    match = re.match(
        r"^(\d+(?:[.,]\d+)?\s*(?:MG|MCG|G|ML|UI|U|%)\b)\s*(.*)$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return None, value

    dosage = _clean_spaces(match.group(1).replace(",", "."))
    presentation = _clean_spaces(match.group(2)) or None
    return dosage, presentation


def _add_required_field_warnings(document: MedicalDocument, warnings: list[str]) -> None:
    if not document.patient.name:
        _add_warning(warnings, "No se pudo extraer el nombre del paciente.")
    if not document.patient.dni:
        _add_warning(warnings, "No se pudo extraer el DNI del paciente.")
    if not document.medications:
        _add_warning(warnings, "No se pudo extraer ningun medicamento.")
    elif not document.medications[0].name:
        _add_warning(warnings, "No se pudo extraer el nombre del medicamento.")


def normalize_extracted_text(value: str) -> tuple[str, bool]:
    normalized_value = value
    for damaged_text, replacement in KNOWN_TEXT_REPLACEMENTS.items():
        normalized_value = normalized_value.replace(damaged_text, replacement)

    return normalized_value, normalized_value != value


def _normalize_text_field(
    field_name: str, value: str | None, warnings: list[str]
) -> str | None:
    if value is None:
        return None

    normalized_value, was_corrected = normalize_extracted_text(value)
    if was_corrected:
        _add_warning(
            warnings,
            f"{field_name} contenia caracteres danados y fue normalizada usando una correccion conocida.",
        )
        return normalized_value

    if "\ufffd" in normalized_value:
        _add_warning(
            warnings,
            f"{field_name} puede contener caracteres danados durante la extraccion.",
        )

    return normalized_value


def _add_warning(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)
