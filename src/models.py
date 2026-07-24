from datetime import date

from pydantic import BaseModel, Field

from src.classifier import DocumentType


class Patient(BaseModel):
    name: str | None = None
    dni: str | None = None
    cuil: str | None = None
    birth_date: date | None = None
    gender: str | None = None


class Professional(BaseModel):
    name: str | None = None
    license: str | None = None


class Medication(BaseModel):
    name: str | None = None
    active_ingredient: str | None = None
    dosage: str | None = None
    presentation: str | None = None
    quantity: float | None = None
    instructions: str | None = None
    coverage_percentage: float | None = None


class MedicalDocument(BaseModel):
    document_type: DocumentType
    patient: Patient
    professional: Professional | None = None
    medications: list[Medication] = Field(default_factory=list)
    diagnosis: str | None = None
    issued_at: date | None = None
    valid_until: date | None = None
    warnings: list[str] = Field(default_factory=list)
