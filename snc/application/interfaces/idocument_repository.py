"""Interface for document repository operations."""

from abc import ABC, abstractmethod
from typing import Optional
from snc.domain.models import DomainDocument


class IDocumentRepository(ABC):
    """Repository interface for narrative instruction documents.

    Defines how the application retrieves and persists NI documents.
    The actual implementation belongs in the infrastructure layer.
    """

    @abstractmethod
    def get_document(self, doc_id: int) -> Optional[DomainDocument]:
        """Retrieve a domain document by its ID.

        Args:
            doc_id: The ID of the document to retrieve

        Returns:
            The domain document if found, None otherwise
        """
        pass

    @abstractmethod
    def save_document(self, document: DomainDocument) -> None:
        """Persist changes to a domain document.

        This might create or update the record in the database.
        Depending on the domain logic, tokens might be handled separately.

        Args:
            document: The domain document to save
        """
        pass

    @abstractmethod
    def update_document_content(self, doc_id: int, new_content: str) -> None:
        """Update only the content of a document.

        Args:
            doc_id: The ID of the document to update
            new_content: The new content to set
        """
        pass
