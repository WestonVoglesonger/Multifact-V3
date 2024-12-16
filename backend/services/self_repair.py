from sqlalchemy.orm import Session
from typing import List
from backend.services.validation import ValidationService, ValidationResult, ValidationError
from backend.entities.compiled_multifact import CompiledMultifact
from backend.services.llm_client import LLMClient
from sqlalchemy import select

class SelfRepairService:
    @staticmethod
    def repair_artifact(artifact_id: int, session: Session, max_attempts: int = 3) -> bool:
        """
        Attempt to self-repair the code for the given artifact up to max_attempts.
        
        Steps:
        1. Validate artifact. If success, return True immediately.
        2. If fail, summarize errors and call LLM to fix code.
        3. Update artifact with LLM’s revised code, re-validate.
        4. Repeat until success or max_attempts reached.
        5. If still fail, mark artifact as invalid and return False.
        """

        artifact = session.scalars(
            select(CompiledMultifact).where(CompiledMultifact.id == artifact_id)
        ).first()
        if not artifact:
            raise ValueError(f"Artifact with id {artifact_id} not found.")
        
        for attempt in range(max_attempts):
            # Validate current code
            result = ValidationService.validate_artifact(artifact_id, session)

            if result.success:
                # Code is now valid
                return True
            else:
                # Code invalid, attempt self-repair
                # Summarize errors
                error_summary = SelfRepairService._summarize_errors(result.errors)
                
                # Prompt LLM to fix code
                new_code = SelfRepairService._ask_llm_to_fix_code(artifact.code, error_summary)
                
                # Update artifact with new code
                artifact.code = new_code
                # We'll set valid=False here since we haven't validated the new code yet
                artifact.valid = False
                session.commit()

        # After max_attempts, if still not valid, mark it as invalid and return False
        # Last validation:
        final_result = ValidationService.validate_artifact(artifact_id, session)
        if final_result.success:
            return True
        else:
            # Could mark artifact as permanently invalid or leave as is
            artifact.valid = False
            session.commit()
            return False

    @staticmethod
    def _summarize_errors(errors: List[ValidationError]) -> str:
        """
        Create a human-readable summary of errors to feed into the LLM.
        Example:
        "Found the following TypeScript errors:
        artifact_1.ts(10,5): TS2322: Type 'string' is not assignable to type 'number'.
        artifact_1.ts(15,2): TS7005: Variable 'y' implicitly has an 'any' type."
        """
        lines = ["Found the following TypeScript errors:"]
        for err in errors:
            lines.append(f"{err.file}({err.line},{err.char}): {err.message}")
        return "\n".join(lines)

    @staticmethod
    def _ask_llm_to_fix_code(original_code: str, error_summary: str) -> str:
        """
        Prompt the LLM with the original code and the errors, asking it to produce a corrected version.
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

        # Call LLM
        for attempt in range(3):
            try:
                response = LLMClient._generic_chat_call(system_message, user_message)  # We'll create _generic_chat_call below
                code_content = response.strip()
                return code_content
            except Exception as e:
                if attempt == 2:
                    raise e
        raise RuntimeError("Failed to get fixed code from LLM after 3 attempts.")