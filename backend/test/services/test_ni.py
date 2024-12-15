import pytest
from sqlalchemy.orm import Session
from backend.services.ni_service import NIService
from backend.models.ni_document import NIDocumentCreate
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken

def test_create_ni_document_single_scene(session: Session):
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.", version="v1")

    ni_doc = NIService.create_ni_document(doc_data, session)

    # Check that the document is created
    assert ni_doc.id is not None
    assert ni_doc.content == doc_data.content
    assert ni_doc.version == "v1"

    # Check that a token was created
    tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).all()
    assert len(tokens) == 1
    token = tokens[0]
    assert token.scene_name == "Intro"
    assert token.content == "This is intro scene."
    assert len(token.hash) == 64  # SHA256 hex digest length

def test_create_ni_document_no_scene(session: Session):
    # If no [Scene:] line, entire doc is one DefaultScene
    doc_data = NIDocumentCreate(content="No scene here, just content.", version="v2")

    ni_doc = NIService.create_ni_document(doc_data, session)

    tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).all()
    assert len(tokens) == 1
    token = tokens[0]
    assert token.scene_name == "DefaultScene"
    assert token.content == "No scene here, just content."

def test_create_ni_document_multiple_scenes(session: Session):
    doc_data = NIDocumentCreate(
        content="[Scene:Intro]\nIntro content.\n[Scene:Main]\nMain content here.", 
        version="v3"
    )
    ni_doc = NIService.create_ni_document(doc_data, session)
    tokens = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).order_by(NIToken.order).all()
    assert len(tokens) == 2
    assert tokens[0].scene_name == "Intro"
    assert tokens[0].content == "Intro content."
    assert tokens[1].scene_name == "Main"
    assert tokens[1].content == "Main content here."