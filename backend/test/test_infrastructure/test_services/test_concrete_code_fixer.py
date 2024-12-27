import pytest
from unittest.mock import patch
from backend.infrastructure.services.code_fixer_service import ConcreteCodeFixerService
from backend.infrastructure.llm.model_factory import GroqModelType
from backend.infrastructure.llm.client_factory import ClientFactory

def test_fix_code_success():
    """
    Test that fix_code calls the LLM up to 3 times, returns the corrected code.
    We'll mock the LLM client call so we don't do real network calls.
    """

    code_fixer = ConcreteCodeFixerService()

    original_code = "console.log('Hello');"
    error_summary = "Some TypeScript error summary"
    # We'll patch the client factory's get_llm_client
    with patch.object(ClientFactory, "get_llm_client") as mock_factory:
        # The mock LLM
        mock_llm = mock_factory.return_value
        mock_llm._generic_chat_call.side_effect = [
            # first attempt works => return "Fixed code"
            "console.log('fixed');"
        ]

        result = code_fixer.fix_code(original_code, error_summary)
        assert result.strip() == "console.log('fixed');"
        # Verify the LLM was called once
        assert mock_llm._generic_chat_call.call_count == 1

def test_fix_code_raises_after_3_failures():
    """
    If the LLM call fails 3 times, fix_code should raise RuntimeError.
    """
    code_fixer = ConcreteCodeFixerService()
    with patch.object(ClientFactory, "get_llm_client") as mock_factory:
        mock_llm = mock_factory.return_value
        # Set up the mock to return None for each attempt
        # This simulates a failed response without raising an exception
        mock_llm._generic_chat_call.side_effect = [None, None, None]
        
        with pytest.raises(RuntimeError, match="Failed to get fixed code from LLM after 3 attempts."):
            code_fixer.fix_code("some code", "some errors")
        
        # Verify the LLM was called exactly 3 times
        assert mock_llm._generic_chat_call.call_count == 3

def test_fix_code_no_errors():
    """
    If error_summary doesn't mention errors, presumably the code is unchanged or fix is trivial.
    """
    code_fixer = ConcreteCodeFixerService()
    with patch.object(ClientFactory, "get_llm_client") as mock_factory:
        mock_llm = mock_factory.return_value
        mock_llm._generic_chat_call.return_value = "No changes needed"

        result = code_fixer.fix_code("console.log('original');", "")
        assert "No changes needed" in result
        assert mock_llm._generic_chat_call.call_count == 1
