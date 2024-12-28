from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


class OpenAIModelType(Enum):
    """
    Enumeration of available OpenAI model types.

    - GPT_4O: The versatile, high-intelligence GPT-4o model with large context.
    - GPT_4O_MINI: A faster, more cost-effective smaller variant of GPT-4o.
    - O1: A reasoning-focused model that can think before answering and handle tools.
    - O1_MINI: A smaller, more efficient variant of O1 optimized for reasoning.
    """

    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    O1 = "o1"
    O1_MINI = "o1-mini"


class GroqModelType(Enum):
    """
    Enumeration of available Groq model types.

    - GEMMA2_9B_IT: A 9-billion parameter model from Google (Gemma2) with an 8K context.
    - GEMMA_7B_IT: A 7-billion parameter Gemma model (deprecated) with 8K context.
    - LLAMA_3_3_70B_VERSATILE: A 70B parameter Llama 3.3 variant with a large context window.
    - LLAMA_3_1_8B_INSTANT: A smaller, faster Llama 3.1 8B model with a large context.
    - LLAMA_GUARD_3_8B: A guarded Llama 3-based model focusing on security and reliability.
    - LLAMA3_70B_8192: Another 70B Llama 3 model variant specialized for an 8K context.
    - LLAMA3_8B_8192: An 8B Llama 3 model variant with 8K context support.
    - MIXTRAL_8X7B_32768: A Mistral-based model with a large 32K context window.
    """

    GEMMA2_9B_IT = "gemma2-9b-it"
    GEMMA_7B_IT = "gemma-7b-it"
    LLAMA_3_3_70B_VERSATILE = "llama-3.3-70b-versatile"
    LLAMA_3_1_8B_INSTANT = "llama-3.1-8b-instant"
    LLAMA_GUARD_3_8B = "llama-guard-3-8b"
    LLAMA3_70B_8192 = "llama3-70b-8192"
    LLAMA3_8B_8192 = "llama3-8b-8192"
    MIXTRAL_8X7B_32768 = "mixtral-8x7b-32768"


@dataclass
class CompilationResult:
    """
    Result of a compilation operation.
    """

    code: str
    valid: bool
    errors: Optional[List[str]] = None
    created_at: datetime = datetime.now()
    cache_hit: bool = False
    score: Optional[float] = None
    feedback: Optional[str] = None
