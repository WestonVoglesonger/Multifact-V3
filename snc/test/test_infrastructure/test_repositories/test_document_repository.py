# File: test_infrastructure/test_repositories/test_document_repository.py

import pytest
from sqlalchemy.orm import Session
from datetime import datetime
from snc.infrastructure.repositories.document_repository import DocumentRepository
from snc.infrastructure.entities.ni_document import NIDocument
from snc.domain.models import DomainDocument


def test_get_document(db_session: Session):
    """
    Test DocumentRepository.get_document with an existing doc from demo data.
    """
    doc_repo = DocumentRepository(db_session)

    # Grab a doc from the DB, e.g. [Scene:Updater]
    doc_ent = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:Updater]%"))
        .first()
    )
    assert doc_ent, "Expected an 'Updater' document in the DB."

    domain_doc = doc_repo.get_document(doc_ent.id)
    assert domain_doc is not None, "Should return a DomainDocument"
    assert domain_doc.id == doc_ent.id
    assert "[Scene:Updater]" in domain_doc.content


def test_update_document_content(db_session: Session):
    """
    Test updating a doc's content.
    """
    doc_repo = DocumentRepository(db_session)

    # Create a new doc
    new_doc = NIDocument(content="[Scene:TempDoc]\nHello", version="vX")
    db_session.add(new_doc)
    db_session.commit()

    # Now update content
    doc_repo.update_document_content(new_doc.id, "Updated content.")
    updated_doc = doc_repo.get_document(new_doc.id)
    assert updated_doc is not None
    assert updated_doc.content == "Updated content."


def test_save_document(db_session: Session):
    """
    Test DocumentRepository.save_document. We fix it so it converts from DomainDocument to NIDocument.
    """
    doc_repo = DocumentRepository(db_session)

    domain_doc = DomainDocument(
        doc_id=0,
        content="[Scene:SaveDoc]\nNew doc content",
        version="vSave",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tokens=[],
    )

    # This calls our new 'save_document' which internally builds an NIDocument
    saved_doc = doc_repo.save_document(domain_doc)

    # Check DB
    doc_in_db = (
        db_session.query(NIDocument)
        .filter_by(content="[Scene:SaveDoc]\nNew doc content")
        .one_or_none()
    )
    assert doc_in_db, "Document should be persisted in DB."
    assert doc_in_db.version == "vSave", "Version should match what we set."
