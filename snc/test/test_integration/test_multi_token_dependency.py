import pytest
from sqlalchemy.orm import Session

# Entities / domain
from snc.infrastructure.entities.ni_document import NIDocument

# Our orchestrator or service that orchestrates parse+compile
from snc.application.services.ni_orchestrator import NIOrchestrator

# A service that helps us analyze token dependencies
from snc.application.services.dependency_graph_service import DependencyGraphService

# LLM model type (pick one that won't call a real LLM or is replaced by a mock)
from snc.infrastructure.llm.model_factory import OpenAIModelType

from snc.test.fixtures import ni_orchestrator


@pytest.mark.integration
def test_multi_token_dependency(
    db_session: Session,
    ni_orchestrator: NIOrchestrator,
):
    """
    Integration test to verify that multiple tokens with dependencies
    are handled / compiled in a correct order, or at least recognized.

    We'll create a doc with two functions that reference each other,
    plus a scenario:
        - function add() references function inc()
        - function inc() is stand-alone or references something else
    The test then:
      1) Creates a doc with bracket-based lines referencing each other.
      2) Orchestrates parse + compile.
      3) Uses DependencyGraphService to confirm the tokens form
         the correct directed acyclic graph (DAG).
      4) (Optional) checks topological_sort doesn't fail with a cycle.
    """

    content = """
    [Scene:DepScene]
    This scene sets up a multi-token scenario.

    [Function:inc]
    This function increments a value by 1.

    [Function:add]
    This function [REF:inc] does a larger sum by calling inc multiple times.
    """

    # 1) Use the NI orchestrator to parse+create doc
    doc = ni_orchestrator.create_ni_document(
        initial_content=content,
        version="vDependencyTest",
    )

    # 2) Now gather tokens from DB
    tokens = ni_orchestrator.token_repo.get_all_tokens_for_document(doc.id)
    assert (
        len(tokens) == 3
    ), f"Expected 3 tokens: 1 scene + 2 functions. Found {len(tokens)}"

    # 5) Build the dependency graph
    graph_service = DependencyGraphService(ni_orchestrator.token_repo)
    graph_service.from_document(doc.id)

    # Optionally, verify the number of nodes in the graph
    assert (
        len(graph_service.tokens) == 3
    ), "Dependency graph should have 3 tokens total."

    # 6) Confirm topological sort
    #    If the test scenario is:
    #      - `inc` has no dependencies
    #      - `add` depends on `inc`
    #      - The scene is "DepScene" and typically doesn't depend on anything
    #    Then the sort order might place `inc` before `add`.
    order = graph_service.topological_sort()
    # The 'scene' might not reference anything, so it can appear anywhere,
    # but 'inc' must appear before 'add' if 'add' references inc.

    # We'll confirm 'add' is after 'inc'.
    # Step: find token_id for inc & add
    inc_token = next(
        (t for t in tokens if t.token_type == "function" and t.token_name == "inc"),
        None,
    )
    add_token = next(
        (t for t in tokens if t.token_type == "function" and t.token_name == "add"),
        None,
    )
    assert inc_token and add_token, "Expected to find tokens named inc and add."

    assert (
        inc_token.id is not None and add_token.id is not None
    ), "Token IDs should not be None"
    inc_index = order.index(inc_token.id)
    add_index = order.index(add_token.id)
    assert (
        inc_index < add_index
    ), "Token 'inc' should precede 'add' in topological order."

    # 7) (Optional) Confirm each compiled artifact is valid
    tokens_with_artifacts = ni_orchestrator.token_repo.get_tokens_with_artifacts(doc.id)
    invalid_artifacts = []
    for domain_token, domain_artifact in tokens_with_artifacts:
        if domain_artifact and not domain_artifact.valid:
            invalid_artifacts.append(domain_artifact.id)
    assert (
        not invalid_artifacts
    ), f"Found invalid artifacts in multi-token dependency test: {invalid_artifacts}"

    print(
        "\nMulti-token dependency test passed: tokens are compiled, topologically sorted, and valid."
    )
