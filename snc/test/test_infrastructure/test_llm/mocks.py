import pytest
from unittest.mock import MagicMock, patch
from snc.domain.models import Model
from snc.domain.client_types import ClientType
from snc.infrastructure.llm.groq_llm_client import GroqLLMClient


@pytest.fixture
def mock_llm_client():
    """A fixture that returns a mock LLM client with parse_document, generate_code, fix_code methods."""
    mock_client = MagicMock()
    mock_client.parse_document.return_value = {"scenes": []}
    mock_client.generate_code.return_value = "mock code"
    mock_client.fix_code.return_value = "fixed code"
    return mock_client


@pytest.fixture
def mock_groq_client() -> MagicMock:
    """Create a mock Groq client for testing."""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=""))]
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_model_groq():
    """A simple Model instance for testing."""
    return Model(
        client_type=ClientType.GROQ,
        name="test-groq-model",
        context_window=8192,
        max_output_tokens=1024,
        prompt_cost_per_1k=0.005,
        completion_cost_per_1k=0.005,
        supports_images=False,
    )


@pytest.fixture
def groq_llm_client(
    mock_model_groq: Model, mock_groq_client: MagicMock, monkeypatch: pytest.MonkeyPatch
):
    """Create a GroqLLMClient with the Groq(...) usage patched."""
    with patch("snc.infrastructure.llm.groq_llm_client.Groq", return_value=mock_groq_client):
        yield GroqLLMClient(mock_model_groq)


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Create a mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock(message=MagicMock(content=""))]
    mock_client.chat.completions.create.return_value = mock_completion
    return mock_client


@pytest.fixture
def mock_model_openai():
    """A simple Model instance for testing."""
    return Model(
        client_type=ClientType.OPENAI,
        name="test-model",
        context_window=8192,
        max_output_tokens=1024,
        prompt_cost_per_1k=0.001,
        completion_cost_per_1k=0.002,
        supports_images=False,
    )


@pytest.fixture
def mock_groq_model() -> Model:
    """Create a mock Groq model for testing."""
    return Model(
        client_type=ClientType.GROQ,
        name="gemma2-9b-it",
        context_window=8192,
        max_output_tokens=4096,
        prompt_cost_per_1k=0.025,
        completion_cost_per_1k=0.05,
        supports_images=False,
    )


@pytest.fixture
def mock_openai_model() -> Model:
    """Create a mock OpenAI model for testing."""
    return Model(
        client_type=ClientType.OPENAI,
        name="gpt-4o-mini",
        context_window=128000,
        max_output_tokens=16384,
        prompt_cost_per_1k=0.0025,
        completion_cost_per_1k=0.01,
        supports_images=True,
    )
