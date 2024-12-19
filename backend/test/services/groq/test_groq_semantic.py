import pytest
from sqlalchemy.orm import Session
from backend.services.validation.validation_service import ValidationService
from backend.entities.ni_token import NIToken
from backend.entities.ni_document import NIDocument
from backend.test.services.fixtures import ni_with_component_and_method, insert_artifact, setup_insert_data_fixture

GOOD_CODE = """\
export class MyComponent {
  user = { name: 'Alice', email: 'alice@example.com' };
  sendEmail() { console.log('Email sent!'); }
}
"""

BAD_CODE_NO_METHOD = """\
export class MyComponent {
  user = { name: 'Alice', email: 'alice@example.com' };
  // missing sendEmail method
}
"""

BAD_CODE_NO_COMPONENT = """\
function sendEmail() {
  console.log('Sending email');
}
"""

def test_semantic_success(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None, "Token should exist"
    artifact = insert_artifact(db_session, token, GOOD_CODE)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert result.success is True

def test_semantic_missing_method(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None, "Token should exist"
    artifact = insert_artifact(db_session, token, BAD_CODE_NO_METHOD)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success

def test_semantic_missing_component(db_session: Session, ni_with_component_and_method: NIDocument):
    token = db_session.query(NIToken).filter_by(ni_document_id=ni_with_component_and_method.id).first()
    assert token is not None, "Token should exist"
    artifact = insert_artifact(db_session, token, BAD_CODE_NO_COMPONENT)
    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success