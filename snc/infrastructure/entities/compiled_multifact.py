"""Entity model for compiled multifacts."""

from sqlalchemy import (
    Integer,
    Text,
    ForeignKey,
    String,
    Boolean,
    DateTime,
    func,
    Float,
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from .entity_base import EntityBase
from snc.domain.models import DomainCompiledMultifact


class CompiledMultifact(EntityBase):
    """Database model for compiled multifacts.

    This model represents the persistent storage of compiled artifacts,
    including their code, metadata, and validation status.
    """

    __tablename__ = "compiled_multifacts"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    ni_token_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ni_tokens.id", ondelete="CASCADE"),
        nullable=False,
    )
    language: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    valid: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    cache_hit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    token_hash: Mapped[str] = mapped_column(String, nullable=True)

    # New fields:
    score: Mapped[float] = mapped_column(Float, nullable=True)
    feedback: Mapped[str] = mapped_column(Text, nullable=True)

    def to_domain_artifact(self) -> DomainCompiledMultifact:
        """Convert to domain model.

        Returns:
            Domain model representation of this artifact
        """
        return DomainCompiledMultifact(
            artifact_id=self.id,
            ni_token_id=self.ni_token_id,
            language=self.language,
            framework=self.framework,
            code=self.code,
            valid=self.valid,
            cache_hit=self.cache_hit,
            created_at=self.created_at,
            score=self.score,
            feedback=self.feedback,
        )

    @classmethod
    def to_entity_artifact(
        cls, domain: DomainCompiledMultifact
    ) -> "CompiledMultifact":
        """Create entity from domain model.

        Args:
            domain: Domain model to convert

        Returns:
            New entity instance
        """
        return cls(
            ni_token_id=domain.ni_token_id,
            language=domain.language,
            framework=domain.framework,
            code=domain.code,
            valid=domain.valid,
            cache_hit=domain.cache_hit,
            token_hash=None,
            score=domain.score,
            feedback=domain.feedback,
        )

    @classmethod
    def from_domain_artifact(
        cls, domain: DomainCompiledMultifact
    ) -> "CompiledMultifact":
        """Convert a domain model to an entity.

        Args:
            domain: Domain model to convert

        Returns:
            New entity instance with all fields set
        """
        return cls(
            id=domain.id if domain.id != 0 else None,  # Don't use 0 as ID
            ni_token_id=domain.ni_token_id,
            language=domain.language,
            framework=domain.framework,
            code=domain.code,
            valid=domain.valid,
            cache_hit=domain.cache_hit,
            created_at=domain.created_at,
            score=domain.score,
            feedback=domain.feedback,
        )
