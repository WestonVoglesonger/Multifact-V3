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
):
    """
    Test the self-repair service with mocked dependencies to verify the repair flow.
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

    # 2) Create an artifact with invalid code
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

    # 3) Set up validation results sequence
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

    # 4) Set up mock fix_code that returns valid TypeScript
    def mock_fix_code(original_code: str, error_summary: str) -> str:
        return "function fixedCode() { console.log('Now it works!'); }"

    with patch.object(
        mock_self_repair_service.validation_service,
        "validate_artifact",
        side_effect=mock_validate_artifact,
    ), patch.object(
        mock_self_repair_service.code_fixer_service,
        "fix_code",
        side_effect=mock_fix_code,
    ):
        # 5) Run repair process
        success = mock_self_repair_service.repair_artifact(
            artifact_id, max_attempts=2
        )
        assert success is True, "Expected the artifact to be successfully repaired"

    # 6) Verify the repair results
    repaired_art = db_session.query(CompiledMultifact).get(artifact_id)
    assert repaired_art is not None, f"Artifact {artifact_id} not found"
    
    # Check for valid TypeScript function structure
    code = repaired_art.code
    assert "function" in code, "Should contain a function declaration"
    assert "(" in code and ")" in code, "Function should have parentheses"
    assert "{" in code and "}" in code, "Function should have braces"
    assert "console.log" in code, "Should contain the expected functionality"
    assert repaired_art.valid is True, "Artifact should be marked as valid"


def test_self_repair_service_flow_with_real_llm(
    db_session: Session, real_self_repair_service: SelfRepairService
):
    """
    Test the self-repair service with real LLM integration.
    """
    # 1) Create test document and token
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
        content="Create a TypeScript function that logs a message",
        hash="dummy-hash",
    )
    db_session.add(token_ent)
    db_session.commit()

    # 2) Create an artifact with invalid code
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

    # 3) Set up validation sequence
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

    with patch.object(
        real_self_repair_service.validation_service,
        "validate_artifact",
        side_effect=mock_validate_artifact,
    ):
        # 4) Run repair process
        success = real_self_repair_service.repair_artifact(artifact_id, max_attempts=2)
        assert success is True, "Expected the artifact to be successfully repaired"

    # 5) Verify the repair results
    repaired_art = db_session.query(CompiledMultifact).get(artifact_id)
    assert repaired_art is not None, f"Artifact {artifact_id} not found"
    
    # Check for valid TypeScript function structure
    code = repaired_art.code
    assert "function" in code, "Should contain a function declaration"
    assert "(" in code and ")" in code, "Function should have parentheses"
    assert "{" in code and "}" in code, "Function should have braces"
    assert repaired_art.valid is True, "Artifact should be marked as valid"
