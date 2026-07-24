from abc import ABC, abstractmethod

from src.models import MedicalDocument


class DocumentParser(ABC):
    """Base interface for future document-specific parsers."""

    @abstractmethod
    def parse(self, text: str) -> MedicalDocument:
        """Parse extracted text into a structured medical document."""
