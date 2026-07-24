from src.models import MedicalDocument
from src.parsers.base import DocumentParser


class PrescriptionParser(DocumentParser):
    def parse(self, text: str) -> MedicalDocument:
        raise NotImplementedError(
            "Prescription parsing is not implemented in this first stage."
        )
