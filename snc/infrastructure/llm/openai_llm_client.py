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

from snc.domain.models import Model
from snc.application.interfaces.illm_client import ILLMClient

load_dotenv()


class OpenAILLMClient(ILLMClient):
    """
    A bracket-based LLM parser that ensures we never skip lines like
    [Scene:XYZ], [Component:ABC], or [Function:Foo]. Implements ILLMClient interface.
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
        # 1) Identify bracket lines and their content
        bracket_lines = self._extract_bracket_lines(ni_content)
        logging.debug(f"Found {len(bracket_lines)} bracket lines: {bracket_lines}")

        # Extract content for each bracket line
        lines = ni_content.split("\n")
        bracket_content = {}
        current_bracket = None
        current_content = []

        for line in lines:
            line = line.strip()
            if line.startswith("[") and "]" in line:
                if current_bracket:
                    bracket_content[current_bracket] = "\n".join(current_content).strip()
                current_bracket = line
                current_content = []
            elif current_bracket:
                current_content.append(line)

        if current_bracket:
            bracket_content[current_bracket] = "\n".join(current_content).strip()

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
                "No disclaimers or extra text—only valid JSON.\n"
                "Do not skip any bracket lines. One bracket line = one object. If the user has two `[Function:...]` lines, we must have two function objects.\n"
            ),
        }
        # 3) Create the user message with the doc content and content mapping
        user_prompt = f"Document:\n{ni_content}\n\nContent mapping:\n{json.dumps(bracket_content, indent=2)}\n\nReturn bracket-based JSON."
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

        # 6) Add raw text to each component for token creation
        for scene in data.get("scenes", []):
            for component in scene.get("components", []):
                component_line = f"[Component:{component['name']}]"
                if component_line in bracket_content:
                    component["raw_text"] = f"{component_line}\n{bracket_content[component_line]}"

        return data

    def _extract_target_name(self, token_content: str) -> str:
        """Extract the target name from token content.

        Args:
            token_content: Content to extract name from, can be in bracketed or non-bracketed format

        Returns:
            str: Extracted target name

        Raises:
            ValueError: If target name cannot be extracted
        """
        if not token_content or not token_content.strip():
            raise ValueError("Token content is empty")

        # Try to find Scene:Name, Component:Name, or Function:Name in brackets
        patterns = [
            r"\[Scene:(\w+)\]",
            r"\[Component:(\w+)\]",
            r"\[Function:(\w+)\]",
            r"\[Service:(\w+)\]",
            r"\[Interface:(\w+)\]",
            r"\[Type:(\w+)\]",
        ]

        # First try bracketed format
        for pattern in patterns:
            match = re.search(pattern, token_content)
            if match:
                name = match.group(1)
                print(f"Found name: {name} using pattern: {pattern}")
                return name

        # Try non-bracketed format (e.g. "Scene: MainScene")
        non_bracketed_patterns = [
            r"Scene:\s*(\w+)",
            r"Component:\s*(\w+)",
            r"Function:\s*(\w+)",
            r"Service:\s*(\w+)",
            r"Interface:\s*(\w+)",
            r"Type:\s*(\w+)",
        ]

        for pattern in non_bracketed_patterns:
            match = re.search(pattern, token_content)
            if match:
                name = match.group(1)
                print(f"Found name: {name} using non-bracketed pattern: {pattern}")
                return name

        # If no match found, try to find it in the first line
        first_line = token_content.split("\n")[0].strip()
        if ":" in first_line:
            name = first_line.split(":")[-1].strip()
            if name and name.isalnum():  # Ensure name is valid
                print(f"Found name from first line: {name}")
                return name

        raise ValueError(
            f"Could not extract target name from token content: {token_content[:100]}..."
        )

    def _post_process_code(self, code: str, target_name: str, code_type: str) -> str:
        """Post-process the generated code to enforce correct names and structure."""
        if not target_name:
            raise ValueError("Target name cannot be None or empty")

        # Remove any explanatory text after the code
        code = re.sub(r"\n\s*Please note.*$", "", code, flags=re.MULTILINE | re.DOTALL)
        code = re.sub(r"\n\s*This code.*$", "", code, flags=re.MULTILINE | re.DOTALL)
        code = re.sub(r"\n\s*Note:.*$", "", code, flags=re.MULTILINE | re.DOTALL)

        # Fix component name in class declaration
        code = re.sub(r"export class \w+", f"export class {target_name}", code)

        # Fix component name in decorator
        selector_name = "".join(
            ["-" + c.lower() if c.isupper() else c for c in target_name]
        ).lstrip("-")
        code = re.sub(r"selector:\s*\'[^\']+\'", f"selector: 'app-{selector_name}'", code)
        code = re.sub(
            r"templateUrl:\s*\'[^\']+\'",
            f"templateUrl: './{selector_name}.component.html'",
            code,
        )
        code = re.sub(
            r"styleUrls:\s*\[[^\]]+\]",
            f"styleUrls: ['./{selector_name}.component.css']",
            code,
        )

        return code.strip()

    def generate_code(
        self,
        token_content: str,
        additional_requirements: str = "",
        code_style: str = "",
    ) -> str:
        """
        Provide an LLM code-generation call. Focuses on TypeScript Angular if needed.
        """
        # Extract the target name first
        target_name = self._extract_target_name(token_content)

        system_message = {
            "role": "system",
            "content": (
                "You are a world-class coding assistant specializing in TypeScript and Angular development. "
                "You must ONLY return the TypeScript/Angular code. NO explanations, NO comments outside the code, NO disclaimers.\n\n"
                "Rules:\n"
                "1. Use TypeScript 4.8+ with strict mode\n"
                "2. Follow Angular 15+ best practices\n"
                "3. Use proper dependency injection\n"
                "4. Initialize all properties\n"
                "5. Use OnPush change detection\n"
                "6. Add error handling\n"
                "7. Add loading states\n"
                "8. Use async/await\n"
                "9. Add JSDoc comments\n"
                "10. Make all properties strongly typed\n\n"
                "IMPORTANT: Return ONLY the code. No explanations before or after. No disclaimers. No apologies."
            ),
        }

        # Determine the type of code to generate
        code_type = "component"
        if "Scene:" in token_content:
            code_type = "scene"
        elif "Function:" in token_content:
            code_type = "function"

        # Add specific guidance based on code type
        type_specific_guidance = {
            "scene": (
                f"Create a scene named {target_name} that includes:\n"
                "- NgRx store integration\n"
                "- Virtual scrolling\n"
                "- Real-time updates\n"
                "- Error boundaries\n"
                "- Loading states"
            ),
            "component": (
                f"Create a component named {target_name} that includes:\n"
                "- OnPush change detection\n"
                "- Lifecycle hooks\n"
                "- Error handling\n"
                "- Loading states"
            ),
            "function": (
                f"Create a service named {target_name} that includes:\n"
                "- Dependency injection\n"
                "- Error handling\n"
                "- Strong typing"
            ),
        }

        user_message_content = (
            f"Generate {code_type} code for {target_name}.\n\n"
            f"Requirements:\n{token_content}\n\n"
            f"{type_specific_guidance[code_type]}\n\n"
            "Return ONLY the TypeScript code. No explanations. No disclaimers."
        )
        user_message = {"role": "user", "content": user_message_content}

        # Use lower temperature for more consistent output
        response = self._generic_chat_call(
            system_message,
            user_message,
            model_name=self.model.name,
            temperature=0.2,
            max_tokens=2000,
        )

        # Clean up code block markers and any explanatory text
        response = re.sub(
            r"```(?:\w+)?\s*\n?", "", response
        )  # Remove opening markers with optional language
        response = re.sub(r"\n?```\s*", "", response)  # Remove closing markers
        response = re.sub(
            r"^I\'m sorry.*?\n", "", response, flags=re.MULTILINE | re.DOTALL
        )  # Remove apologies
        response = re.sub(
            r"^Please note.*?\n", "", response, flags=re.MULTILINE | re.DOTALL
        )  # Remove notes
        response = re.sub(
            r"^Note:.*?\n", "", response, flags=re.MULTILINE | re.DOTALL
        )  # Remove notes
        response = re.sub(
            r"^Here.*?\n", "", response, flags=re.MULTILINE | re.DOTALL
        )  # Remove intros
        response = re.sub(
            r"^Based on.*?\n", "", response, flags=re.MULTILINE | re.DOTALL
        )  # Remove explanations
        response = response.strip()

        # Post-process the code to enforce correct names and structure
        return self._post_process_code(response, target_name, code_type)

    def fix_code(self, original_code: str, error_summary: str) -> str:
        """
        Attempt to fix code with LLM. If fails after 3 attempts, raise an error.
        """
        system_message = {
            "role": "system",
            "content": (
                "You are a coding assistant. You have been given TypeScript code for an Angular component that contains errors. "
                "You must fix the code so that it passes strict type checking with `tsc`. "
                "Return only the fixed TypeScript code without any markdown code block markers or explanations. "
                "Keep as much of the original structure as possible."
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Here is the current code:\n{original_code}\n\n"
                f"{error_summary}\n\n"
                "Return only the fixed TypeScript code without any markdown code block markers."
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
                    # Clean up any remaining code block markers
                    response = re.sub(r"^```\w*\s*", "", response)
                    response = re.sub(r"\s*```$", "", response)
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
        Wraps an OpenAI ChatCompletion call to handle common functionality for all LLM requests.
        """
        import time
        import logging

        for attempt in range(3):
            try:
                messages = [
                    ChatCompletionSystemMessageParam(**system_message),
                    ChatCompletionUserMessageParam(**user_message),
                ]
                actual_model_name = self.model.name
                logging.debug(f"Using model name: {actual_model_name}")
                response = self.client.chat.completions.create(
                    model=actual_model_name,
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
                    self.last_usage = CompletionUsage(
                        prompt_tokens=0, completion_tokens=0, total_tokens=0
                    )
                    self.last_cost = 0.0

                # Return the text content
                if hasattr(response.choices[0], "message") and hasattr(
                    response.choices[0].message, "content"
                ):
                    content = response.choices[0].message.content
                    return content.strip() if content is not None else ""
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
        for scn in data.get("scenes", []):
            component_count += len(scn.get("components", []))
            function_count += len(scn.get("functions", []))
            # Also check components for nested functions
            for comp in scn.get("components", []):
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

    def _attempt_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse JSON from the LLM's response text.
        """
        try:
            # First try to parse as-is
            return json.loads(text)
        except json.JSONDecodeError:
            # If that fails, try to find JSON between triple backticks
            json_pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
            matches = re.findall(json_pattern, text)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    pass
            return None
