import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from openai.types.completion_usage import CompletionUsage
from snc.infrastructure.llm.openai_llm_client import OpenAILLMClient
from snc.domain.models import Model
from snc.test.test_infrastructure.test_llm.mocks import (
    mock_openai_client,
    mock_model_openai,
)


@pytest.fixture
def openai_llm_client(
    mock_model_openai: Model,
    mock_openai_client: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Create an OpenAILLMClient but patch out the real OpenAI(...) usage
    so no actual network calls are made.
    """
    # Patch the import of OpenAI in openai_llm_client
    with patch(
        "snc.infrastructure.llm.openai_llm_client.OpenAI",
        return_value=mock_openai_client,
    ):
        yield OpenAILLMClient(mock_model_openai)


def test_parse_document_empty_json(
    openai_llm_client: OpenAILLMClient, mock_openai_client: MagicMock
):
    """Test parse_document returning empty scenes if JSON is empty or missing keys."""
    # Force the .create(...) call to return "{}" as content
    mock_openai_client.chat.completions.create.return_value.choices[
        0
    ].message.content = "{}"

    result = openai_llm_client.parse_document("Some NI content")
    assert isinstance(result, dict)
    assert "scenes" in result
    assert result["scenes"] == []


def test_parse_document_with_scenes(
    openai_llm_client: OpenAILLMClient, mock_openai_client: MagicMock
):
    """Test parse_document returning valid JSON with scenes."""
    mock_openai_client.chat.completions.create.return_value.choices[
        0
    ].message.content = '{"scenes":[{"name":"Intro","narrative":"some text"}]}'
    result = openai_llm_client.parse_document("Content with scenes")
    assert "scenes" in result
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["name"] == "Intro"


def test_generate_code(
    openai_llm_client: OpenAILLMClient, mock_openai_client: MagicMock
):
    """Test generate_code calls the API and returns stripped content."""
    mock_openai_client.chat.completions.create.return_value.choices[
        0
    ].message.content = "   Some TS code   "
    code = openai_llm_client.generate_code("component content")
    assert code == "Some TS code"
    # Verify the LLM was called
    mock_openai_client.chat.completions.create.assert_called_once()


def test_fix_code(openai_llm_client: OpenAILLMClient, mock_openai_client: MagicMock):
    """Test fix_code logic with a simple mock response."""
    mock_openai_client.chat.completions.create.return_value.choices[
        0
    ].message.content = "Fixed Code"
    result = openai_llm_client.fix_code("Original code", "Some error summary")
    assert result == "Fixed Code"


def test_compute_cost_from_model(openai_llm_client: OpenAILLMClient):
    """Test cost calculation using a mock usage."""
    usage_mock = CompletionUsage(
        prompt_tokens=1000, completion_tokens=500, total_tokens=1500
    )
    cost = openai_llm_client.compute_cost_from_model(usage_mock)
    # prompt_tokens=1000 => 1000/1000=1 * prompt_cost_per_1k=0.003 => 0.003
    # completion_tokens=500 => 0.5 * 0.004 => 0.002
    # total => 0.003 + 0.002 => 0.005
    assert cost == pytest.approx(0.005)
