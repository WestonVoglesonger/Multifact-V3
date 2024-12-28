# tests/services/test_dependency_graph_service.py

import pytest
from sqlalchemy.orm import Session
from snc.application.services.dependency_graph_service import DependencyGraphService
from snc.infrastructure.repositories.token_repository import TokenRepository
from snc.infrastructure.entities.ni_token import NIToken
from snc.infrastructure.entities.ni_document import NIDocument
from datetime import datetime, timezone
import uuid
from snc.application.services.token_diff_service import TokenDiffService


def test_dependency_graph_service_normal(db_session: Session):
    """
    Tests normal S->C->F chain from the inserted doc: "[Scene:S]... [Component:C]... [Function:F]"
    """
    token_repo = TokenRepository(db_session)

    # Retrieve the dependency document by content
    dep_doc = (
        db_session.query(NIToken)
        .filter(NIToken.token_type == "scene", NIToken.scene_name == "S")
        .first()
    )
    assert (
        dep_doc is not None
    ), "Expected token with type 'scene' and scene_name 'S' to exist."

    doc_id = dep_doc.ni_document_id
    dgs = DependencyGraphService(token_repo=token_repo)
    dgs.from_document(doc_id)
    sorted_ids = dgs.topological_sort()

    # Fetch tokens to verify the order
    f_token = (
        db_session.query(NIToken)
        .filter(
            NIToken.token_type == "function",
            NIToken.scene_name == None,
            NIToken.component_name == None,
        )
        .first()
    )
    c_token = (
        db_session.query(NIToken)
        .filter(NIToken.token_type == "component", NIToken.component_name == "C")
        .first()
    )
    s_token = dep_doc  # Already retrieved

    expected_order = [f_token.id, c_token.id, s_token.id]
    assert (
        sorted_ids == expected_order
    ), f"Expected order {expected_order}, got {sorted_ids}"


def test_dependency_graph_service_cycle(db_session: Session):
    """
    Insert a cycle scenario to ensure the service raises a ValueError.
    """
    # Insert a new document with a cycle
    cycle_doc = NIDocument(
        content="[Scene:CycleA]\nREF:CycleB\n[Component:CycleB]\nREF:CycleA",
        version="v1",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(cycle_doc)
    db_session.commit()

    # Create tokens: CycleA (scene) and CycleB (component)
    cycle_a_token = NIToken(
        ni_document_id=cycle_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="scene",
        token_name="CycleA",
        scene_name="CycleA",
        component_name=None,
        order=0,
        content="CycleA content\nREF:CycleB",
        hash=TokenDiffService._compute_hash("CycleA content\nREF:CycleB"),
    )
    cycle_b_token = NIToken(
        ni_document_id=cycle_doc.id,
        token_uuid=str(uuid.uuid4()),
        token_type="component",
        token_name="CycleB",
        scene_name=None,
        component_name="CycleB",
        order=1,
        content="CycleB content\nREF:CycleA",
        hash=TokenDiffService._compute_hash("CycleB content\nREF:CycleA"),
    )
    db_session.add_all([cycle_a_token, cycle_b_token])
    db_session.commit()

    # Link dependencies: CycleA depends on CycleB, CycleB depends on CycleA
    cycle_a_token.dependencies.append(cycle_b_token)
    cycle_b_token.dependencies.append(cycle_a_token)
    db_session.commit()

    token_repo = TokenRepository(db_session)
    dgs = DependencyGraphService(token_repo=token_repo)

    with pytest.raises(ValueError, match="Cycle detected in dependency graph."):
        dgs.from_document(cycle_doc.id)
        dgs.topological_sort()
