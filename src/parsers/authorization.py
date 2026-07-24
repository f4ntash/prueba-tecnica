from datetime import date, datetime
import re

from src.classifier import DocumentType, normalize_text
from src.models import MedicalDocument, Medication, Patient, Professional
from src.parsers.base import DocumentParser
from src.parsers.prescription import normalize_extracted_text


class AuthorizationParseError(Exception):
    """Raised when text cannot be parsed as a medication authorization."""


_TABLE_HEADERS = ("NOMBRE COMERCIAL", "MONODROGA", "COBERT.", "CANT. AUT.")
_TABLE_END_MARKERS = ("MEDICO SOLICITANTE:", "DIAGNOSTICO:", "DNI AFILIADO:")


class MedicationAuthorizationParser(DocumentParser):
    def parse(self, text: str) -> MedicalDocument:
        lines = _clean_lines(text)
        normalized_text = normalize_text(text)
        warnings: list[str] = []

        if not _looks_like_authorization(normalized_text):
            raise AuthorizationParseError(
                "El texto no contiene senales suficientes de una autorizacion de medicamentos."
            )

        patient = _parse_patient(lines, warnings)
        professional = _parse_professional(lines, warnings)
        medications = _parse_medications(lines, warnings)

        document = MedicalDocument(
            document_type=DocumentType.MEDICATION_AUTHORIZATION,
            patient=patient,
            professional=professional,
            medications=medications,
            diagnosis=_parse_diagnosis(lines, warnings),
            issued_at=_parse_date_field(
                _find_label_value(lines, "Fecha de Autorizaci"),
                "Fecha de Autorizacion",
                warnings,
            )
            or _parse_date_field(
                _find_label_value(lines, "Fecha de Emisi"),
                "Fecha de Emision",
                warnings,
            ),
            valid_until=_parse_date_field(
                _find_valid_until_value(lines),
                "AUTORIZACION VALIDA HASTA EL",
                warnings,
            ),
            warnings=warnings,
        )

        _add_required_field_warnings(document, warnings)
        document.warnings = warnings
        return document


def _clean_lines(text: str) -> list[str]:
    return [_clean_spaces(line) for line in text.splitlines() if _clean_spaces(line)]


def _clean_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _looks_like_authorization(normalized_text: str) -> bool:
    has_title = "AUTORIZACION" in normalized_text and "MEDICAMENTOS" in normalized_text
    has_admin_data = "AUTORIZACI" in normalized_text
    has_table = any(header in normalized_text for header in _TABLE_HEADERS)
    return has_title and has_admin_data and has_table


def _parse_patient(lines: list[str], warnings: list[str]) -> Patient:
    afiliado_line = _find_line(lines, "AFILIADO:")
    name = _parse_affiliate_name(afiliado_line, warnings)
    dni = _parse_affiliate_dni(lines)

    return Patient(name=name, dni=dni)


def _parse_affiliate_name(line: str | None, warnings: list[str]) -> str | None:
    if not line:
        _add_warning(warnings, "No se encontro la linea AFILIADO para extraer el paciente.")
        return None

    value = _value_after_colon(line)
    value = re.sub(r"^\S+\s+", "", value).strip()
    delimiter_match = re.search(r"\b(?:OBLIG\.?|IVA|PLAN:|EDAD:|EMP\.:)\b", value, flags=re.IGNORECASE)
    if not delimiter_match:
        _add_warning(warnings, "No se pudo aislar el nombre del afiliado con confianza.")
        return None

    name = _clean_spaces(value[: delimiter_match.start()])
    if not name:
        _add_warning(warnings, "No se pudo aislar el nombre del afiliado con confianza.")
        return None

    return _normalize_text_field("Afiliado", name, warnings)


def _parse_affiliate_dni(lines: list[str]) -> str | None:
    index = _find_line_index(lines, "DNI Afiliado:")
    if index is None:
        return None

    same_line_value = _value_after_colon(lines[index])
    if _is_valid_dni(same_line_value):
        return same_line_value

    if index + 1 < len(lines) and _is_valid_dni(lines[index + 1]):
        return lines[index + 1]

    return None


