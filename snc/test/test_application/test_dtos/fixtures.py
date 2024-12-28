from datetime import datetime
import uuid
from typing import Dict, Any

import pytest

from snc.infrastructure.llm.model_factory import ClientType


@pytest.fixture
def valid_token_data() -> Dict[str, Any]:
    """Return valid data for TokenResponse."""
    return {
        "uuid": "abc123",
        "type": "scene",
        "scene_name": "IntroScene",
        "component_name": None,
        "content": "Scene narrative goes here.",
        "hash": "abcdef123456",
        "order": 0,
        "dependencies": [],
    }


@pytest.fixture
def valid_document_data(valid_token_data: Dict[str, Any]) -> Dict[str, Any]:
    """Return valid data for DocumentResponse."""
    return {
        "id": 1,
        "content": "Full NI content text",
        "version": "v1",
        "created_at": datetime(2023, 1, 1, 10, 0, 0),
        "updated_at": datetime(2023, 1, 1, 12, 0, 0),
        "tokens": [valid_token_data],
    }


@pytest.fixture
def valid_model_data() -> Dict[str, Any]:
    """Return valid data for Model."""
    return {
        "client_type": ClientType.OPENAI,  # or ClientType.GROQ
        "name": "gpt-4o",
        "context_window": 32000,
        "max_output_tokens": 2048,
        "prompt_cost_per_1k": 0.03,
        "completion_cost_per_1k": 0.06,
        "supports_images": False,
        # optional fields
        "reasoning_tokens": None,
        "knowledge_cutoff_date": "2023-01-01",
        "supports_audio": False,
        "supports_video": True,
        "supports_reasoning": True,
    }


@pytest.fixture
def valid_compiled_multifact_create_data() -> Dict[str, Any]:
    """Return valid data for CompiledMultifactCreate."""
    return {
        "ni_token_id": 42,
        "language": "typescript",
        "framework": "angular",
        "code": "export class Example {}",
        "valid": True,
        "cache_hit": False,
        "score": 0.85,
        "feedback": "Code looks good and follows best practices",
    }


@pytest.fixture
def valid_compiled_multifact_read_data() -> Dict[str, Any]:
    """Return valid data for CompiledMultifactRead."""
    return {
        "id": 100,
        "ni_token_id": 42,
        "language": "typescript",
        "framework": "angular",
        "code": "export class Example {}",
        "created_at": datetime(2023, 1, 1, 9, 0, 0),
        "valid": True,
        "cache_hit": True,
        "score": 0.85,
        "feedback": "Code looks good and follows best practices",
    }
