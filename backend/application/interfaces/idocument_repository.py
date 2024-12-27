from abc import ABC, abstractmethod
from typing import Optional
from backend.domain.models import DomainDocument

class IDocumentRepository(ABC):
    """
    Defines how the application retrieves and persists NI documents.
    The actual implementation belongs in the infrastructure layer.
    """

    @abstractmethod
    def get_document(self, doc_id: int) -> Optional[DomainDocument]:
        """
        Retrieve a domain document by its ID. Return None if not found.
        """
        pass

    @abstractmethod
    def save_document(self, document: DomainDocument) -> None:
        """
        Persist changes to a domain document.
        This might create or update the record in the database.
        Depending on the domain logic, tokens might be handled separately.
        """
        pass

    @abstractmethod
    def update_document_content(self, doc_id: int, new_content: str) -> None:
        """
        Update only the content of the NI document with the given doc_id.
        """
        pass