def _is_valid_dni(value: str) -> bool:
    return bool(re.fullmatch(r"\d{7,8}", value.strip()))


def _parse_professional(lines: list[str], warnings: list[str]) -> Professional | None:
    name = _find_label_value(lines, "MEDICO SOLICITANTE:")
    name = _normalize_text_field("Medico solicitante", name, warnings)
    if not name:
        return None
    return Professional(name=_strip_final_name_punctuation(name))


def _parse_diagnosis(lines: list[str], warnings: list[str]) -> str | None:
    value = _find_label_value(lines, "DIAGNOSTICO:")
    if not value:
        return None

    match = re.match(r"^\d+\s*-\s*(.+)$", value)
    diagnosis = match.group(1) if match else value
    return _normalize_text_field("Diagnostico", _clean_spaces(diagnosis), warnings)


def _parse_medications(lines: list[str], warnings: list[str]) -> list[Medication]:
    block = _table_data_block(lines)
    if not block:
        _add_warning(warnings, "No se pudo ubicar el bloque tabular de medicamentos.")
        return []

    rows = _reconstruct_medication_rows(block, warnings)
    medications = [_medication_from_row(row, warnings) for row in rows]
    return [medication for medication in medications if medication is not None]


def _table_data_block(lines: list[str]) -> list[str]:
    start_index = _find_line_index(lines, "CANT. AUT.")
    if start_index is None:
        return []

    block: list[str] = []
    for line in lines[start_index + 1 :]:
        normalized_line = normalize_text(line)
        if any(normalized_line.startswith(marker) for marker in _TABLE_END_MARKERS):
            break
        if _is_table_header(line):
            continue
        block.append(line)
    return block


