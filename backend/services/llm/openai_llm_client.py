# openai_llm_client.py
import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from openai.types.completion_usage import CompletionUsage

from backend.env import getenv
from backend.services.llm.base_llm_client import BaseLLMClient
from backend.services.llm.model_factory import ModelFactory, ClientType, OpenAIModelType
from backend.models.llm_model import Model

def compute_cost_from_model(usage: CompletionUsage | dict, model: Model) -> float:
    if isinstance(usage, dict):
        prompt_tokens = usage["prompt_tokens"]  # type: ignore
        completion_tokens = usage["completion_tokens"]  # type: ignore
    else:
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens

    prompt_cost = Decimal(prompt_tokens) / Decimal(1000) * Decimal(model.prompt_cost_per_1k)
    completion_cost = Decimal(completion_tokens) / Decimal(1000) * Decimal(model.completion_cost_per_1k)
    return float(round(prompt_cost + completion_cost, 6))

class OpenAILLMClient(BaseLLMClient):
    """
    Client for interacting with OpenAI's LLM to generate code and parse narrative instructions.
    Uses the ModelFactory to select a model and determine costs.
    """
    def __init__(self, model_type: OpenAIModelType):
        super().__init__()
        self.client = OpenAI(api_key=getenv("OPENAI_API_KEY"))
        # Retrieve the model configuration from the factory
        self.model = ModelFactory.get_model(ClientType.OPENAI, model_type)

        self.last_usage: Optional[CompletionUsage] = None
        self.last_cost: float = 0.0

    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        system_message = {
            "role": "system",
            "content": (
                "You are a strict parser that reads a narrative instruction document and extracts scenes, components, and functions.\n"
                "Return ONLY JSON, no explanations.\n"
                "Every function MUST have a 'name' field.\n"
            ),
        }

        user_prompt = f"""
You are a parser that takes a narrative instruction document and extracts scenes, components, and functions.
Document:
{ni_content}
Now return the JSON.
"""
        user_message = {"role": "user", "content": user_prompt}

        response = self._generic_chat_call(
            system_message,
            user_message,
            model=self.model.name,  # Use model name from the Model object
            temperature=0,
            max_tokens=3000,
        )
        data = self._attempt_json_parse(response)

        if data is None or "scenes" not in data:
            logging.warning("Failed to parse JSON response.")
            return {"scenes": []}
        return data

    def generate_code(self, token_content: str, additional_requirements: str = "", code_style: str = "") -> str:
        system_message = {
            "role": "system",
            "content": (
                "You are a world-class coding assistant focused on generating high-quality, idiomatic, and secure "
                "TypeScript Angular components. Produce only the code with no extraneous explanations."
            ),
        }

        user_message_content = (
            f"Here is the narrative description of the component(s):\n```\n{token_content}\n```\n\n"
            f"Additional requirements:\n{additional_requirements}\n\n"
            f"Style guide:\n{code_style}\n\n"
            "Return only the code."
        )

        user_message = {"role": "user", "content": user_message_content}

        return self._generic_chat_call(system_message, user_message, model=self.model.name)

    def fix_code(self, original_code: str, error_summary: str) -> str:
        system_message = {
            "role": "system",
            "content": "You are a code-fixing assistant. Produce only corrected code."
        }

        user_message = {
            "role": "user",
            "content": (
                f"Current code:\n```\n{original_code}\n```\n"
                f"Errors:\n{error_summary}\n\n"
                "Fix these errors and return only the corrected code."
            )
        }

        return self._generic_chat_call(system_message, user_message, model=self.model.name)

    def _generic_chat_call(
        self,
        system_message: dict,
        user_message: dict,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        for attempt in range(3):
            try:
                messages = [
                    ChatCompletionSystemMessageParam(**system_message),
                    ChatCompletionUserMessageParam(**user_message),
                ]
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                self.last_usage = getattr(response, "usage", None)
                if self.last_usage is not None:
                    self.last_cost = compute_cost_from_model(self.last_usage, self.model)
                else:
                    self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
                    self.last_cost = 0.0

                return response.choices[0].message.content.strip()
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise RuntimeError("LLM call failed after 3 attempts.") from e
        raise RuntimeError("LLM call failed after 3 attempts.")
