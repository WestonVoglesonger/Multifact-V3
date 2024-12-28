import pytest
from unittest.mock import MagicMock, patch
from snc.infrastructure.llm.model_factory import GroqModelType
from snc.infrastructure.llm.llm_service_impl import ConcreteLLMService
from snc.test.test_infrastructure.test_llm.mocks import mock_llm_client


@patch("snc.infrastructure.llm.client_factory.ClientFactory.get_llm_client")
def test_parse_document(mock_client_factory: MagicMock, mock_llm_client: MagicMock):
    mock_client_factory.return_value = mock_llm_client
    service = ConcreteLLMService(GroqModelType.LLAMA_GUARD_3_8B)

    result = service.parse_document("some content")
    assert result == {"scenes": []}
    mock_llm_client.parse_document.assert_called_once()


@patch("snc.infrastructure.llm.client_factory.ClientFactory.get_llm_client")
def test_generate_code(mock_client_factory: MagicMock, mock_llm_client: MagicMock):
    mock_client_factory.return_value = mock_llm_client
    service = ConcreteLLMService(GroqModelType.LLAMA_GUARD_3_8B)

    code = service.generate_code("my token content", "reqs", "style")
    assert code == "mock code"
    mock_llm_client.generate_code.assert_called_once_with(
        "my token content", "reqs", "style"
    )


@patch("snc.infrastructure.llm.client_factory.ClientFactory.get_llm_client")
def test_fix_code(mock_client_factory: MagicMock, mock_llm_client: MagicMock):
    mock_client_factory.return_value = mock_llm_client
    service = ConcreteLLMService(GroqModelType.LLAMA_GUARD_3_8B)

    fixed = service.fix_code("bad code", "error summary")
    assert fixed == "fixed code"
    mock_llm_client.fix_code.assert_called_once_with("bad code", "error summary")
