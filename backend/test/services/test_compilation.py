import pytest
from sqlalchemy.orm import Session
from backend.services.ni_service import NIService
from backend.services.compilation import CompilationService
from backend.models.ni_document import NIDocumentCreate
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact

def test_compile_token_new(session: Session):
    # First, create a NI document so we have a token
    doc_data = NIDocumentCreate(content="[Scene:Intro]\nThis is intro scene.", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, session)

    # Get the token
    token = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).first()
    assert token is not None

    # Compile the token
    artifact = CompilationService.compile_token(token.id, session)
    assert artifact is not None
    assert artifact.ni_token_id == token.id
    # Instead of checking for "Generated code for token", let's check that the code is non-empty and seems like code
    assert len(artifact.code.strip()) > 0
    # Check for something code-related, e.g. 'component', since we assume an Angular component:
    assert "@component" in artifact.code.lower() or "component" in artifact.code.lower()

def test_compile_token_cache(session: Session):
    # Create doc and get a token again
    doc_data = NIDocumentCreate(content="Just some content no scenes", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, session)
    token = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).first()

    # First compile
    artifact_1 = CompilationService.compile_token(token.id, session)
    assert artifact_1 is not None
    assert artifact_1.cache_hit == False

    # Second compile should hit cache
    artifact_2 = CompilationService.compile_token(token.id, session)
    assert artifact_2 is not None
    assert artifact_2.id == artifact_1.id
    assert artifact_2.cache_hit == True

def test_compile_token_non_existent(session: Session):
    # Try compiling a non-existent token ID
    with pytest.raises(ValueError) as exc:
        CompilationService.compile_token(9999, session)  # assumes no token with id 9999
    assert "Token with id 9999 not found" in str(exc.value)