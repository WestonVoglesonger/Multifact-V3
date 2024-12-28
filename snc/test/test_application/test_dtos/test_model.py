from datetime import datetime
from typing import Any, Dict
import pytest
from pydantic import ValidationError
from snc.application.dto.llm_model import Model
from snc.infrastructure.llm.model_factory import ClientType
from snc.test.test_application.test_dtos.fixtures import valid_model_data


def test_model_valid(valid_model_data: Dict[str, Any]):
    m = Model(**valid_model_data)
    assert m.client_type == ClientType.OPENAI
    assert m.name == "gpt-4o"
    assert m.context_window == 32000
    assert m.reasoning_tokens is None


def test_model_missing_required_field(valid_model_data: Dict[str, Any]):
    data = valid_model_data.copy()
    data.pop("name")
    with pytest.raises(ValidationError) as exc:
        Model(**data)
    assert "name" in str(exc.value)


def test_model_wrong_type(valid_model_data: Dict[str, Any]):
    data = valid_model_data.copy()
    data["prompt_cost_per_1k"] = "not-a-float"
    with pytest.raises(ValidationError) as exc:
        Model(**data)
    assert "prompt_cost_per_1k" in str(exc.value)
