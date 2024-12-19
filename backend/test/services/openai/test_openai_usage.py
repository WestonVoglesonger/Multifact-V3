# import pytest
# from unittest.mock import MagicMock, patch
# from decimal import Decimal
# from backend.services.llm.openai_llm_client import OpenAILLMClient, compute_cost
# from openai.types.completion_usage import CompletionUsage
# from typing import Callable, Any
# @pytest.fixture
# def openai_client():
#     client = OpenAILLMClient()
#     return client

# @pytest.mark.parametrize("prompt_tokens,completion_tokens,expected_cost", [
#     (100, 200, compute_cost({"prompt_tokens": 100, "completion_tokens": 200}, 0.00015, 0.0006)),
#     (0, 0, compute_cost({"prompt_tokens": 0, "completion_tokens": 0}, 0.00015, 0.0006)),
#     (5000, 5000, compute_cost({"prompt_tokens": 5000, "completion_tokens": 5000}, 0.00015, 0.0006)),
#     (999, 1, compute_cost({"prompt_tokens": 999, "completion_tokens": 1}, 0.00015, 0.0006)),
# ])
# @patch("openai.OpenAI.chat.completions.create")
# def test_openai_usage_cost_calculation(mock_create: MagicMock, openai_client: OpenAILLMClient, prompt_tokens: int, completion_tokens: int, expected_cost: float) -> None:
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
#     mock_response.usage = CompletionUsage(
#         prompt_tokens=prompt_tokens,
#         completion_tokens=completion_tokens,
#         total_tokens=prompt_tokens+completion_tokens
#     )
#     mock_create.return_value = mock_response

#     result = openai_client.parse_document("Test document")

#     assert "scenes" in result, "parse_document should return a result dictionary with 'scenes'."
#     assert openai_client.last_usage is not None
#     assert openai_client.last_usage.prompt_tokens == prompt_tokens
#     assert openai_client.last_usage.completion_tokens == completion_tokens
#     assert openai_client.last_cost == expected_cost, f"Expected cost {expected_cost}, got {openai_client.last_cost}"

# @patch("openai.OpenAI.chat.completions.create")
# def test_openai_generate_code_cost_tracking(mock_create: MagicMock, openai_client: OpenAILLMClient) -> None:
#     # Simulate a code generation scenario with known usage
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="generated code snippet"))]
#     mock_response.usage = {
#         "prompt_tokens": 1500,
#         "completion_tokens": 2500,
#         "total_tokens": 4000
#     }
#     mock_create.return_value = mock_response

#     code = openai_client.generate_code("Generate a component")
#     assert "generated code snippet" in code
#     assert openai_client.last_usage is not None
#     assert openai_client.last_usage.prompt_tokens == 1500
#     assert openai_client.last_usage.completion_tokens == 2500

#     # Compute expected cost with the client's default costs
#     if openai_client.last_usage:
#         expected_cost = compute_cost(openai_client.last_usage, openai_client.cost_per_1k_prompt, openai_client.cost_per_1k_completion)
#         assert openai_client.last_cost == expected_cost

# @patch("openai.OpenAI.chat.completions.create")
# def test_openai_fix_code_usage(mock_create: MagicMock, openai_client: OpenAILLMClient) -> None:
#     # Simulate fixing code scenario
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="fixed code"))]
#     mock_response.usage = {
#         "prompt_tokens": 250,
#         "completion_tokens": 750,
#         "total_tokens": 1000
#     }
#     mock_create.return_value = mock_response

#     original_code = "some buggy code"
#     error_summary = "some errors"
#     fixed_code = openai_client.fix_code(original_code, error_summary)

#     assert "fixed code" in fixed_code
#     assert openai_client.last_usage.prompt_tokens == 250
#     assert openai_client.last_usage.completion_tokens == 750

# @pytest.mark.benchmark
# @patch("openai.OpenAI.chat.completions.create")
# def test_openai_performance(benchmark: Callable[[Callable[[], Any]], Any], mock_create: MagicMock, openai_client: OpenAILLMClient) -> None:
#     # Performance test to measure speed and cost over multiple calls
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="some code"))]
#     mock_response.usage = {
#         "prompt_tokens": 1000,
#         "completion_tokens": 2000,
#         "total_tokens": 3000
#     }
#     mock_create.return_value = mock_response

#     def run_call():
#         return openai_client.generate_code("Generate a component")

#     result = benchmark(run_call)
#     assert "some code" in result
#     assert openai_client.last_usage.total_tokens == 3000
