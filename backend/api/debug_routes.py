from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.infrastructure.llm.openai_llm_client import OpenAILLMClient
from backend.application.services.code_evaluation_service import CodeEvaluationService
from backend.domain.models import Model
from backend.infrastructure.llm.model_factory import ClientType

api = APIRouter(prefix="/debug", tags=["debug"])


class CodeEvalRequest(BaseModel):
    code: str


@api.post("/evaluate-code")
def debug_code_evaluation(payload: CodeEvalRequest, db: Session = Depends()):
    try:
        # Create a test model config
        model = Model(
            client_type=ClientType.OPENAI,
            name="gpt-4o-mini",
            context_window=4096,
            max_output_tokens=1024,
            prompt_cost_per_1k=0.005,
            completion_cost_per_1k=0.005,
            supports_images=False,
        )

        # Initialize services with debug logging
        llm_client = OpenAILLMClient(model)
        evaluation_service = CodeEvaluationService(llm_client)

        # Try evaluation with detailed error capture
        try:
            result = evaluation_service.evaluate_code(
                code=payload.code, context={"debug": True}
            )
        except Exception as e:
            return {
                "error": str(e),
                "error_type": type(e).__name__,
                "raw_code": payload.code,
                "model_used": model.name,
            }

        return {
            "evaluation_result": result,
            "raw_code": payload.code,
            "model_used": model.name,
            "client_type": str(model.client_type),
        }
    except Exception as e:
        return {"error": f"Outer error: {str(e)}", "error_type": type(e).__name__}
