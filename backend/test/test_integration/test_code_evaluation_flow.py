# File: backend/test/test_integration/test_code_evaluation_flow.py

import json
import pytest
from sqlalchemy.orm import Session
from unittest.mock import patch

# Entities
from backend.infrastructure.entities.ni_document import NIDocument

# Our orchestrator or service that orchestrates parse+diff+compile
from backend.application.services.ni_orchestrator import NIOrchestrator

# LLM Model (pick one that triggers code evaluation)
from backend.infrastructure.llm.model_factory import OpenAIModelType

from backend.test.fixtures import ni_orchestrator


@pytest.mark.integration
def test_code_evaluation_flow(
    db_session: Session,
    ni_orchestrator: NIOrchestrator,
):
    """
    Integration test focusing on code evaluation after compilation,
    using a bracket-based text with:
      [Scene:Intro]
      [Component:Greeting]
      [Function:displayGreeting]
      [Function:logEntry]
    We expect 4 tokens total (1 scene, 1 component, 2 functions).
    Each token gets compiled => each token should have an artifact => 
    each artifact has 'score' and 'feedback'.
    """

    content =  """[Scene:WizardStep1]
        The user begins the setup process with an introduction.
        [Component:Introduction]
        Provide an overview of what the setup will entail.
        [Function:proceedToStep2]
        Move the user to the next step when they click "Next.
        [Scene:WizardStep2]
        The user inputs their personal information.
        [Component:PersonalInfo]
        Collect the user's name, email, and phone number.
        [Function:validateInput]
        Ensure the input is valid and complete.
        [Function:submitForm]
        Submit the form and confirm the user's information."""

    # 1) Create a doc record in DB (empty content at first)
    document = ni_orchestrator.create_ni_document(content)

    tokens = ni_orchestrator.token_repo.get_all_tokens_for_document(document.id)

    # 2) Compile the document
    ni_orchestrator.compile_tokens(tokens, OpenAIModelType.GPT_4O_MINI)
    
    print("\n=== TEST DEBUGGING START ===")

    # 4) Debug: check the tokens that were created
    tokens = ni_orchestrator.token_repo.get_all_tokens_for_document(document.id)
    print("\nDEBUG - Created tokens:")
    for token in tokens:
        print(
            f"Token: type={token.token_type}, "
            f"scene={token.scene_name}, "
            f"component={token.component_name}, "
            f"content-len={len(token.content)}"
        )

    # Here we expect 4 tokens total:
    assert len(tokens) == 7, (
        f"Expected 7 tokens (2 scenes, 2 component, 3 functions), "
        f"found {len(tokens)}.\n"
        f"Tokens found: {[(t.token_type, t.scene_name, t.component_name) for t in tokens]}"
    )

    # 5) Each token should have a compiled artifact => let's gather them
    tokens_with_artifacts = ni_orchestrator.token_repo.get_tokens_with_artifacts(document.id)
    artifact_map = {}
    print("\nDEBUG - Tokens with artifacts:")
    for domain_token, domain_artifact in tokens_with_artifacts:
        print(
            f"\nToken ID={domain_token.id}, type={domain_token.token_type}, "
            f"scene={domain_token.scene_name}, component={domain_token.component_name}"
        )
        if domain_artifact:
            artifact_map[domain_token.id] = domain_artifact
            print(
                f"  Has artifact: id={domain_artifact.id}, "
                f"valid={domain_artifact.valid}"
            )
        else:
            print("  No artifact attached")

    # We expect 4 artifacts as well (one per token).
    assert len(artifact_map) == 7, (
        f"Not all tokens got an artifact after compilation.\n"
        f"Found {len(artifact_map)} artifacts for {len(tokens)} tokens."
    )

    # 6) Verify that each artifact has code, plus code evaluation (score & feedback)
    print("\nDEBUG - Artifact evaluation results:")
    for t_id, art in artifact_map.items():
        print(f"\nArtifact {art.id} for token {t_id}:")
        print(f"  Score: {getattr(art, 'score', 'N/A')}")
        print(f"  Feedback: {getattr(art, 'feedback', 'N/A')}")
        print(f"  Valid: {getattr(art, 'valid', 'N/A')}")
        code_len = len(art.code) if art.code else 0
        print(f"  Code length: {code_len}")

        # A) Must have some code
        assert code_len > 0, (
            f"Artifact {art.id} has empty code. "
            f"Token ID={t_id}, type=???"
        )
        # B) Must have score & feedback
        assert hasattr(art, "score"), f"Artifact {art.id} missing 'score' attribute."
        assert hasattr(art, "feedback"), f"Artifact {art.id} missing 'feedback' attribute."
        # C) Score not None, in [0..10]
        assert art.score is not None, f"Score is None for artifact {art.id}."
        assert 0 <= art.score <= 10, f"Unexpected score={art.score} for artifact {art.id}."
        # D) Feedback is non-empty
        assert art.feedback.strip(), f"Feedback is empty for artifact {art.id}."

    print("\n=== TEST DEBUGGING END ===")
    print("\nCode Evaluation Flow: All artifacts compiled and evaluated with a score/feedback!")
