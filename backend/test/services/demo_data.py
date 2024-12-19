from sqlalchemy.orm import Session
from backend.models.ni_document import NIDocumentCreate
from backend.services.ni import NIService
from backend.services.compilation import CompilationService
from backend.services.validation.validation_service import ValidationService
from backend.entities.ni_token import NIToken
from backend.services.llm.base_llm_client import BaseLLMClient
def insert_demo_data(session: Session, llm_client: BaseLLMClient):
    # Document 1: Simple scenario
    doc1_data = NIDocumentCreate(
        content="[Scene:SimpleDOC1MARKER]\nA simple component scenario.",
        version="v1"
    )
    doc1 = NIService.create_ni_document(doc1_data, session)
    tokens_doc1 = session.query(NIToken).filter(NIToken.ni_document_id == doc1.id).all()
    for t in tokens_doc1:
        artifact = CompilationService.compile_token(t.id, session, llm_client)
        ValidationService.validate_artifact(artifact.id, session)

    # Document 2: More complex scenario
    doc2_data = NIDocumentCreate(
        content="[Scene:Intro]\nUserProfile component.\n[Scene:Main]\nDashboard component.",
        version="v2"
    )
    doc2 = NIService.create_ni_document(doc2_data, session)
    tokens_doc2 = session.query(NIToken).filter(NIToken.ni_document_id == doc2.id).all()
    for t in tokens_doc2:
        artifact = CompilationService.compile_token(t.id, session)
        ValidationService.validate_artifact(artifact.id, session)

    # Document 3: Tricky scenario for self-repair
    doc3_data = NIDocumentCreate(
        content="[Scene:TrickyDOC3MARKER]\nNumberDisplay expects number but uses string.",
        version="v3"
    )
    doc3 = NIService.create_ni_document(doc3_data, session)
    tokens_doc3 = session.query(NIToken).filter(NIToken.ni_document_id == doc3.id).all()
    for t in tokens_doc3:
        artifact = CompilationService.compile_token(t.id, session)
        # Validation likely fails, no self repair done here; test can do it.
        ValidationService.validate_artifact(artifact.id, session)

    # Document 4: Another scenario
    doc4_data = NIDocumentCreate(
        content="[Scene:Components]\nUserList & UserDetail scenario.\n[Scene:Interaction]\nEmit event on user click.",
        version="v4"
    )
    doc4 = NIService.create_ni_document(doc4_data, session)
    tokens_doc4 = session.query(NIToken).filter(NIToken.ni_document_id == doc4.id).all()
    for t in tokens_doc4:
        artifact = CompilationService.compile_token(t.id, session)
        ValidationService.validate_artifact(artifact.id, session)

    # Document 5: Uncompiled doc
    doc5_data = NIDocumentCreate(
        content="[Scene:CompileTest]\nCompileTest component.",
        version="v1"
    )
    NIService.create_ni_document(doc5_data, session)

    session.commit()