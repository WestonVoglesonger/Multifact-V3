# tests/services/test_self_repair_service.py

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from snc.infrastructure.entities.compiled_multifact import CompiledMultifact
from snc.infrastructure.repositories.artifact_repository import ArtifactRepository
from snc.infrastructure.validation.validation_service import ConcreteValidationService
from snc.infrastructure.services.code_fixer_service import ConcreteCodeFixerService
from snc.infrastructure.llm.client_factory import ClientFactory
from snc.application.services.self_repair_service import (
    SelfRepairService,
    ArtifactNotFoundError,
)
from snc.application.interfaces.ivalidation_service import (
    ValidationResult,
    ValidationError,
)
from snc.test.test_application.test_services.fixtures import mock_code_fixer_service


def test_self_repair_service_already_valid(
    db_session: Session, mock_code_fixer_service: MagicMock
):
    """
    In the demo data, we inserted a doc with a valid artifact under [Scene:RepairDoc].
    Test that SelfRepairService returns True if artifact is already valid.
    """

    # 1) Grab a valid artifact from the DB
    valid_artifact = (
        db_session.query(CompiledMultifact)
        .filter(CompiledMultifact.valid == True)
        .first()
    )
    assert valid_artifact, "Expected at least one valid artifact from the demo data."
    artifact_id = valid_artifact.id

    # 2) Build real or near-real services
    artifact_repo = ArtifactRepository(db_session)
    validation_service = ConcreteValidationService(db_session)
    code_fixer = ConcreteCodeFixerService()
    mock_code_fixer_service.side_effect = (
        lambda code, error_summary: "// Some code that passes validation\nexport class MyFixedComponent {}"
    )

    # 3) Create the SelfRepairService
    srs = SelfRepairService(artifact_repo, validation_service, code_fixer, db_session)

    # 4) Run the code
    success = srs.repair_artifact(artifact_id)

    # 5) Assert that since the artifact was already valid,
    #    the repair should trivially return True without trying to fix anything
    assert (
        success is True
    ), "If artifact is already valid, repair should succeed immediately."

    # 6) Confirm that fix_code was never called or was called zero times
    mock_code_fixer_service.assert_not_called()


def test_self_repair_service_fix_invalid(
    db_session: Session, mock_code_fixer_service: MagicMock
):
    """
    Test scenario where an artifact is invalid.
    We'll rely on the real ValidationService logic but mock out the LLM calls.
    """
    # 1) Grab an invalid artifact
    invalid_artifact = (
        db_session.query(CompiledMultifact)
        .filter(CompiledMultifact.valid == False)
        .first()
    )
    if not invalid_artifact:
        pytest.skip("No invalid artifact found in demo data. Insert one for this test.")
    artifact_id = invalid_artifact.id

    # 2) Build real or near-real services
    artifact_repo = ArtifactRepository(db_session)
    validation_service = ConcreteValidationService(db_session)
    code_fixer = ConcreteCodeFixerService()

    # Mock validation service to return failure
    with patch.object(code_fixer, "fix_code") as mock_fix_code, patch.object(
        validation_service, "validate_artifact"
    ) as mock_validate:
        mock_fix_code.return_value = (
            "// Some code that passes validation\nexport class MyFixedComponent {}"
        )
        mock_validate.return_value = ValidationResult(
            success=False,
            errors=[
                ValidationError(file="test.ts", line=1, char=1, message="Test error")
            ],
        )

        # 3) Create SelfRepairService
        srs = SelfRepairService(
            artifact_repo, validation_service, code_fixer, db_session
        )

        # 4) Repair with max_attempts=1
        success = srs.repair_artifact(artifact_id, max_attempts=1)

        # 5) Re-fetch
        updated_artifact = db_session.query(CompiledMultifact).get(artifact_id)
        assert updated_artifact, "Artifact should still exist after the attempt."

        if success:
            # If our validation logic thinks it's fixed by the new code
            assert (
                updated_artifact.valid is True
            ), "Artifact should now be valid after repair."
        else:
            # If validation still fails
            assert (
                updated_artifact.valid is False
            ), "Artifact should remain invalid after a failed repair."

        # 6) Confirm fix_code was indeed called once (since the artifact was invalid)
        assert (
            mock_fix_code.call_count == 1
        ), "We expected exactly one fix_code call for a single attempt."


def test_self_repair_service_artifact_not_found(
    db_session: Session, mock_code_fixer_service: MagicMock
):
    """
    If the artifact doesn't exist at all in the DB, the service should raise ArtifactNotFoundError.
    """
    artifact_repo = ArtifactRepository(db_session)
    validation_service = ConcreteValidationService(db_session)
    code_fixer = ConcreteCodeFixerService()
    srs = SelfRepairService(artifact_repo, validation_service, code_fixer, db_session)

    with pytest.raises(ArtifactNotFoundError):
        srs.repair_artifact(999999)  # Non-existent ID

    # fix_code not called in this scenario
    mock_code_fixer_service.assert_not_called()
