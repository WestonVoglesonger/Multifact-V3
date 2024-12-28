import pytest
from unittest.mock import patch, MagicMock

from sqlalchemy.orm import Session

# Entities / domain
from snc.infrastructure.entities.ni_document import NIDocument
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.compiled_multifact import CompiledMultifact

# Application services
from snc.application.services.self_repair_service import SelfRepairService
from snc.application.interfaces.ivalidation_service import (
    ValidationError,
    ValidationResult,
)

from snc.test.fixtures import mock_self_repair_service, real_self_repair_service


def test_self_repair_service_flow(
    db_session: Session,
    mock_self_repair_service: SelfRepairService,
    # If needed: doc_repo, token_repo, artifact_repo, etc.
):
    """
    This test mocks the "compiling LLM" to produce invalid code,
    so that we can see if the SelfRepairService can fix it.
    """

    # 1) Create a doc + token in the DB
    doc_ent = NIDocument(content="", version="TestRepairDoc")
    db_session.add(doc_ent)
    db_session.commit()
    doc_id = doc_ent.id

    token_ent = NIToken(
        ni_document_id=doc_id,
        token_uuid="repair-test-uuid",
        token_type="function",
        token_name="BrokenFunction",
        scene_name=None,
        component_name=None,
        content="Narrative instructions for a broken function",
        hash="dummy-hash",
    )
    db_session.add(token_ent)
    db_session.commit()

    # 2) Mock the compilation step. Instead of actually calling the LLM,
    #    we directly insert an artifact with "invalid code."
    artifact = CompiledMultifact(
        ni_token_id=token_ent.id,
        language="typescript",
        framework="angular",
        code="function brokenCode { console.log('Missing parentheses' }",  # invalid TS
        valid=False,
        cache_hit=False,
    )
    db_session.add(artifact)
    db_session.commit()
    artifact_id = artifact.id

    # 3) We'll patch the "validate_artifact" call to simulate failing first,
    #    then re-check if it's been "fixed."

    # The first time it's called => it fails
    # The second time => let's pretend it's successful.

    # We'll store references to each call result in a list
    val_results = [
        ValidationResult(
            success=False,
            errors=[
                ValidationError(
                    file="artifact.ts", line=1, char=10, message="TS1005: ';' expected."
                )
            ],
        ),
        ValidationResult(success=True, errors=[]),
    ]
    val_result_iter = iter(val_results)

    def mock_validate_artifact(art_id: int):
        return next(val_result_iter)

    # 4) We'll also patch the "fix_code" method on your code-fixer to produce "fixed" code
    def mock_fix_code(original_code: str, error_summary: str) -> str:
        return "function fixedCode() { console.log('Now it works!'); }"

    with patch.object(
        mock_self_repair_service.validation_service,
        "validate_artifact",
        side_effect=mock_validate_artifact,
    ):
        with patch.object(
            mock_self_repair_service.code_fixer_service,
            "fix_code",
            side_effect=mock_fix_code,
        ):
            # 5) Actually call repair_artifact
            success = mock_self_repair_service.repair_artifact(
                artifact_id, max_attempts=2
            )
            assert success is True, "Expected the artifact to be successfully repaired."

    # 6) Check that the artifact in DB is now updated with the fixed code
    repaired_art = db_session.query(CompiledMultifact).get(artifact_id)
    assert "function fixedCode()" in repaired_art.code
    assert repaired_art.valid is True
    print("SelfRepairService test passed: artifact was fixed & validated!")


def test_self_repair_service_flow_with_real_llm(
    db_session: Session, real_self_repair_service: SelfRepairService
):
    """
    This test uses the real LLM to compile the artifact.
    """
    # 1) Create a doc + token in the DB
    doc_ent = NIDocument(content="", version="TestRepairDoc")
    db_session.add(doc_ent)
    db_session.commit()
    doc_id = doc_ent.id

    token_ent = NIToken(
        ni_document_id=doc_id,
        token_uuid="repair-test-uuid",
        token_type="function",
        token_name="BrokenFunction",
        scene_name=None,
        component_name=None,
        content="Narrative instructions for a broken function",
        hash="dummy-hash",
    )
    db_session.add(token_ent)
    db_session.commit()

    artifact = CompiledMultifact(
        ni_token_id=token_ent.id,
        language="typescript",
        framework="angular",
        code="function brokenCode { console.log('Missing parentheses' }",  # invalid TS
        valid=False,
        cache_hit=False,
    )
    db_session.add(artifact)
    db_session.commit()
    artifact_id = artifact.id

    # 3) We'll patch the "validate_artifact" call to simulate failing first,
    #    then re-check if it's been "fixed."

    # The first time it's called => it fails
    # The second time => let's pretend it's successful.

    # We'll store references to each call result in a list
    val_results = [
        ValidationResult(
            success=False,
            errors=[
                ValidationError(
                    file="artifact.ts", line=1, char=10, message="TS1005: ';' expected."
                )
            ],
        ),
        ValidationResult(success=True, errors=[]),
    ]

    # 5) Actually call repair_artifact
    success = real_self_repair_service.repair_artifact(artifact_id, max_attempts=2)
    assert success is True, "Expected the artifact to be successfully repaired."

    # 6) Check that the artifact in DB is now updated with the fixed code
    repaired_art = db_session.query(CompiledMultifact).get(artifact_id)
    assert "function brokenCode()" in repaired_art.code
    assert repaired_art.valid is True
    print("SelfRepairService test passed: artifact was fixed & validated!")
