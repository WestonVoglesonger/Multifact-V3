from datetime import datetime, timezone
from snc.domain.models import DomainDocument, DomainToken


def test_domain_document_minimal_init():
    """
    Verify that DomainDocument can be constructed with minimal required arguments.
    """
    now = datetime.now(timezone.utc)
    doc = DomainDocument(
        doc_id=10,
        content="Document content here",
        version=None,
        created_at=now,
        updated_at=now,
    )
    assert doc.id == 10
    assert doc.content == "Document content here"
    assert doc.version is None
    assert doc.created_at == now
    assert doc.updated_at == now
    assert doc.tokens == []


def test_domain_document_with_tokens():
    """
    Verify that DomainDocument can hold tokens and add_token works.
    """
    now = datetime.now(timezone.utc)
    doc = DomainDocument(
        doc_id=123,
        content="Some doc content",
        version="v2",
        created_at=now,
        updated_at=now,
    )
    token_a = DomainToken(
        id=None,
        token_uuid="tok-a",
        token_type="scene",
        content="SceneA",
        hash="aaa",
        token_name="SceneA",
    )
    token_b = DomainToken(
        id=None,
        token_uuid="tok-b",
        token_type="component",
        content="ComponentB",
        hash="bbb",
        token_name="ComponentB",
    )
    doc.add_token(token_a)
    doc.add_token(token_b)

    assert len(doc.tokens) == 2
    assert doc.tokens[0].token_uuid == "tok-a"
    assert doc.tokens[1].token_uuid == "tok-b"
