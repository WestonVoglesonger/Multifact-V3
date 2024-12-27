from backend.application.interfaces.icode_fixer_service import ICodeFixerService
from backend.infrastructure.llm.model_factory import GroqModelType
from backend.infrastructure.llm.client_factory import ClientFactory

class ConcreteCodeFixerService(ICodeFixerService):
    def fix_code(self, original_code: str, error_summary: str) -> str:
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

        llm_client = ClientFactory.get_llm_client(GroqModelType.LLAMA_GUARD_3_8B)

        # Attempt LLM call up to 3 times
        for attempt in range(3):
            try:
                response = llm_client._generic_chat_call(system_message, user_message, model_name=GroqModelType.LLAMA_GUARD_3_8B.value)
                code_content = response.strip()
                return code_content
            except Exception:
                if attempt == 2:
                    raise
        raise RuntimeError("Failed to get fixed code from LLM after 3 attempts.")
