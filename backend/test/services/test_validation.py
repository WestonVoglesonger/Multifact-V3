from sqlalchemy.orm import Session
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.validation import ValidationService
from backend.test.services.conftest import session
from backend.services.ni_service import NIService
from backend.models.ni_document import NIDocumentCreate
from backend.entities.ni_token import NIToken

def test_validation_of_artifact(session: Session):
    # Create a NI document that generates at least one token
    doc_data = NIDocumentCreate(content="[Scene:Test]\nSome content.", version="v1")
    ni_doc = NIService.create_ni_document(doc_data, session)

    # Retrieve the created token
    token = session.query(NIToken).filter(NIToken.ni_document_id == ni_doc.id).first()
    assert token is not None

    # Now we know token.id exists, we can reference it
    bad_code = "let x: number = 'string';"
    artifact = CompiledMultifact(
        ni_token_id=token.id,  # use the actual token id
        language="typescript",
        framework="angular",
        code=bad_code,
        valid=True,
        cache_hit=False
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)

    result = ValidationService.validate_artifact(artifact.id, session)
    assert result.success is False
    assert len(result.errors) > 0