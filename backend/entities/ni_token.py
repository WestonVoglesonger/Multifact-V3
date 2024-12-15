from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from .entity_base import EntityBase

class NIToken(EntityBase):
    __tablename__ = "ni_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ni_document_id: Mapped[int] = mapped_column(Integer, ForeignKey("ni_documents.id", ondelete="CASCADE"), nullable=False)
    scene_name: Mapped[str] = mapped_column(String, nullable=True)
    component_name: Mapped[str] = mapped_column(String, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    hash: Mapped[str] = mapped_column(String, nullable=False)