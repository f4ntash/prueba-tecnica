from src.models import MedicalDocument
from src.parsers.base import DocumentParser


class MedicationAuthorizationParser(DocumentParser):
    def parse(self, text: str) -> MedicalDocument:
        raise NotImplementedError(
            "Medication authorization parsing is not implemented in this first stage."
        )
