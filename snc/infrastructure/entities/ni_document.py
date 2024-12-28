from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, String, DateTime, func
from .entity_base import EntityBase
from typing import List
from snc.domain.models import DomainDocument


class NIDocument(EntityBase):
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

    tokens: Mapped[List["NIToken"]] = relationship(
        "NIToken", back_populates="ni_document"
    )

    def to_domain_document(self) -> DomainDocument:
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
        return cls(content=domain.content, version=domain.version)
