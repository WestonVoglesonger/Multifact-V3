"""Entity model for narrative interface documents."""

from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, String, DateTime, func
from typing import List

from .entity_base import EntityBase
from snc.domain.models import DomainDocument
from .ni_token import NIToken

__all__ = ["NIDocument"]


class NIDocument(EntityBase):
    """Database model for narrative interface documents.

    This model represents the persistent storage of narrative interface
    documents, including their content, version, and tokens.
    """

    __tablename__ = "ni_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    tokens: Mapped[List[NIToken]] = relationship(
        "NIToken",
        backref="ni_document",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def to_domain_document(self) -> DomainDocument:
        """Convert to domain model.

        Returns:
            Domain model representation of this document
        """
        return DomainDocument(
            doc_id=self.id,
            content=self.content,
            version=self.version,
            created_at=self.created_at,
            updated_at=self.updated_at,
            tokens=[token.to_domain_token() for token in self.tokens],
        )

    @classmethod
    def to_entity_document(cls, domain: DomainDocument) -> "NIDocument":
        """Create entity from domain model.

        Args:
            domain: Domain model to convert

        Returns:
            New entity instance
        """
        return cls(content=domain.content, version=domain.version)