def _reconstruct_medication_rows(block: list[str], warnings: list[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    current_row: list[str] = []

    for line in block:
        if _is_product_code(line) and current_row:
            rows.append(current_row)
            current_row = [line]
        else:
            current_row.append(line)

    if current_row:
        rows.append(current_row)

    valid_rows: list[list[str]] = []
    for row in rows:
        if len(row) < 5:
            _add_warning(warnings, "No se pudo reconstruir una fila completa de medicamento.")
            continue
        valid_rows.append(row)

    return valid_rows


def _medication_from_row(row: list[str], warnings: list[str]) -> Medication | None:
    code = row[0]
    if not _is_product_code(code):
        _add_warning(warnings, "No se pudo reconstruir una fila completa de medicamento.")
        return None

    coverage_index = _find_first_index(row, _is_percentage)
    if coverage_index is None:
        invalid_coverage = _find_invalid_coverage(row)
        if invalid_coverage:
            _add_warning(warnings, f"Cobertura tiene formato invalido: {invalid_coverage}.")
        else:
            _add_warning(warnings, "No se pudo identificar la cobertura del medicamento.")
        return None

    if coverage_index + 1 >= len(row):
        _add_warning(warnings, "No se pudo identificar la cantidad autorizada del medicamento.")
        return None

    commercial_lines = row[1 : coverage_index - 1]
    active_ingredient = row[coverage_index - 1] if coverage_index > 2 else None
    quantity_line = row[coverage_index + 1]

    coverage = _parse_percentage(row[coverage_index], warnings)
    quantity = _parse_quantity(quantity_line, warnings)
    name_line = _clean_spaces(" ".join(commercial_lines))
    name, dosage, presentation = _split_medication_name(name_line)

    return Medication(
        name=_normalize_text_field("Medicamento", name, warnings),
        active_ingredient=_normalize_text_field("Monodroga", active_ingredient, warnings),
        dosage=_normalize_text_field("Dosis", dosage, warnings),
        presentation=_normalize_text_field("Presentacion", presentation, warnings),
        quantity=quantity,
        instructions=None,
        coverage_percentage=coverage,
    )


def _split_medication_name(value: str) -> tuple[str | None, str | None, str | None]:
    match = re.search(
        r"\b(\d+(?:[.,]\d+)?\s*(?:MG|MCG|G|ML|UI|U|%)\b)\s*(.*)$",
        value,
        flags=re.IGNORECASE,
    )
    if not match:
        return _clean_spaces(value), None, None

    name = _clean_spaces(value[: match.start()])
    dosage = _clean_spaces(match.group(1).replace(",", "."))
    presentation = _clean_spaces(match.group(2)) or None
    return name or None, dosage, presentation


def _find_first_index(values: list[str], predicate) -> int | None:
    for index, value in enumerate(values):
        if predicate(value):
            return index
    return None


def _find_invalid_coverage(row: list[str]) -> str | None:
    for value in row:
        if "%" in value:
            return value
    return None


def _parse_percentage(value: str, warnings: list[str]) -> float | None:
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*%", value.strip())
    if not match:
        _add_warning(warnings, f"Cobertura tiene formato invalido: {value}.")
        return None
    percentage = float(match.group(1).replace(",", "."))
    if not 0 <= percentage <= 100:
        _add_warning(warnings, f"Cobertura fuera de rango: {value}.")
        return None
    return percentage


def _parse_quantity(value: str, warnings: list[str]) -> float | None:
    try:
        return float(value.replace(",", ".").strip())
    except ValueError:
        _add_warning(warnings, f"Cantidad autorizada tiene formato invalido: {value}.")
        return None


def _is_percentage(value: str) -> bool:
    return bool(re.fullmatch(r"\d+(?:[.,]\d+)?\s*%", value.strip()))


def _is_product_code(value: str) -> bool:
    return bool(re.fullmatch(r"\d+\s*-\s*\d+", value.strip()))


def _is_table_header(value: str) -> bool:
    normalized_value = normalize_text(value)
    return normalized_value in {
        "CODIGO",
        "NOMBRE COMERCIAL",
        "MONODROGA",
        "COBERT.",
        "CANT. AUT.",
    }


def _strip_final_name_punctuation(value: str) -> str:
    return value.rstrip(".,;:").strip()


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


def _find_valid_until_value(lines: list[str]) -> str | None:
    for line in lines:
        normalized_line = normalize_text(line)
        if normalized_line.startswith("AUTORIZACI") and "HASTA EL" in normalized_line:
            return _value_after_colon(line) or None
    return None


def _find_label_value(lines: list[str], label: str) -> str | None:
    line = _find_line(lines, label)
    if line is None:
        return None
    return _value_after_colon(line) or None


def _find_line(lines: list[str], label: str) -> str | None:
    normalized_label = normalize_text(label)
    for line in lines:
        normalized_line = normalize_text(line)
        if normalized_line.startswith(normalized_label):
            return line
    return None


def _find_line_index(lines: list[str], marker: str) -> int | None:
    normalized_marker = normalize_text(marker)
    for index, line in enumerate(lines):
        if normalize_text(line).startswith(normalized_marker):
            return index
    return None


def _value_after_colon(line: str) -> str:
    if ":" not in line:
        return ""
    return _clean_spaces(line.split(":", 1)[1])


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


def _add_required_field_warnings(document: MedicalDocument, warnings: list[str]) -> None:
    if not document.patient.name:
        _add_warning(warnings, "No se pudo extraer el nombre del afiliado.")
    if not document.medications:
        _add_warning(warnings, "No se pudo extraer ningun medicamento autorizado.")
    if not document.issued_at:
        _add_warning(warnings, "No se pudo extraer la fecha de autorizacion o emision.")
    if not document.valid_until:
        _add_warning(warnings, "No se pudo extraer la fecha de validez de la autorizacion.")


def _add_warning(warnings: list[str], message: str) -> None:
    if message not in warnings:
        warnings.append(message)
