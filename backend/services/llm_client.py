# backend/services/llm_client.py
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from backend.env import getenv

client = OpenAI(api_key=getenv("OPENAI_API_KEY"))

class LLMClient:
    @staticmethod
    def generate_code(token_content: str, 
                      additional_requirements: str = "", 
                      code_style: str = "Use consistent naming, strongly typed inputs, and follow Angular best practices.") -> str:
        """
        Generate code for the given token content using the OpenAI API, with enhanced prompt engineering.
        
        Args:
            token_content (str): Narrative instructions or component descriptions from the NI.
            additional_requirements (str): Extra instructions for code generation (optional).
            code_style (str): A stable style guide / set of coding conventions to always follow.
        """
        
        # Build a stable system message that sets a clear identity and long-term "persona" for the model.
        # This persona ensures the model always strives to produce the best possible code.
        # This message includes style guidance, a final directive about no explanations, and a mention of constraints.
        system_message = {
            "role": "system",
            "content": (
                "You are a world-class coding assistant focused on generating high-quality, idiomatic, and secure "
                "TypeScript Angular components. Your mission: Given a natural language description, produce only the code "
                "with no extraneous explanations. Always:\n\n"
                "* Maintain a clean, consistent style.\n"
                "* Use TypeScript strictly and follow Angular's best practices.\n"
                "* Strongly type all inputs and outputs.\n"
                "* Follow the user's stylistic preferences if given, else fallback to your stable style guide.\n\n"
                "If user instructions conflict, clarify by leaning towards correctness and maintainability.\n\n"
                "Under no circumstances produce explanations, comments outside code, or additional text not asked for.\n"
                "Only return the final code snippet.\n"
            ),
        }

        # Compose the user message. Include the token_content and additional requirements (if any).
        # Give a friendly but direct instruction to implement the requested component(s).
        user_message_content = (
            f"Here is the narrative description of the component(s):\n```\n{token_content}\n```\n\n"
            f"Additional requirements:\n{additional_requirements}\n\n"
            f"Please produce code now following the style guide:\n{code_style}\n\n"
            "Return only the code, no explanations."
        )

        user_message = {
            "role": "user",
            "content": user_message_content
        }

        return LLMClient._generic_chat_call(system_message, user_message)

    @staticmethod
    def fix_code(original_code: str, error_summary: str) -> str:
        """
        Prompt the LLM to fix given TypeScript code based on the provided error summary.
        Returns the corrected code.
        """
        # Enhanced persona and instructions for fixes:
        system_message = {
            "role": "system",
            "content": (
                "You are a code-fixing assistant. You've received a TypeScript Angular component that has errors. "
                "Your job is to produce corrected code that passes strict type checking, adheres to Angular best practices, "
                "and maintains the original structure as much as possible.\n\n"
                "Do not add explanations or commentary outside the code. Only return the final, corrected code snippet.\n"
            )
        }

        user_message = {
            "role": "user",
            "content": (
                f"Current code:\n```\n{original_code}\n```\n\n"
                f"Errors:\n{error_summary}\n\n"
                "Please fix these errors and return only the corrected code."
            )
        }

        return LLMClient._generic_chat_call(system_message, user_message)

    @staticmethod
    def _generic_chat_call(
        system_message: dict, 
        user_message: dict, 
        model: str = "gpt-4o-mini", 
        temperature: float = 0.7, 
        max_tokens: int = 1500
    ) -> str:
        # Now stable as before, but we rely on better prompts from above methods.
        for attempt in range(3):
            try:
                messages = [
                    ChatCompletionSystemMessageParam(**system_message),
                    ChatCompletionUserMessageParam(**user_message)
                ]
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if attempt == 2:
                    # On final attempt, re-raise the error
                    raise e
        raise RuntimeError("LLM call failed after 3 attempts.")