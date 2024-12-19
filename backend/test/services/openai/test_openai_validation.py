import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from backend.services.validation.validation_service import ValidationService
from backend.entities.ni_document import NIDocument
from backend.entities.ni_token import NIToken
from backend.entities.compiled_multifact import CompiledMultifact
from backend.test.services.fixtures import setup_insert_data_fixture

@patch("backend.services.validation.validation_service.ValidationService._get_validator")
@patch("backend.services.validation.validation_service.run")
def test_validate_artifact_success(
    mock_run: MagicMock, mock_get_validator: MagicMock, db_session: Session
):
    # Mock the subprocess run for tsc
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 0

    # Mock the plugin-based validator with no errors
    mock_validator = MagicMock()
    # Instead of mock_validator.validate, we rely on the actual calls made by the code:
    # run_syntax_type_check and run_semantic_checks
    mock_validator.run_syntax_type_check.return_value = []
    mock_validator.run_semantic_checks.return_value = []
    mock_get_validator.return_value = mock_validator

    # Find a test doc
    doc1 = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:SimpleDOC1MARKER]%"))
        .first()
    )
    assert doc1 is not None, "Test document was not found in the database."

    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc1.id).first()
    artifact = db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()

    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert result.success is True
    assert len(result.errors) == 0

    # Ensure that run_semantic_checks was called once since syntax check passed
    mock_validator.run_semantic_checks.assert_called_once()

@patch("backend.services.validation.validation_service.ValidationService._get_validator")
@patch("backend.services.validation.validation_service.run")
def test_validate_artifact_failure(
    mock_run: MagicMock, mock_get_validator: MagicMock, db_session: Session
):
    # Simulate a TS compiler error
    mock_run.return_value.stdout = "artifact_1.ts(1,5): error TS2322: Type 'string' is not assignable to type 'number'."
    mock_run.return_value.stderr = ""
    mock_run.return_value.returncode = 2

    mock_validator = MagicMock()
    # Set run_syntax_type_check to return a compiler error
    from backend.services.validation.validation_service import ValidationError
    mock_validator.run_syntax_type_check.return_value = [
        ValidationError(file="artifact_1.ts", line=1, char=5, message="TS2322: Type 'string' is not assignable to type 'number'.")
    ]
    # No semantic errors
    mock_validator.run_semantic_checks.return_value = []

    mock_get_validator.return_value = mock_validator

    doc3 = (
        db_session.query(NIDocument)
        .filter(NIDocument.content.like("%[Scene:TrickyDOC3MARKER]%"))
        .first()
    )
    assert doc3 is not None, "Test document was not found in the database."

    token = db_session.query(NIToken).filter(NIToken.ni_document_id == doc3.id).first()
    artifact = (
        db_session.query(CompiledMultifact).filter_by(ni_token_id=token.id).first()
    )

    result = ValidationService.validate_artifact(artifact.id, db_session)
    assert not result.success  # Now should be False because we returned an error
    assert len(result.errors) > 0
    assert "TS2322" in result.errors[0].message

    # Compiler failed, so no semantic checks should run
    mock_validator.run_semantic_checks.assert_not_called() 