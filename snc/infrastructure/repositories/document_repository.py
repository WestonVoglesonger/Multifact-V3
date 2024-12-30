from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from snc.domain.models import DomainDocument, DomainToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.application.interfaces.idocument_repository import IDocumentRepository


class DocumentRepository(IDocumentRepository):
    def __init__(self, session: Session):
        self.session = session

    def get_document(self, ni_id: int) -> Optional[DomainDocument]:
        doc = self.session.query(NIDocument).filter(NIDocument.id == ni_id).one_or_none()
        if doc is None:
            return None

        # Convert NIDocument to DomainDocument
        return doc.to_domain_document()

    def update_document_content(self, ni_id: int, new_content: str) -> None:
        doc = self.session.query(NIDocument).filter(NIDocument.id == ni_id).one_or_none()
        if doc:
            doc.content = new_content
            self.session.commit()

    def save_document(self, document: DomainDocument) -> DomainDocument:
        """
        Convert the domain doc to an entity, persist it, then return a fresh DomainDocument.
        """
        document_entity = NIDocument.to_entity_document(document)
        self.session.add(document_entity)
        self.session.commit()

        # Now return the domain doc re-built from entity
        return document_entity.to_domain_document()

    def create_document(self, content: str = "", version: str = "v1.0") -> DomainDocument:
        """Create a new document and return it.

        Args:
            content: Initial document content
            version: Document version string

        Returns:
            DomainDocument: The created document
        """
        from snc.infrastructure.entities.ni_document import NIDocument
        from datetime import datetime

        now = datetime.now()
        document = NIDocument(
            content=content,
            version=version,
            created_at=now,
            updated_at=now,
        )
        self.session.add(document)
        self.session.commit()
        return document.to_domain_document()
