"""Relationship definitions for NI entities."""

from sqlalchemy import Column, Integer, ForeignKey, Table
from sqlalchemy.orm import relationship

from .entity_base import EntityBase

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


def setup_relationships():
    """Set up relationships between entities after they are defined."""
    from .ni_document import NIDocument
    from .ni_token import NIToken

    NIDocument.tokens = relationship(
        "NIToken", back_populates="ni_document", lazy="joined"
    )
    NIToken.ni_document = relationship(
        "NIDocument", back_populates="tokens", lazy="joined"
    )
    NIToken.dependencies = relationship(
        "NIToken",
        secondary=ni_token_dependencies,
        primaryjoin=(
            NIToken.id == ni_token_dependencies.c.token_id
        ),
        secondaryjoin=(
            NIToken.id == ni_token_dependencies.c.dependency_token_id
        ),
        backref="dependents",
        lazy="joined"
    )
