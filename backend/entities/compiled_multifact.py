from sqlalchemy import Column, Integer, Text, ForeignKey, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .entity_base import EntityBase

class CompiledMultifact(EntityBase):
    __tablename__ = "compiled_multifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ni_token_id: Mapped[int] = mapped_column(Integer, ForeignKey("ni_tokens.id", ondelete="CASCADE"), nullable=False)
    language: Mapped[str] = mapped_column(String, nullable=False)
    framework: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")