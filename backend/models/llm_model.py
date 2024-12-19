from dataclasses import dataclass
from typing import Optional

@dataclass
class Model:
    name: str
    context_window: int
    max_output_tokens: int
    prompt_cost_per_1k: float
    completion_cost_per_1k: float
    supports_images: bool
    reasoning_tokens: Optional[float] = None
    knowledge_cutoff_date: Optional[str] = None
    supports_audio: bool = False
    supports_video: bool = False
    supports_reasoning: bool = False
    # Additional metadata as needed