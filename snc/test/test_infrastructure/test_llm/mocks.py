import pytest
from unittest.mock import MagicMock, patch
from snc.domain.models import Model
from snc.infrastructure.llm.model_factory import ClientType
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
def mock_groq_client():
    """Mock object for the `Groq` client used inside `GroqLLMClient`."""
    mock_client = MagicMock()
    # .create(...) returns an object with 'choices', each with .message.content
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="{}"))], usage=None
    )
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
    with patch(
        "snc.infrastructure.llm.groq_llm_client.Groq", return_value=mock_groq_client
    ):
        yield GroqLLMClient(mock_model_groq)


@pytest.fixture
def mock_openai_client():
    """Mock object for the `OpenAI` client used inside `OpenAILLMClient`."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="{}"))],
        usage=None,  # or put usage data if you want to test cost calculations
    )
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
