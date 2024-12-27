from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

api = APIRouter()

logger = logging.getLogger(__name__)


class NIContentRequest(BaseModel):
    ni_content: str


@api.post("/debug/parse-llm-raw")
def debug_parse_ni_raw(payload: NIContentRequest):
    """
    A debug endpoint that returns the *raw* LLM response as text,
    without attempting to parse JSON.
    """
    try:
        # 1) Create or get your LLM client
        #    For example, if you're using the Groq client:
        from backend.infrastructure.llm.model_factory import OpenAIModelType
        from backend.infrastructure.llm.client_factory import ClientFactory

        llm_client = ClientFactory.get_llm_client(OpenAIModelType.GPT_4O_MINI)

        # 2) Build the system prompt / user message
        system_message = {
            "role": "system",
            "content": (
                "You are a strict parser. You MUST return valid JSON with this structure:\n"
                "{\n  \"scenes\": [ {\"name\":\"...\", \"narrative\":\"...\", "
                "\"components\": [ { \"name\":\"...\", \"narrative\":\"...\", \"functions\":[...] }, ... ] } ],\n"
                "}\nNo extra text or disclaimers."
            )
        }


        user_message = {
            "role": "user",
            "content": (
                "Please parse the following NI instructions into JSON:\n"
                f"{payload.ni_content}"
            ),
        }


        # 3) Make the raw LLM call
        response_text = llm_client._generic_chat_call(
            system_message=system_message,
            user_message=user_message,
            model_name="gpt-4o-mini",
            temperature=0.2,
            max_tokens=800,
        )

        # 4) Return it directly
        return {"status": "ok", "raw_llm_response": response_text}
    except Exception as e:
        logger.error(f"Error in debug_parse_ni_raw: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

