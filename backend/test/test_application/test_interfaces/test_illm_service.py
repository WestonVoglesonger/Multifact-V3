import pytest
from backend.application.interfaces.illm_service import ILLMService


def test_illm_service_is_abstract():
    with pytest.raises(TypeError, match="Can't instantiate abstract class ILLMService"):
        ILLMService()  # type: ignore


def test_illm_service_minimal_subclass():
    class MinimalLLMService(ILLMService):
        def parse_document(self, content: str):
            return {"parsed": True}

        def generate_code(
            self,
            token_content: str,
            additional_requirements: str = "",
            code_style: str = "",
        ) -> str:
            return "some_generated_code"

        def fix_code(self, original_code: str, error_summary: str) -> str:
            return "some_fixed_code"

    svc = MinimalLLMService()
    assert svc.parse_document("content") == {"parsed": True}
    assert svc.generate_code("token") == "some_generated_code"
    assert svc.fix_code("bad_code", "error") == "some_fixed_code"

