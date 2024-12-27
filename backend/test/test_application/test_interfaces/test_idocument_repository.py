import pytest
from typing import Optional
from backend.application.interfaces.idocument_repository import IDocumentRepository
from backend.domain.models import DomainDocument


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

    repo = MinimalDocumentRepo()
    assert repo is not None
