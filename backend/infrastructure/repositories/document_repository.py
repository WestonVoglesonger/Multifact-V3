from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.domain.models import DomainDocument, DomainToken
from backend.infrastructure.entities.ni_document import NIDocument
from backend.application.interfaces.idocument_repository import IDocumentRepository

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