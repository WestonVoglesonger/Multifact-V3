from datetime import datetime
from typing import Any, Dict
import pytest
from pydantic import ValidationError
from backend.application.dto.compiled_multifact import CompiledMultifactCreate, CompiledMultifactRead
from backend.test.test_application.test_dtos.fixtures import valid_compiled_multifact_create_data, valid_compiled_multifact_read_data


def test_compiled_multifact_create_valid(valid_compiled_multifact_create_data: Dict[str, Any]):
    cmc = CompiledMultifactCreate(**valid_compiled_multifact_create_data)
    assert cmc.ni_token_id == 42
    assert cmc.language == "typescript"
    assert cmc.code == "export class Example {}"
    assert cmc.valid is True
    assert cmc.cache_hit is False


def test_compiled_multifact_create_missing_field(valid_compiled_multifact_create_data: Dict[str, Any]):
    data = valid_compiled_multifact_create_data.copy()
    data.pop("code")
    with pytest.raises(ValidationError) as exc:
        CompiledMultifactCreate(**data)
    assert "code" in str(exc.value)


def test_compiled_multifact_create_defaults(valid_compiled_multifact_create_data: Dict[str, Any]):
    data = valid_compiled_multifact_create_data.copy()
    data.pop("valid")  # remove optional field with default
    cmc = CompiledMultifactCreate(**data)
    assert cmc.valid is True, "Default for valid should be True"
    assert cmc.cache_hit is False


def test_compiled_multifact_read_valid(valid_compiled_multifact_read_data: Dict[str, Any]):
    cmr = CompiledMultifactRead(**valid_compiled_multifact_read_data)
    assert cmr.id == 100
    assert cmr.ni_token_id == 42
    assert cmr.code == "export class Example {}"
    assert cmr.created_at == datetime(2023, 1, 1, 9, 0, 0)
    assert cmr.valid is True
    assert cmr.cache_hit is True


def test_compiled_multifact_read_missing_id(valid_compiled_multifact_read_data: Dict[str, Any]):
    data = valid_compiled_multifact_read_data.copy()
    data.pop("id")
    with pytest.raises(ValidationError) as exc:
        CompiledMultifactRead(**data)
    assert "id" in str(exc.value)


def test_compiled_multifact_read_wrong_type(valid_compiled_multifact_read_data: Dict[str, Any]):
    data = valid_compiled_multifact_read_data.copy()
    data["ni_token_id"] = "not-an-int"
    with pytest.raises(ValidationError) as exc:
        CompiledMultifactRead(**data)
    assert "ni_token_id" in str(exc.value)

