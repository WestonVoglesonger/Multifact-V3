# tests/services/test_token_diff_service.py

import pytest
import hashlib
from snc.application.services.token_diff_service import (
    TokenDiffService,
    TokenDiffError,
)
from snc.application.services.exceptions import TokenNameCollisionError
from snc.domain.models import DomainToken, TokenDiffResult, DomainCompiledMultifact
from typing import cast, List, Tuple
from snc.application.services.token_diff_service import TokenDiffService


def test_token_diff_service_no_changes():
    """
    Test TokenDiffService when there are no changes between old and new tokens.
    """
    # Old token
    old_token = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        content="Scene content",
        scene_name="S",
        token_name="S",
        hash=TokenDiffService._compute_hash("Scene content"),
    )
    old_tokens = [(old_token, None)]

    # New token data identical to old
    new_tokens_data = [{"type": "scene", "scene_name": "S", "content": "Scene content"}]

    service = TokenDiffService()
    diff_result = service.diff_tokens(
        cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
        new_tokens_data,
    )
    assert len(diff_result.removed) == 0
    assert len(diff_result.added) == 0
    assert len(diff_result.changed) == 0


def test_token_diff_service_added_and_removed():
    """
    Test TokenDiffService detecting removed and added tokens.
    """
    # Old tokens
    old_token1 = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        scene_name="Scene1",
        token_name="Scene1",
        content="Scene1 content",
        hash=TokenDiffService._compute_hash("Scene1 content"),
    )
    old_tokens = [(old_token1, None)]

    # New tokens: remove old_token1, add new_token2
    new_tokens_data = [
        {"type": "scene", "scene_name": "Scene2", "content": "Scene2 content"}
    ]

    service = TokenDiffService()
    diff_result = service.diff_tokens(
        cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
        new_tokens_data,
    )

    assert len(diff_result.removed) == 1
    assert diff_result.removed[0][0] == old_token1
    assert len(diff_result.added) == 1
    assert diff_result.added[0]["type"] == "scene"
    assert diff_result.added[0]["scene_name"] == "Scene2"
    assert len(diff_result.changed) == 0


def test_token_diff_service_changed_tokens():
    """
    Test TokenDiffService detecting changed tokens.
    """
    # Old token
    old_token = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        scene_name="Scene1",
        token_name="Scene1",
        content="Old content",
        hash=TokenDiffService._compute_hash("Old content"),
    )
    old_tokens = [(old_token, None)]

    # New token data with changed content
    new_tokens_data = [
        {"type": "scene", "scene_name": "Scene1", "content": "New content"}
    ]

    service = TokenDiffService()
    diff_result = service.diff_tokens(
        cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
        new_tokens_data,
    )

    assert len(diff_result.changed) == 1
    assert diff_result.changed[0][0] == old_token
    assert diff_result.changed[0][2]["content"] == "New content"


def test_token_diff_service_duplicate_old_tokens():
    """
    Test TokenDiffService raises TokenDiffError when duplicate keys are found in old tokens.
    """
    # Two old tokens with same type and name
    old_token1 = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        scene_name="SceneX",
        token_name="SceneX",
        content="ContentX1",
        hash=TokenDiffService._compute_hash("ContentX1"),
    )
    old_token2 = DomainToken(
        id=2,
        token_uuid="uuid-2",
        token_type="scene",
        scene_name="SceneX",
        token_name="SceneX",
        content="ContentX2",
        hash=TokenDiffService._compute_hash("ContentX2"),
    )
    old_tokens = [(old_token1, None), (old_token2, None)]

    # New tokens data
    new_tokens_data = [
        {"type": "scene", "scene_name": "SceneX", "content": "ContentX1"}
    ]

    service = TokenDiffService()

    with pytest.raises(TokenDiffError, match="Duplicate old token key detected:"):
        service.diff_tokens(
            cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
            new_tokens_data,
        )


def test_token_diff_service_duplicate_new_tokens():
    """
    Test TokenDiffService raises TokenNameCollisionError when duplicate keys are found in new tokens.
    """
    # Old tokens
    old_token = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        scene_name="SceneX",
        token_name="SceneX",
        content="ContentX",
        hash=TokenDiffService._compute_hash("ContentX"),
    )
    old_tokens = [(old_token, None)]

    # New tokens data with duplicate scene_name
    new_tokens_data = [
        {"type": "scene", "scene_name": "SceneX", "content": "ContentX"},
        {"type": "scene", "scene_name": "SceneX", "content": "ContentX Duplicate"},
    ]

    service = TokenDiffService()

    with pytest.raises(
        TokenNameCollisionError, match="Duplicate new token key detected:"
    ):
        service.diff_tokens(
            cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
            new_tokens_data,
        )


def test_token_diff_service_partial_changes():
    """
    Test TokenDiffService with a mix of changes: remove one, change one, add one.
    """
    # Old tokens
    old_token1 = DomainToken(
        id=1,
        token_uuid="uuid-1",
        token_type="scene",
        scene_name="Scene1",
        token_name="Scene1",
        content="Content1",
        hash=TokenDiffService._compute_hash("Content1"),
    )
    old_token2 = DomainToken(
        id=2,
        token_uuid="uuid-2",
        token_type="component",
        component_name="Comp1",
        token_name="Comp1",
        content="Comp Content1",
        hash=TokenDiffService._compute_hash("Comp Content1"),
    )
    old_tokens = [(old_token1, None), (old_token2, None)]

    # New tokens data: remove old_token1, change old_token2, add new_token3
    new_tokens_data = [
        {
            "type": "component",
            "component_name": "Comp1",
            "content": "Comp Content Updated",
        },
        {"type": "function", "function_name": "Func1", "content": "Function Content1"},
    ]

    service = TokenDiffService()
    diff_result = service.diff_tokens(
        cast(List[Tuple[DomainToken, DomainCompiledMultifact | None]], old_tokens),
        new_tokens_data,
    )

    assert len(diff_result.removed) == 1
    assert diff_result.removed[0][0] == old_token1
    assert len(diff_result.changed) == 1
    assert diff_result.changed[0][0] == old_token2
    assert diff_result.changed[0][2]["content"] == "Comp Content Updated"
    assert len(diff_result.added) == 1
    assert diff_result.added[0]["type"] == "function"
    assert diff_result.added[0]["function_name"] == "Func1"
    assert diff_result.added[0]["content"] == "Function Content1"
