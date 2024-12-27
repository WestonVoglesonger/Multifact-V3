from pydantic import BaseModel
from typing import Optional
from backend.infrastructure.llm.model_factory import ClientType

class Model(BaseModel):
    # If ClientType is an Enum, we can reference it directly:
    client_type: ClientType
    name: str
    context_window: int
    max_output_tokens: int
    prompt_cost_per_1k: float
    completion_cost_per_1k: float
    supports_images: bool

    # Optional fields with defaults
    reasoning_tokens: Optional[float] = None
    knowledge_cutoff_date: Optional[str] = None
    supports_audio: bool = False
    supports_video: bool = False
    supports_reasoning: bool = False
