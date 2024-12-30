# File: backend/infrastructure/llm/groq_llm_client.py

import json
import logging
from decimal import Decimal
from typing import Optional, Dict, Any, cast
from os import getenv

from dotenv import load_dotenv
from groq import Groq
from groq.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionMessageParam,
)
from openai.types.completion_usage import CompletionUsage

from snc.domain.models import Model
from snc.application.interfaces.illm_client import ILLMClient

load_dotenv()


class GroqLLMClient(ILLMClient):
    """
    Client for interacting with Groq's LLM to generate code and parse narrative instructions,
    using ModelFactory and the specified model type.
    """

    def __init__(self, model: Model):
        super().__init__(model)
        self.client = Groq(api_key=getenv("GROQ_API_KEY"))
        self.last_usage: Optional[CompletionUsage] = None

    def parse_document(self, ni_content: str) -> Dict[str, Any]:
        system_message = {
            "content": (
                "You are a bracket-based parser. Whenever you see `[Function:XYZ]`, you must create an object in "
                "`functions` array with `name=XYZ` and `narrative` = lines until the next bracket.\n"
                "If there's no `[Component:Name]` open, put this function in the scene's `functions`. No discarding.\n\n"
                "Specifically:\n"
                "  - `[Scene:Name]`: Creates a JSON object in `scenes` array.\n"
                "    The text after that bracket (until the next bracket) is its `narrative`.\n\n"
                "  - `[Component:Name]`: Creates a JSON object in the scene's `components` array.\n"
                "    The text after that bracket is that component's `narrative`, until the next bracket.\n\n"
                "  - `[Function:Name]`: If we already have a `component`, put this new function in that component's `functions`.\n"
                "    Otherwise, if no component is open, put this function in the `functions` array of the **scene** itself.\n"
                "    The text after that bracket is its `narrative`, until the next bracket.\n\n"
                "You must return JSON in the shape:\n"
                "{\n"
                '  "scenes": [\n'
                "    {\n"
                '      "name": "...",\n'
                '      "narrative": "...",\n'
                '      "functions": [\n'
                '        { "name": "...", "narrative": "..." }, ...\n'
                "      ],\n"
                '      "components": [\n'
                "        {\n"
                '          "name": "...",\n'
                '          "narrative": "...",\n'
                '          "functions": [\n'
                '            { "name": "...", "narrative": "..." }, ...\n'
                "          ]\n"
                "        }, ...\n"
                "      ]\n"
                "    }, ...\n"
                "  ]\n"
                "}\n\n"
                "You must never create a `component` named `Function:XYZ` unless the bracket actually said `[Component:Function:XYZ]`.\n"
                "Instead, `[Function:Name]` belongs in a `functions` array on either the current component or the current scene.\n"
                "No extra disclaimers or keys, only valid JSON.\n"
            )
        }

        user_prompt = f"""
            You are a parser for scenes, components, and functions.
            Document:
            {ni_content}
            Now return the JSON with the structure described above.
        """
        user_message = {"content": user_prompt}

        response = self._generic_chat_call(
            system_message,
            user_message,
            model_name=self.model.name,
            temperature=0,
            max_tokens=3000,
        )
        data = self._attempt_json_parse(response)

        if data is None or "scenes" not in data:
            logging.warning("Failed to parse JSON response.")
            return {"scenes": []}

        # Debug: Print the raw parsed JSON
        logging.debug(f"Parsed JSON from LLM: {json.dumps(data, indent=2)}")

        # Post-process to extract inline [Function:XYZ] calls from the scene's narrative
        for scene in data.get("scenes", []):
            lines = scene["narrative"].splitlines()
            new_functions = scene.get("functions", []) or []
            cleaned_lines = []
            collecting_func = False
            func_lines: list[str] = []
            func_name = ""

            for line in lines:
                stripped = line.strip()
                if stripped.startswith("[Function:") and stripped.endswith("]"):
                    # Extract function name
                    bracket = stripped.lstrip("[").rstrip("]")
                    parts = bracket.split(":", maxsplit=1)
                    if len(parts) == 2 and parts[0].lower() == "function":
                        func_name = parts[1].strip()
                        collecting_func = True
                        func_lines = []
                        logging.debug(f"Detected function start: {func_name}")
                    else:
                        # Not a valid function bracket, keep the line
                        cleaned_lines.append(line)
                elif collecting_func:
                    if stripped.startswith("[") and stripped.endswith("]"):
                        # Found another bracket, finalize current function
                        if func_name and func_lines:
                            function_narrative = "\n".join(func_lines).strip()
                            new_functions.append(
                                {
                                    "name": func_name,
                                    "narrative": function_narrative,
                                }
                            )
                            logging.debug(f"Finalized function: {func_name}")
                        # Reset function collection
                        collecting_func = False
                        func_name = ""
                        func_lines = []
                        # Reprocess this bracket line
                        cleaned_lines.append(line)
                    else:
                        # Continue collecting function lines
                        func_lines.append(line)
                        logging.debug(f"Collecting function line: {line.strip()}")
                else:
                    # Normal line, not part of a function
                    cleaned_lines.append(line)

            # After loop, check if a function is still being collected
            if collecting_func and func_name and func_lines:
                function_narrative = "\n".join(func_lines).strip()
                new_functions.append(
                    {
                        "name": func_name,
                        "narrative": function_narrative,
                    }
                )
                logging.debug(f"Finalized function at end of narrative: {func_name}")

            # Update scene's functions and narrative
            scene["functions"] = new_functions
            scene["narrative"] = "\n".join(cleaned_lines)

            logging.debug(f"Updated scene '{scene['name']}' with functions: {scene['functions']}")

        # Debug: Print the final JSON after post-processing
        logging.debug(f"Final JSON after post-processing: {json.dumps(data, indent=2)}")

        return data

    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        system_message = {
            "content": "You are a world-class coding assistant.\nReturn only code.",
        }

        user_message_content = (
            f"Component instructions:\n```\n{token_content}\n```\n"
            f"Extra reqs:\n{additional_requirements}\n"
            f"Style:\n{code_style}\n"
            "Only code."
        )

        user_message = {"content": user_message_content}
        return self._generic_chat_call(system_message, user_message, model_name=self.model.name)

    def fix_code(self, original_code: str, error_summary: str) -> str:
        system_message = {
            "content": (
                "You are a coding assistant. You have been given TypeScript code for an Angular component that contains errors. "
                "You must fix the code so that it passes strict type checking with `tsc`. "
                "Only return the fixed code, no explanations or extra output. Keep as much of the original structure as possible."
            )
        }

        user_message = {
            "content": (
                f"Here is the current code:\n```\n{original_code}\n```\n\n"
                f"{error_summary}\n\n"
                "Please fix these errors and return only the corrected code."
            ),
        }

        # Attempt LLM call up to 3 times
        for attempt in range(3):
            try:
                response = self._generic_chat_call(
                    system_message,
                    user_message,
                    model_name=self.model.name,
                )
                if response is not None:
                    return response.strip()
            except Exception:
                # Handle any exceptions from the LLM call
                pass

        # If we get here, all attempts failed
        raise RuntimeError("Failed to get fixed code from LLM after 3 attempts.")

    def _generic_chat_call(
        self,
        system_message: Dict[str, str],  # or more specific TypedDict if you like
        user_message: Dict[str, str],
        model_name: str,
        temperature: float = 0.7,
        max_tokens: int = 1500,
    ) -> str:
        """
        A generic helper that sends system & user messages to the Groq LLM and returns the response.
        """
        for attempt in range(3):
            try:
                # Build typed message params
                sys_msg = ChatCompletionSystemMessageParam(
                    role="system", content=system_message["content"]
                )
                usr_msg = ChatCompletionUserMessageParam(
                    role="user", content=user_message["content"]
                )

                # Now Mypy / Pyright sees a list of properly typed message objects
                messages: list[
                    ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam
                ] = [sys_msg, usr_msg]

                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                if not hasattr(response, "choices") or not response.choices:
                    raise RuntimeError("Invalid response structure from Groq API")

                usage_dict = getattr(response, "usage", None)
                if usage_dict:
                    self.last_usage = CompletionUsage(
                        prompt_tokens=usage_dict.prompt_tokens,
                        completion_tokens=usage_dict.completion_tokens,
                        total_tokens=usage_dict.total_tokens,
                    )
                else:
                    self.last_usage = CompletionUsage(
                        prompt_tokens=0, completion_tokens=0, total_tokens=0
                    )

                if hasattr(response.choices[0], "message") and hasattr(
                    response.choices[0].message, "content"
                ):
                    content = response.choices[0].message.content
                    return content.strip() if content else ""
                else:
                    raise RuntimeError("Invalid response structure: missing content")

            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt == 2:
                    raise RuntimeError("LLM call failed after 3 attempts.") from e

        raise RuntimeError("LLM call failed after 3 attempts.")

    def compute_cost_from_model(self, usage: CompletionUsage) -> float:
        """
        Compute the cost of a given usage dictionary based on the model's pricing.
        """
        prompt_tokens = usage.prompt_tokens
        completion_tokens = usage.completion_tokens

        prompt_cost = (
            Decimal(prompt_tokens) / Decimal(1000) * Decimal(self.model.prompt_cost_per_1k)
        )
        completion_cost = (
            Decimal(completion_tokens) / Decimal(1000) * Decimal(self.model.completion_cost_per_1k)
        )
        return float(round(prompt_cost + completion_cost, 6))

    def _attempt_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse `text` as JSON. If parsing fails, return None.
        """
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            logging.error("Failed to decode JSON from LLM output.")
            return None
