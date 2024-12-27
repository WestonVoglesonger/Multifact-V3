import pytest
from unittest.mock import patch, MagicMock, Mock
from backend.infrastructure.llm.client_factory import ClientFactory
from backend.infrastructure.services.code_fixer_service import ConcreteCodeFixerService
from backend.infrastructure.validation.validation_service import ConcreteValidationService
from backend.application.interfaces.ivalidation_service import ValidationResult, ValidationError
from backend.application.services.code_evaluation_service import CodeEvaluationService

#
# Fixture that mocks ANY code-fixer attempts (avoid calling real LLM for "fix_code")
#
def mock_fix_code_return(original_code: str, error_summary: str) -> str:
    """
    Pretend we 'fixed' the code. 
    If there's an error_summary, we return code that presumably passes validation.
    Otherwise, we just return the original code.
    """
    if "Found the following TypeScript errors" in error_summary:
        return "// Some code that passes validation\nexport class MyFixedComponent {}"
    else:
        return original_code

@pytest.fixture
def mock_code_fixer_service():
    """
    Patch `ConcreteCodeFixerService.fix_code` → mock_fix_code_return
    Ensures tests never do real LLM calls for code fixes.
    """
    with patch.object(
        ConcreteCodeFixerService, 
        "fix_code", 
        side_effect=mock_fix_code_return
    ) as mock_method:
        yield mock_method


#
# Fixture that *mocks* the ValidationService so we can easily say success/fail
#
@pytest.fixture
def mock_validation_service_success():
    """
    Patch `ConcreteValidationService.validate_artifact` to always succeed.
    """
    with patch.object(ConcreteValidationService, "validate_artifact") as mock_validate:
        mock_validate.return_value = ValidationResult(success=True, errors=[])
        yield mock_validate


@pytest.fixture
def mock_validation_service_failure():
    """
    Patch `ConcreteValidationService.validate_artifact` to always fail.
    """
    with patch.object(ConcreteValidationService, "validate_artifact") as mock_validate:
        mock_validate.return_value = ValidationResult(
            success=False,
            errors=[
                ValidationError(
                    file="artifact.ts",
                    line=1,
                    char=1,
                    message="TS1005: ';' expected."
                )
            ]
        )
        yield mock_validate


#
# Fixture that *mocks* the LLM's generate_code
#
@pytest.fixture
def mock_llm_client():
    """
    Returns a MagicMock for the LLM client. 
    generate_code is side_effected to return code that is either valid or invalid
    based on the content string.
    """
    mock_client = MagicMock()

    def generate_code_side_effect(content: str) -> str:
        if "Should compile content" in content:
            return "export class MyValidComponent { greet() {} }"
        elif "Will fail content" in content:
            return "invalid code"
        else:
            return "// default mock code"
    
    mock_client.generate_code.side_effect = generate_code_side_effect

    # If you also want to ensure parse_document is never called:
    mock_client.parse_document.return_value = {"scenes": []}

    return mock_client


#
# Fixture that patches `ClientFactory.get_llm_client(...)` so it returns `mock_llm_client`
#
@pytest.fixture
def patch_client_factory(mock_llm_client: Mock):
    with patch.object(ClientFactory, "get_llm_client", return_value=mock_llm_client) as mock_method:
        yield mock_method


#
# Fixture that *mocks* the LLM parse_document specifically for the “Help” scenario
#
@pytest.fixture
def mock_llm_parse_help():
    """
    Patch `ConcreteLLMService.parse_document` so that it *always* returns 
    a scene named Intervention plus a new component named 'Help'.
    """
    with patch("backend.infrastructure.llm.llm_service_impl.ConcreteLLMService.parse_document") as mock_parse:
        mock_parse.return_value = {
            "scenes": [
                {
                    "name": "Intervention",
                    "narrative": "Updated intervention doc.",
                    "components": [
                        {
                            "name": "Help",
                            "narrative": "Display a help message.",
                            "functions": []
                        }
                    ]
                }
            ]
        }
        yield mock_parse

@pytest.fixture
def evaluation_service_mock():
    """
    If you want a real model call, remove the mock and do:
      llm_client = ClientFactory.get_llm_client(OpenAIModelType.O1_MINI)
      return CodeEvaluationService(llm_client)
    But for stable testing, we mock the LLM response.
    """
    mock_llm_client = MagicMock()
    mock_llm_client._generic_chat_call.return_value = '{"score": 9.2, "feedback": "Great code structure."}'
    return CodeEvaluationService(mock_llm_client)