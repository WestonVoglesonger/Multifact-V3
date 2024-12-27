import json
import logging
import re
from decimal import Decimal
from typing import Optional, Dict, Any, List
from os import getenv
from dotenv import load_dotenv

from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from openai.types.completion_usage import CompletionUsage

from backend.domain.models import Model
from backend.infrastructure.llm.base_llm_client import BaseLLMClient

load_dotenv()


class OpenAILLMClient(BaseLLMClient):
    """
    A bracket-based LLM parser that ensures we never skip lines like
    [Scene:XYZ], [Component:ABC], or [Function:Foo]. Inherits from BaseLLMClient.
    """

    def __init__(self, model: Model):
        super().__init__(model)
        self.client = OpenAI(api_key=getenv("OPENAI_API_KEY"))

    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        """
        Attempt to parse bracket lines ([Scene:...], [Component:...], [Function:...])
        into a JSON object with scenes, components, and functions.

        Steps:
          1) Identify all bracket lines with a local regex (guaranteeing we know how many).
          2) Build a precise system prompt for the LLM.
          3) Call the LLM with temperature=0 for determinism.
          4) Attempt to parse JSON from LLM's output.
          5) Enforce that each bracket line is recognized (or at least warn if missing).
        """
        # 1) Identify bracket lines
        bracket_lines = self._extract_bracket_lines(ni_content)
        logging.debug(f"Found {len(bracket_lines)} bracket lines: {bracket_lines}")

        # 2) Build the system message
        system_message = {
            "role": "system",
            "content": (
                "You are a bracket-based parser. For each line in the document that matches:\n"
                "  [Scene:Name]\n"
                "  [Component:Name]\n"
                "  [Function:Name]\n"
                "you must produce exactly one JSON object.\n\n"
                "In your final JSON, each bracket line becomes:\n"
                "  - [Scene:X] => a new scene in the 'scenes' array, with name=X.\n"
                "  - [Component:Y] => a new component in the current scene's 'components' array, with name=Y.\n"
                "  - [Function:Z] => a new function in either the current component or the current scene's 'functions', with name=Z.\n"
                "The text after that bracket line, until the next bracket or doc end, is that bracket's 'narrative'.\n\n"
                "Return JSON in this shape:\n"
                "{\n"
                '  \"scenes\": [\n'
                "    {\n"
                '      \"name\": \"...\",\n'
                '      \"narrative\": \"...\",\n'
                '      \"functions\": [\n'
                '        { \"name\": \"...\", \"narrative\": \"...\" }, ...\n'
                "      ],\n"
                '      \"components\": [\n'
                "        {\n"
                '          \"name\": \"...\",\n'
                '          \"narrative\": \"...\",\n'
                '          \"functions\": [\n'
                '            { \"name\": \"...\", \"narrative\": \"...\" }, ...\n'
                "          ]\n"
                "        }, ...\n"
                "      ]\n"
                "    }, ...\n"
                "  ]\n"
                "}\n\n"
                "No disclaimers or extra text—only valid JSON.\n"
                "Do not skip any bracket lines. One bracket line = one object. If the user has two `[Function:...]` lines, we must have two function objects.\n"
            ),
        }
        # 3) Create the user message with the doc content
        user_prompt = f"Document:\n{ni_content}\n\nReturn bracket-based JSON."
        user_message = {"role": "user", "content": user_prompt}

        # 4) Call the LLM with temperature=0 for minimal creativity
        response_text = self._generic_chat_call(
            system_message=system_message,
            user_message=user_message,
            model_name=self.model.name,
            temperature=0,
            max_tokens=3000,
        )
        data = self._attempt_json_parse(response_text)
        if data is None or "scenes" not in data:
            logging.warning("LLM returned invalid or missing JSON for bracket lines.")
            return {"scenes": []}

        # 5) Check that each bracket line is recognized
        self._enforce_bracket_count(data, bracket_lines)

        return data

    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        """
        Provide an LLM code-generation call. Focuses on TypeScript Angular if needed.
        """
        system_message = {
            "role": "system",
            "content": (
                "You are a world-class coding assistant focused on generating high-quality, idiomatic, "
                "and secure TypeScript Angular components. Produce only the code with no extraneous explanations."
            ),
        }

        user_message_content = (
            f"Here is the narrative:\n```\n{token_content}\n```\n\n"
            f"Additional requirements:\n{additional_requirements}\n\n"
            f"Style:\n{code_style}\n\n"
            "Return only the code."
        )
        user_message = {"role": "user", "content": user_message_content}
        return self._generic_chat_call(
            system_message, user_message, model_name=self.model.name
        )

    def fix_code(self, original_code: str, error_summary: str) -> str:
        """
        Attempt to fix code with LLM. If fails after 3 attempts, raise an error.
        """
        system_message = {
            "role": "system",
            "content": (
                "You are a coding assistant. You have been given TypeScript code for an Angular component that contains errors. "
                "You must fix the code so that it passes strict type checking with `tsc`. "
                "Only return the fixed code, no explanations or extra output. Keep as much of the original structure as possible."
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Here is the current code:\n```\n{original_code}\n```\n\n"
                f"{error_summary}\n\n"
                "Please fix these errors and return only the corrected code."
            ),
        }

        for attempt in range(3):
            try:
                response = self._generic_chat_call(
                    system_message,
                    user_message,
                    model_name=self.model.name,
                    temperature=0.3,
                    max_tokens=1500,
                )
                if response:
                    return response.strip()
            except Exception as e:
                logging.error(f"Fix code attempt {attempt+1} failed: {e}")

        raise RuntimeError("Failed to get fixed code from LLM after 3 attempts.")

    def _generic_chat_call(
        self,
        system_message: Dict[str, Any],
        user_message: Dict[str, Any],
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        """
        Wraps an OpenAI ChatCompletion call, implementing the abstract method from BaseLLMClient.
        """
        import time

        for attempt in range(3):
            try:
                messages = [
                    ChatCompletionSystemMessageParam(**system_message),
                    ChatCompletionUserMessageParam(**user_message),
                ]
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )

                if not hasattr(response, "choices") or not response.choices:
                    raise RuntimeError("Invalid response structure from LLM")

                self.last_usage = getattr(response, "usage", None)
                if self.last_usage is not None:
                    self.last_cost = self.compute_cost_from_model(self.last_usage)
                else:
                    self.last_usage = {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }
                    self.last_cost = 0.0

                # Return the text content
                if (
                    hasattr(response.choices[0], "message")
                    and hasattr(response.choices[0].message, "content")
                ):
                    return response.choices[0].message.content.strip()
                else:
                    raise RuntimeError("Missing message content in response.")

            except Exception as e:
                logging.error(f"_generic_chat_call attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(1)  # small backoff
                else:
                    raise RuntimeError("LLM call failed after 3 attempts.") from e

        raise RuntimeError("LLM call failed after 3 attempts.")

    def compute_cost_from_model(self, usage: CompletionUsage) -> float:
        # Here `usage` is a pydantic model with direct attributes
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens
        
        # Then do your calculation:
        # (These rates are just an example.)
        prompt_cost = (prompt_tokens / 1000.0) * 0.003
        completion_cost = (completion_tokens / 1000.0) * 0.004
        return round(prompt_cost + completion_cost, 6)


    def _extract_bracket_lines(self, text: str) -> List[str]:
        """
        Finds lines that begin with [Scene:..., [Component:..., or [Function:...].
        Returns them as a list of raw lines.
        """
        lines = text.splitlines()
        bracket_pattern = re.compile(r"^\s*\[(Scene|Component|Function)\s*:\s*(.*?)\]\s*$")
        bracket_lines = []
        for line in lines:
            if bracket_pattern.match(line.strip()):
                bracket_lines.append(line.strip())
        return bracket_lines

    def _enforce_bracket_count(self, data: Dict[str, Any], bracket_lines: List[str]) -> None:
        """
        Check how many bracket lines we have vs how many total objects in the final JSON. 
        If there's a mismatch, we log a warning. We could also do fallback inserts, etc.
        """
        # Count how many actual bracket-based items the LLM returned
        scene_count = len(data.get("scenes", []))
        component_count = 0
        function_count = 0
        for scn in data["scenes"]:
            component_count += len(scn.get("components", []))
            function_count += len(scn.get("functions", []))
            for comp in scn["components"]:
                function_count += len(comp.get("functions", []))

        recognized_count = scene_count + component_count + function_count
        expected_count = len(bracket_lines)
        if recognized_count < expected_count:
            logging.warning(
                f"LLM returned fewer bracket objects ({recognized_count}) than bracket lines ({expected_count})."
                "Some bracket lines might be missing in the final JSON."
            )
            # Optionally you could do a fallback approach to forcibly add placeholders
            # for missing bracket lines. But we'll only log a warning for now.
        elif recognized_count > expected_count:
            logging.warning(
                f"LLM returned more bracket objects ({recognized_count}) than bracket lines ({expected_count})."
                "Might have duplicates or spurious objects."
            )
        else:
            logging.debug("Bracket lines match the LLM's final JSON object count perfectly!")
