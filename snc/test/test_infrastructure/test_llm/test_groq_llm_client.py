import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from openai.types.completion_usage import CompletionUsage
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient
from snc.domain.models import Model
from snc.infrastructure.llm.model_factory import ClientType
from snc.test.test_infrastructure.test_llm.mocks import (
    mock_groq_client,
    mock_model_groq,
    groq_llm_client,
    mock_model_groq,
)
import json


def test_parse_document_empty_scenes(
    groq_llm_client: GroqLLMClient, mock_groq_client: MagicMock
):
    mock_groq_client.chat.completions.create.return_value.choices[0].message.content = (
        "{}"
    )
    result = groq_llm_client.parse_document("some doc content")
    assert result["scenes"] == []


def test_parse_document_scenes(
    groq_llm_client: GroqLLMClient, mock_groq_client: MagicMock
):
    """Test parsing a document with scenes."""
    mock_groq_client.chat.completions.create.return_value.choices[0].message.content = (
        json.dumps(
            {
                "scenes": [
                    {
                        "name": "Intro",
                        "narrative": "some text",
                        "components": [
                            {
                                "name": "Header",
                                "narrative": "header text",
                                "functions": [
                                    {"name": "doStuff", "narrative": "function text"}
                                ],
                            }
                        ],
                    }
                ]
            }
        )
    )
    result = groq_llm_client.parse_document("N/I content")
    assert "scenes" in result
    assert len(result["scenes"]) == 1
    assert result["scenes"][0]["name"] == "Intro"
    assert result["scenes"][0]["narrative"] == "some text"
    assert len(result["scenes"][0]["components"]) == 1
    assert result["scenes"][0]["components"][0]["name"] == "Header"
    assert result["scenes"][0]["components"][0]["narrative"] == "header text"
    assert len(result["scenes"][0]["components"][0]["functions"]) == 1
    assert result["scenes"][0]["components"][0]["functions"][0]["name"] == "doStuff"
    assert (
        result["scenes"][0]["components"][0]["functions"][0]["narrative"]
        == "function text"
    )


def test_generate_code(groq_llm_client: GroqLLMClient, mock_groq_client: MagicMock):
    mock_groq_client.chat.completions.create.return_value.choices[0].message.content = (
        "Some code"
    )
    code = groq_llm_client.generate_code("my token content")
    assert code == "Some code"


def test_fix_code(groq_llm_client: GroqLLMClient, mock_groq_client: MagicMock):
    mock_groq_client.chat.completions.create.return_value.choices[0].message.content = (
        "Fixed code"
    )
    result = groq_llm_client.fix_code("original code", "error summary")
    assert result == "Fixed code"


def test_compute_cost_from_model(groq_llm_client: GroqLLMClient):
    usage_mock = CompletionUsage(
        prompt_tokens=200, completion_tokens=300, total_tokens=500
    )
    cost = groq_llm_client.compute_cost_from_model(usage_mock)
    # 200 -> 0.2 * prompt_cost_per_1k=0.005 = 0.001
    # 300 -> 0.3 * completion_cost_per_1k=0.005 = 0.0015
    # total => 0.0025
    assert cost == pytest.approx(0.0025)
