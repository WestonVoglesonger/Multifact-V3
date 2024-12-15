# backend/services/llm_client.py
from openai import OpenAI
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from backend.env import getenv

client = OpenAI(api_key=getenv("OPENAI_API_KEY"))


class LLMClient:
    @staticmethod
    def generate_code(token_content: str) -> str:
        """Generate code for the given token content using the OpenAI API."""
        # We'll provide a system message guiding the LLM to produce code,
        # and a user message with the token content. You can refine these prompts as needed.

        system_message: ChatCompletionSystemMessageParam = {
            "role": "system",
            "content": "You are a coding assistant that generates TypeScript Angular components from natural language descriptions. Always return only code, no extra explanations.",
        }

        user_message: ChatCompletionUserMessageParam = {
            "role": "user",
            "content": f"Here is the description of a component:\n{token_content}\nGenerate the code now.",
        }

        # Call the ChatCompletion API
        # We'll do a simple retry on failure up to 3 times
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[system_message, user_message],
                    temperature=0.7,  # Adjust as desired
                    max_tokens=1500,  # Adjust based on your needs
                )
                # Extract code from response
                # We assume the assistant returns code as a single code block. If not,
                # you may need to parse out the code block from the message.
                code_content = response.choices[0].message.content.strip()
                return code_content
            except Exception as e:  # OpenAI errors are now standard exceptions
                if attempt == 2:
                    # On final attempt, re-raise the error
                    raise e

        # If somehow we exit the loop without returning or raising, raise a generic error
        raise RuntimeError("Failed to get response from LLM after 3 attempts.")
