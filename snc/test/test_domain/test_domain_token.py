import pytest
from datetime import datetime, timedelta
from snc.domain.models import DomainToken


def test_domain_token_minimal_init():
    """
    Verify that DomainToken can be constructed with minimal valid arguments.
    """
    token = DomainToken(
        id=None,
        token_uuid="uuid-123",
        token_type="scene",
        content="Some scene content",
        hash="abcdef1234567890",
        token_name="SceneA",
    )
    assert token.id is None
    assert token.token_uuid == "uuid-123"
    assert token.token_type == "scene"
    assert token.content == "Some scene content"
    assert token.hash == "abcdef1234567890"
    assert token.scene_name is None
    assert token.component_name is None
    assert token.order == 0
    assert token.dependencies == []


def test_domain_token_full_init():
    """
    Verify that DomainToken can be constructed with all optional fields set.
    """
    dep_token = DomainToken(
        id=101,
        token_uuid="dep-uuid",
        token_type="function",
        content="Dependency function content",
        hash="dep-hash",
        token_name="FunctionB",
    )
    token = DomainToken(
        id=42,
        token_uuid="main-uuid",
        token_type="component",
        content="Main component content",
        hash="main-hash",
        token_name="CompA",
        component_name="CompA",
        order=5,
        dependencies=[dep_token],
    )
    assert token.id == 42
    assert token.token_uuid == "main-uuid"
    assert token.token_type == "component"
    assert token.content == "Main component content"
    assert token.hash == "main-hash"
    assert token.scene_name is None
    assert token.component_name == "CompA"
    assert token.order == 5
    assert len(token.dependencies) == 1
    assert token.dependencies[0].id == 101
    assert token.dependencies[0].token_uuid == "dep-uuid"


def test_domain_token_add_dependency():
    """
    Verify that adding dependencies via add_dependency works.
    """
    main_token = DomainToken(
        id=1,
        token_uuid="main-uuid",
        token_type="scene",
        content="Scene content",
        hash="main-hash",
        token_name="SceneA",
    )
    dep_token_1 = DomainToken(
        id=2,
        token_uuid="dep-1",
        token_type="function",
        content="Function1",
        hash="hash1",
        token_name="FunctionB",
    )
    dep_token_2 = DomainToken(
        id=3,
        token_uuid="dep-2",
        token_type="function",
        content="Function2",
        hash="hash2",
        token_name="FunctionB",
    )

    main_token.add_dependency(dep_token_1)
    main_token.add_dependency(dep_token_2)

    assert len(main_token.dependencies) == 2
    assert main_token.dependencies[0].token_uuid == "dep-1"
    assert main_token.dependencies[1].token_uuid == "dep-2"


def test_domain_token_get_dependency_uuids():
    """
    Verify get_dependency_uuids returns the correct list of UUIDs in order.
    """
    dep_token_a = DomainToken(
        id=5,
        token_uuid="dep-a",
        token_type="function",
        content="",
        hash="hasha",
        token_name="FunctionB",
    )
    dep_token_b = DomainToken(
        id=6,
        token_uuid="dep-b",
        token_type="function",
        content="",
        hash="hashb",
        token_name="FunctionB",
    )
    main_token = DomainToken(
        id=4,
        token_uuid="main-uuid",
        token_type="scene",
        content="",
        hash="main-hash",
        token_name="SceneA",
        dependencies=[dep_token_a, dep_token_b],
    )
    uuids = main_token.get_dependency_uuids()
    assert uuids == ["dep-a", "dep-b"]
