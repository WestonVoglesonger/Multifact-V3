import pytest
from datetime import datetime
from typing import Any, Dict, List

from pydantic import ValidationError

from snc.application.dto.ni_token import TokenResponse

from snc.test.test_application.test_dtos.fixtures import valid_token_data


def test_token_response_valid(valid_token_data: Dict[str, Any]):
    token = TokenResponse(**valid_token_data)
    assert token.uuid == "abc123"
    assert token.type == "scene"
    assert token.scene_name == "IntroScene"
    assert token.component_name is None
    assert token.hash == "abcdef123456"
    assert token.dependencies == []


def test_token_response_missing_uuid(valid_token_data: Dict[str, Any]):
    data = valid_token_data.copy()
    data.pop("uuid")  # remove required field
    with pytest.raises(ValidationError) as exc:
        TokenResponse(**data)
    assert "uuid" in str(exc.value)


def test_token_response_invalid_order(valid_token_data: Dict[str, Any]):
    data = valid_token_data.copy()
    data["order"] = "not-an-integer"  # wrong type
    with pytest.raises(ValidationError) as exc:
        TokenResponse(**data)
    assert "order" in str(exc.value)


def test_token_response_dependencies(valid_token_data: Dict[str, Any]):
    data = valid_token_data.copy()
    data["dependencies"] = ["dep1", "dep2"]
    token = TokenResponse(**data)
    assert token.dependencies == ["dep1", "dep2"]
