import pytest
from typing import Optional
from snc.application.interfaces.idocument_repository import IDocumentRepository
from snc.domain.models import DomainDocument


def test_idocument_repository_is_abstract():
    with pytest.raises(TypeError):
        IDocumentRepository()  # type: ignore


def test_idocument_repository_minimal_subclass():
    class MinimalDocumentRepo(IDocumentRepository):
        def get_document(self, doc_id: int) -> Optional[DomainDocument]:
            return None

        def save_document(self, document: DomainDocument) -> None:
            pass

        def update_document_content(self, doc_id: int, new_content: str) -> None:
            pass

        def create_document(self, content: str, version: str) -> DomainDocument:
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            return DomainDocument(
                doc_id=1,
                content=content,
                version=version,
                created_at=now,
                updated_at=now,
            )

    repo = MinimalDocumentRepo()
    assert repo is not None
