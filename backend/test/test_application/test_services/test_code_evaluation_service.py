# File: tests/test_code_evaluation.py

import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.application.services.code_evaluation_service import CodeEvaluationService
from backend.infrastructure.entities.compiled_multifact import CompiledMultifact
from backend.infrastructure.entities.ni_token import NIToken
from backend.infrastructure.services.compilation_service import (
    ConcreteCompilationService,
)
from backend.test.test_application.test_services.fixtures import evaluation_service_mock


def test_evaluate_compiled_artifact(
    db_session: Session, evaluation_service_mock: CodeEvaluationService
):
    """
    Example test verifying that evaluate_compiled_artifact properly
    calls CodeEvaluationService and returns the expected structure.
    """

    # 1) Grab an existing token from the DB so we don't violate the FK constraint
    existing_token = db_session.scalars(select(NIToken)).first()
    if not existing_token:
        pytest.skip("No tokens found in DB; cannot proceed with code evaluation test.")

    # 2) Insert an artifact referencing the existing token's ID
    new_artifact = CompiledMultifact(
        ni_token_id=existing_token.id,  # references a real token
        language="typescript",
        framework="angular",
        code="export class MyComp { doSomething(){ console.log('Hello'); } }",
        valid=True,
        cache_hit=False,
    )
    db_session.add(new_artifact)
    db_session.commit()

    compilation_service = ConcreteCompilationService(db_session)
    artifact_id = new_artifact.id

    # 3) Evaluate the compiled artifact (assumes 'evaluate_compiled_artifact' is a real method)
    result = compilation_service.evaluate_compiled_artifact(
        artifact_id=artifact_id, evaluator=evaluation_service_mock
    )

    # 4) Assertions
    assert "score" in result
    assert "feedback" in result
    assert result["score"] == 9.2
    assert result["feedback"] == "Great code structure."
