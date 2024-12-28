# tests/entities/test_ni_token.py

import pytest
from sqlalchemy.orm import Session
from datetime import datetime
from snc.infrastructure.entities.ni_token import NIToken, ni_token_dependencies
from snc.domain.models import DomainToken
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.entity_base import EntityBase


def test_ni_token_creation(db_session: Session):
    """
    Test creating and committing an NIToken entity to the DB.
    """
    doc = NIDocument(content="Doc for NIToken creation test", version="vTest")
    db_session.add(doc)
    db_session.commit()

    ni_token = NIToken(
        ni_document_id=doc.id,
        token_uuid="test-uuid-123",
        token_type="scene",
        token_name="TestScene",
        scene_name="TestScene",
        component_name=None,
        order=0,
        content="Some content for test token",
        hash="testhash123",
    )
    db_session.add(ni_token)
    db_session.commit()

    # Verify it's persisted
    fetched_token = (
        db_session.query(NIToken).filter_by(token_uuid="test-uuid-123").one()
    )
    assert fetched_token.id is not None
    assert fetched_token.ni_document_id == doc.id
    assert fetched_token.scene_name == "TestScene"


def test_ni_token_relationship(db_session: Session):
    """
    Test the relationship between NIToken and NIToken dependencies.
    """
    doc = NIDocument(content="Doc for dependency test", version="vTest")
    db_session.add(doc)
    db_session.commit()

    token_a = NIToken(
        ni_document_id=doc.id,
        token_uuid="uuid-A",
        token_type="scene",
        token_name="A",
        scene_name="A",
        component_name=None,
        order=0,
        content="Token A content",
        hash="hashA",
    )
    token_b = NIToken(
        ni_document_id=doc.id,
        token_uuid="uuid-B",
        token_type="component",
        token_name="B",
        scene_name=None,
        component_name="B",
        order=1,
        content="Token B content",
        hash="hashB",
    )

    db_session.add_all([token_a, token_b])
    db_session.commit()

    # Establish dependencies: A depends on B
    token_a.dependencies.append(token_b)
    db_session.commit()

    # Verify
    assert token_b in token_a.dependencies
    # And the 'dependents' backref
    # assert token_a in token_b.dependents


def test_ni_token_to_domain_token(db_session: Session):
    """
    Test the NIToken.to_domain_token() method.
    """
    doc = NIDocument(content="Doc for to_domain test", version="vTest")
    db_session.add(doc)
    db_session.commit()

    token_ent = NIToken(
        ni_document_id=doc.id,
        token_uuid="dom-uuid",
        token_type="function",
        token_name="TestFunction",
        scene_name=None,
        component_name=None,
        order=2,
        content="Function content here",
        hash="domhash",
    )
    db_session.add(token_ent)
    db_session.commit()

    domain_token = token_ent.to_domain_token()
    assert isinstance(domain_token, DomainToken)
    assert domain_token.id == token_ent.id
    assert domain_token.token_uuid == "dom-uuid"
    assert domain_token.hash == "domhash"
    assert domain_token.dependencies == []


def test_ni_token_from_domain_token(db_session: Session):
    """
    Test the @classmethod NIToken.to_entity_token() from a DomainToken.
    """
    domain_tok = DomainToken(
        id=None,
        token_uuid="dom-uuid-2",
        token_type="component",
        content="Comp content here",
        hash="domhash2",
        scene_name=None,
        component_name="TestComp",
        order=3,
        token_name="TestComp",
    )

    doc = NIDocument(content="Doc from domain token", version="vTest")
    db_session.add(doc)
    db_session.commit()

    token_ent = NIToken.to_entity_token(domain_tok, doc.id)
    db_session.add(token_ent)
    db_session.commit()

    fetched = db_session.query(NIToken).filter_by(token_uuid="dom-uuid-2").one()
    assert fetched.component_name == "TestComp"
    assert fetched.order == 3
    assert fetched.content == "Comp content here"
    assert fetched.hash == "domhash2"
