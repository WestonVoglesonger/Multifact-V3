import pytest
from sqlalchemy.orm import Session
from .demo_data import insert_demo_data
from backend.services.ni import NIService
from backend.models.ni_document import NIDocumentCreate
from backend.entities.ni_token import NIToken
from backend.services.compilation import CompilationService

@pytest.fixture(autouse=True)
def setup_insert_data_fixture(db_session: Session):
    # Insert demo data before each test
    insert_demo_data(db_session)
    db_session.commit()
    yield

@pytest.fixture
def initial_ni(db_session: Session):
    # Create initial NI with two scenes and one component in each scene
    # Example:
    # [Scene:Intro]
    # Intro line
    # [Component:Greeting]
    # greet user
    #
    # [Scene:Main]
    # main line
    # [Component:Dashboard]
    # show data
    doc_data = NIDocumentCreate(
        content=(
            "[Scene:Intro]\nIntro line\n[Component:Greeting]\ngreet user\n\n"
            "[Scene:Main]\nmain line\n[Component:Dashboard]\nshow data"
        ),
        version="v1",
    )
    ni_doc = NIService.create_ni_document(doc_data, db_session)

    # Compile all tokens now
    tokens = db_session.query(NIToken).filter_by(ni_document_id=ni_doc.id).all()
    for t in tokens:
        CompilationService.compile_token(t.id, db_session)

    return ni_doc
