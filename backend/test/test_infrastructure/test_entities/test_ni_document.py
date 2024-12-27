# tests/entities/test_ni_document.py

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.infrastructure.entities.ni_document import NIDocument
from backend.infrastructure.entities.ni_token import NIToken
from backend.domain.models import DomainDocument

def test_ni_document_creation(db_session: Session):
    """
    Test creating and persisting an NIDocument.
    """
    doc = NIDocument(
        content="This is a test NIDocument content",
        version="testVersion"
    )
    db_session.add(doc)
    db_session.commit()

    fetched = db_session.query(NIDocument).filter_by(version="testVersion").one()
    assert fetched.id is not None
    assert fetched.content == "This is a test NIDocument content"

def test_ni_document_tokens_relationship(db_session: Session):
    """
    Test the one-to-many relationship between NIDocument and NIToken.
    """
    doc = NIDocument(content="Document with tokens", version="vTestDoc")
    db_session.add(doc)
    db_session.commit()

    tok1 = NIToken(
        ni_document_id=doc.id,
        token_uuid="token-1",
        token_type="scene",
        content="Scene content",
        hash="hash1"
    )
    tok2 = NIToken(
        ni_document_id=doc.id,
        token_uuid="token-2",
        token_type="component",
        content="Comp content",
        hash="hash2"
    )
    db_session.add_all([tok1, tok2])
    db_session.commit()

    fetched_doc = db_session.query(NIDocument).get(doc.id)
    assert len(fetched_doc.tokens) == 2
    uuids = {t.token_uuid for t in fetched_doc.tokens}
    assert "token-1" in uuids
    assert "token-2" in uuids

def test_ni_document_to_domain_document(db_session: Session):
    """
    Test the to_domain_document() method with associated tokens.
    """
    doc = NIDocument(content="Doc for to_domain", version="vDoc")
    db_session.add(doc)
    db_session.commit()

    token_ent = NIToken(
        ni_document_id=doc.id,
        token_uuid="doc-dom-uuid",
        token_type="scene",
        content="doc scene content",
        hash="doc-dom-hash"
    )
    db_session.add(token_ent)
    db_session.commit()

    domain_doc = doc.to_domain_document()
    assert isinstance(domain_doc, DomainDocument)
    assert domain_doc.id == doc.id
    assert len(domain_doc.tokens) == 1
    assert domain_doc.tokens[0].content == "doc scene content"

def test_ni_document_from_domain_document(db_session: Session):
    """
    Test the @classmethod NIDocument.to_entity_document() from a DomainDocument.
    """
    domain_doc = DomainDocument(
        doc_id=0,
        content="Domain doc content",
        version="domV",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        tokens=[]
    )

    doc_ent = NIDocument.to_entity_document(domain_doc)
    db_session.add(doc_ent)
    db_session.commit()

    fetched = db_session.query(NIDocument).filter_by(version="domV").one()
    assert fetched.content == "Domain doc content"
