from sqlalchemy import (
    Column,
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
from .entity_base import EntityBase
from datetime import datetime
from backend.domain.models import DomainCompiledMultifact


class CompiledMultifact(EntityBase):
    __tablename__ = "compiled_multifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ni_token_id: Mapped[int] = mapped_column(Integer, ForeignKey("ni_tokens.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    token_hash: Mapped[str] = mapped_column(String, nullable=True)

    # New fields:
    score: Mapped[float] = mapped_column(Float, nullable=True)      
    feedback: Mapped[str] = mapped_column(Text, nullable=True)     

    def to_domain_artifact(self) -> DomainCompiledMultifact:
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
            feedback=self.feedback
        )

    @classmethod
    def to_entity_artifact(cls, domain: DomainCompiledMultifact) -> "CompiledMultifact":
        return cls(
            ni_token_id=domain.ni_token_id,
            language=domain.language,
            framework=domain.framework,
            code=domain.code,
            valid=domain.valid,
            cache_hit=domain.cache_hit,
            token_hash=None,
            score=domain.score,    
            feedback=domain.feedback
        )
