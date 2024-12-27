from datetime import datetime, timezone
from backend.domain.models import Model

def test_model_init_minimal():
    """
    Verify the Model class can be constructed with minimal required parameters.
    """
    from enum import Enum

    class DummyClientType(Enum):
        GROQ = "groq"

    model_obj = Model(
        client_type=DummyClientType.GROQ,  
        name="dummy-model",
        context_window=4096,
        max_output_tokens=1000,
        prompt_cost_per_1k=0.02,
        completion_cost_per_1k=0.03,
        supports_images=False
    )

    assert model_obj.client_type == DummyClientType.GROQ
    assert model_obj.name == "dummy-model"
    assert model_obj.context_window == 4096
    assert model_obj.max_output_tokens == 1000
    assert model_obj.prompt_cost_per_1k == 0.02
    assert model_obj.completion_cost_per_1k == 0.03
    assert model_obj.supports_images is False
    assert model_obj.knowledge_cutoff_date is None
    assert model_obj.supports_audio is False
    assert model_obj.supports_reasoning is False


def test_model_init_full():
    """
    Verify the Model class handles optional fields.
    """
    from enum import Enum

    class DummyClientType(Enum):
        GROQ = "groq"

    now = datetime.now(timezone.utc)
    model_obj = Model(
        client_type=DummyClientType.GROQ,
        name="some-groq-model",
        context_window=8192,
        max_output_tokens=32768,
        prompt_cost_per_1k=0.00059,
        completion_cost_per_1k=0.00079,
        supports_images=True,
        reasoning_tokens=1000.5,
        knowledge_cutoff_date="2024-01-01",
        supports_audio=True,
        supports_video=True,
        supports_reasoning=True
    )

    assert model_obj.client_type == DummyClientType.GROQ
    assert model_obj.name == "some-groq-model"
    assert model_obj.context_window == 8192
    assert model_obj.max_output_tokens == 32768
    assert model_obj.prompt_cost_per_1k == 0.00059
    assert model_obj.completion_cost_per_1k == 0.00079
    assert model_obj.supports_images is True
    assert model_obj.reasoning_tokens == 1000.5
    assert model_obj.knowledge_cutoff_date == "2024-01-01"
    assert model_obj.supports_audio is True
    assert model_obj.supports_video is True
    assert model_obj.supports_reasoning is True
