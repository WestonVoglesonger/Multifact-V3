from typing import Dict, Any, Optional
import json
import logging

from backend.infrastructure.llm.base_llm_client import BaseLLMClient


class CodeEvaluationService:
    """
    This service asks a *different* LLM to evaluate or score the code that was produced
    by your main code-generation flow. The evaluator LLM is expected to return structured
    JSON with 'score' (1-10) and 'feedback'.
    """

    def __init__(self, evaluator_llm: BaseLLMClient):
        """
        :param evaluator_llm: A BaseLLMClient that is different from the one used
                              for code generation/fixing (e.g. OpenAIModelType.O1_MINI).
        """
        self.evaluator_llm = evaluator_llm
        self.logger = logging.getLogger(__name__)

    def evaluate_code(
        self, code: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calls the second LLM to evaluate the given code (TypeScript, Angular, etc.).
        Expects JSON output with at least 'score' and 'feedback'.
        Returns a dict, e.g. {"score": 8.5, "feedback": "..."}.

        :param code: The compiled code to be evaluated.
        :param context: (Optional) Additional data to pass to the LLM (like doc name, etc.)
        :return: A dict with keys 'score' (float) and 'feedback' (str).
        """
        if context is None:
            context = {}

        # The system message defines the role of the LLM as a code reviewer.
        system_message = {
            "role": "system",
            "content": (
                "You are a code evaluation assistant. You MUST respond with ONLY a JSON object in this format:\n"
                '{"score": <number 0-10>, "feedback": "<brief feedback>"}\n'
                'Example: {"score": 8.5, "feedback": "Good code structure but missing error handling"}\n'
                "Analyze the code for correctness, style, and clarity."
            ),
        }

        user_content = f"""Here is the code to evaluate:
{code}

Context (if any): {json.dumps(context, indent=2)}

Please respond with a JSON object, e.g.:
{{
  "score": 9.1,
  "feedback": "Short summary here."
}}
"""
        user_message = {"role": "user", "content": user_content}

        try:
            response_text = self.evaluator_llm._generic_chat_call(
                system_message=system_message,
                user_message=user_message,
                model_name=self.evaluator_llm.model.name,
                temperature=0.3,
                max_tokens=1000,
            )
            print(f"DEBUG - Raw LLM response: {response_text}")

            # Attempt to parse JSON
            try:
                parsed = json.loads(response_text)
                if not isinstance(parsed, dict):
                    raise ValueError(f"Expected dict, got {type(parsed)}")
                if "score" not in parsed or "feedback" not in parsed:
                    raise ValueError(f"Missing required fields. Got: {parsed}")
                return parsed
            except Exception as parse_err:
                return {
                    "score": 0,
                    "feedback": f"Parse error: {str(parse_err)}. Raw: {response_text[:100]}",
                }
        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            self.logger.error(error_msg)
            return {"score": 0, "feedback": error_msg}
