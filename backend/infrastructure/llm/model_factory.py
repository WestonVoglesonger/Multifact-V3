from enum import Enum

from backend.domain.models import Model
from backend.domain.model_types import GroqModelType, OpenAIModelType


BaseModelType = GroqModelType | OpenAIModelType

class ClientType(Enum):
    """
    Enumeration of supported LLM clients.

    - OPENAI: Models and endpoints associated with OpenAI.
    - GROQ: Models and endpoints offered by the Groq service.
    """
    OPENAI = "openai"
    GROQ = "groq"

class ModelFactory:
    """
    A factory class to retrieve Model instances based on the client (OpenAI or GROQ)
    and a specified model type (from the respective enums).

    This class acts as a centralized registry for model configurations,
    including context windows, token limits, pricing, and feature support.
    """
    OPENAI_MODELS = {
        OpenAIModelType.GPT_4O: Model(
            client_type=ClientType.OPENAI,
            name="gpt-4o",
            context_window=128000,
            max_output_tokens=16384,
            prompt_cost_per_1k=0.0025,
            completion_cost_per_1k=0.01,
            supports_images=True,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        OpenAIModelType.GPT_4O_MINI: Model(
            client_type=ClientType.OPENAI,
            name="gpt-4o-mini",
            context_window=128000,
            max_output_tokens=16384,
            prompt_cost_per_1k=0.00015,
            completion_cost_per_1k=0.0006,
            supports_images=True,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        OpenAIModelType.O1: Model(
            client_type=ClientType.OPENAI,
            name="o1",
            context_window=200000,
            max_output_tokens=100000,
            prompt_cost_per_1k=0.015,
            completion_cost_per_1k=0.06,
            supports_images=True,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=True,
            knowledge_cutoff_date="2023-10-01"
        ),
        OpenAIModelType.O1_MINI: Model(
            client_type=ClientType.OPENAI,
            name="o1-mini",
            context_window=128000,
            max_output_tokens=65536,
            prompt_cost_per_1k=0.003,
            completion_cost_per_1k=0.012,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=True,
            knowledge_cutoff_date="2023-10-01"
        )
    }

    GROQ_MODELS = {
        GroqModelType.GEMMA2_9B_IT: Model(
            client_type=ClientType.GROQ,
            name="gemma2-9b-it",
            context_window=8192,
            max_output_tokens=4096,
            prompt_cost_per_1k=0.025,
            completion_cost_per_1k=0.05,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.LLAMA_3_3_70B_VERSATILE: Model(
            client_type=ClientType.GROQ,
            name="llama-3.3-70b-versatile",
            context_window=128000,
            max_output_tokens=32768,
            prompt_cost_per_1k=0.00059,
            completion_cost_per_1k=0.00079,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.LLAMA_3_1_8B_INSTANT: Model(
            client_type=ClientType.GROQ,
            name="llama-3.1-8b-instant",
            context_window=128000,
            max_output_tokens=8192,
            prompt_cost_per_1k=0.00005,
            completion_cost_per_1k=0.00008,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.LLAMA_GUARD_3_8B: Model(
            client_type=ClientType.GROQ,
            name="llama-guard-3-8b",
            context_window=8192,
            max_output_tokens=4096,
            prompt_cost_per_1k=0.0002,
            completion_cost_per_1k=0.0002,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.LLAMA3_70B_8192: Model(
            client_type=ClientType.GROQ,
            name="llama3-70b-8192",
            context_window=8192,
            max_output_tokens=4096,
            prompt_cost_per_1k=0.00059,
            completion_cost_per_1k=0.00079,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.LLAMA3_8B_8192: Model(
            client_type=ClientType.GROQ,
            name="llama3-8b-8192",
            context_window=8192,
            max_output_tokens=4096,
            prompt_cost_per_1k=0.00005,
            completion_cost_per_1k=0.00008,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        ),
        GroqModelType.MIXTRAL_8X7B_32768: Model(
            client_type=ClientType.GROQ,
            name="mixtral-8x7b-32768",
            context_window=32768,
            max_output_tokens=4096,
            prompt_cost_per_1k=0.00024,
            completion_cost_per_1k=0.00024,
            supports_images=False,
            supports_audio=False,
            supports_video=False,
            supports_reasoning=False,
            knowledge_cutoff_date="2023-10-01"
        )
    }

    @staticmethod
    def get_model(client_type: ClientType, model_type: Enum) -> Model:
        """
        Retrieve a Model instance based on the given client type and model type.

        Args:
            client_type (ClientType): The type of client (OPENAI or GROQ).
            model_type (Enum): The specific model type from the respective enum.

        Returns:
            Model: A configured Model instance.

        Raises:
            ValueError: If the provided model type is not known for the given client,
                        or if the client type is unsupported.
        """
        if client_type == ClientType.OPENAI:
            if model_type in ModelFactory.OPENAI_MODELS:
                return ModelFactory.OPENAI_MODELS[model_type]
            else:
                raise ValueError(f"Unknown OpenAI model type: {model_type}")
        elif client_type == ClientType.GROQ:
            if model_type in ModelFactory.GROQ_MODELS:
                return ModelFactory.GROQ_MODELS[model_type]
            else:
                raise ValueError(f"Unknown Groq model type: {model_type}")
        else:
            raise ValueError(f"Unsupported client type: {client_type}")