"""Entity model for narrative interface tokens."""

from typing import List, Dict, Optional, Sequence
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Text, String, ForeignKey, Table, Column

from .entity_base import EntityBase
from snc.domain.models import DomainToken

ni_token_dependencies = Table(
    "ni_token_dependencies",
    EntityBase.metadata,
    Column(
        "token_id",
        Integer,
        ForeignKey("ni_tokens.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dependency_token_id",
        Integer,
        ForeignKey("ni_tokens.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class NIToken(EntityBase):
    """Database model for narrative interface tokens.

    This model represents the persistent storage of tokens, including
    their content, type, and relationships to documents.
    """

    __tablename__ = "ni_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ni_document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ni_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_uuid: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    token_name: Mapped[str] = mapped_column(String, nullable=False)
    token_type: Mapped[str] = mapped_column(String, nullable=True)
    scene_name: Mapped[str] = mapped_column(String, nullable=True)
    component_name: Mapped[str] = mapped_column(String, nullable=True)
    function_name: Mapped[str] = mapped_column(String, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)

    dependencies: Mapped[List["NIToken"]] = relationship(
        "NIToken",
        secondary=ni_token_dependencies,
        primaryjoin=id == ni_token_dependencies.c.token_id,
        secondaryjoin=id == ni_token_dependencies.c.dependency_token_id,
        backref="dependents",
        lazy="joined",
        collection_class=list,
    )

    def to_domain_token(
        self, cache: Optional[Dict[int, DomainToken]] = None
    ) -> DomainToken:
        """Convert to domain model."""
        if cache is None:
            cache = {}

        if self.id in cache:
            return cache[self.id]

        # Create domain token without dependencies first
        domain_token = DomainToken(
            id=self.id,
            token_uuid=self.token_uuid,
            token_name=self.token_name,
            token_type=self.token_type,
            content=self.content,
            hash=self.hash,
            scene_name=self.scene_name,
            component_name=self.component_name,
            function_name=self.function_name,
            order=self.order,
            dependencies=[],
        )

        # Cache it before processing dependencies
        cache[self.id] = domain_token

        # Convert dependencies using Sequence for covariance
        domain_token.dependencies = list(
            dep.to_domain_token(cache) for dep in self.dependencies
        )
        return domain_token

    @classmethod
    def to_entity_token(cls, domain_token: DomainToken, document_id: int) -> "NIToken":
        """Convert domain model to entity."""
        return cls(
            ni_document_id=document_id,
            token_uuid=domain_token.token_uuid,
            token_name=domain_token.token_name,
            token_type=domain_token.token_type,
            content=domain_token.content,
            hash=domain_token.hash,
            scene_name=domain_token.scene_name,
            component_name=domain_token.component_name,
            function_name=domain_token.function_name,
            order=domain_token.order,
        )
