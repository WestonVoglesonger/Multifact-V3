from snc.application.interfaces.icode_fixer_service import ICodeFixerService
from snc.infrastructure.llm.model_factory import GroqModelType, OpenAIModelType
from snc.infrastructure.llm.client_factory import ClientFactory


class ConcreteCodeFixerService(ICodeFixerService):
    def fix_code(self, original_code: str, error_summary: str) -> str:
        # If there are no errors, return a message indicating no changes needed
        if not error_summary:
            return "No changes needed"

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

        llm_client = ClientFactory.get_llm_client(OpenAIModelType.GPT_4O_MINI)

        # Attempt LLM call up to 3 times
        for attempt in range(3):
            try:
                response = llm_client._generic_chat_call(
                    system_message,
                    user_message,
                    model_name=OpenAIModelType.GPT_4O_MINI.value,
                )
                if response is None:
                    if attempt == 2:
                        raise RuntimeError(
                            "Failed to get fixed code from LLM after 3 attempts."
                        )
                    continue

                code_content = response.strip()

                # Remove Markdown code block markers if present
                code_content = (
                    code_content.replace("```typescript", "").replace("```", "").strip()
                )

                return code_content
            except Exception:
                if attempt == 2:
                    raise RuntimeError(
                        "Failed to get fixed code from LLM after 3 attempts."
                    )
        raise RuntimeError("Failed to get fixed code from LLM after 3 attempts.")
