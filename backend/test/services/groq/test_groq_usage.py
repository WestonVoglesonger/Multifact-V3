# import pytest
# from unittest.mock import MagicMock, patch
# from decimal import Decimal
# from backend.services.llm.groq_llm_client import GroqLLMClient, compute_groq_cost
# from typing import Callable, Any
# @pytest.fixture
# def groq_client():
#     client = GroqLLMClient()
#     return client

# @pytest.mark.parametrize("prompt_tokens,completion_tokens,expected_cost", [
#     (200, 400, compute_groq_cost({"prompt_tokens": 200, "completion_tokens": 400}, 0.025, 0.05)),
#     (0, 0, compute_groq_cost({"prompt_tokens": 0, "completion_tokens": 0}, 0.025, 0.05)),
#     (5000, 5000, compute_groq_cost({"prompt_tokens": 5000, "completion_tokens": 5000}, 0.025, 0.05)),
# ])
# @patch("groq.Groq.chat.completions.create")
# def test_groq_usage_cost_calculation(mock_create: MagicMock, groq_client: GroqLLMClient, prompt_tokens: int, completion_tokens: int, expected_cost: float) -> None:
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="Groq response"))]
#     mock_response.usage = {
#         "prompt_tokens": prompt_tokens,
#         "completion_tokens": completion_tokens,
#         "total_tokens": prompt_tokens + completion_tokens
#     }
#     mock_create.return_value = mock_response

#     result = groq_client.parse_document("Some NI content for Groq.")
#     assert "scenes" in result
#     assert groq_client.last_usage["prompt_tokens"] == prompt_tokens
#     assert groq_client.last_usage["completion_tokens"] == completion_tokens
#     assert groq_client.last_cost == expected_cost, f"Expected {expected_cost}, got {groq_client.last_cost}"

# @patch("groq.Groq.chat.completions.create")
# def test_groq_generate_code_cost_tracking(mock_create: MagicMock, groq_client: GroqLLMClient) -> None:
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="Groq generated code snippet"))]
#     mock_response.usage = {
#         "prompt_tokens": 1200,
#         "completion_tokens": 1800,
#         "total_tokens": 3000
#     }
#     mock_create.return_value = mock_response

#     code = groq_client.generate_code("Generate another component")
#     assert "Groq generated code snippet" in code
#     assert groq_client.last_usage["prompt_tokens"] == 1200
#     assert groq_client.last_usage["completion_tokens"] == 1800

#     if groq_client.last_usage:
#         expected_cost = compute_groq_cost(groq_client.last_usage, 0.025, 0.05)
#         assert groq_client.last_cost == expected_cost

# @patch("groq.Groq.chat.completions.create")
# def test_groq_fix_code(mock_create: MagicMock, groq_client: GroqLLMClient) -> None:
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="fixed groq code"))]
#     mock_response.usage = {
#         "prompt_tokens": 500,
#         "completion_tokens": 500,
#         "total_tokens": 1000
#     }
#     mock_create.return_value = mock_response

#     fixed_code = groq_client.fix_code("buggy code", "some errors")
#     assert "fixed groq code" in fixed_code
#     assert groq_client.last_usage["prompt_tokens"] == 500
#     assert groq_client.last_usage["completion_tokens"] == 500

# @pytest.mark.benchmark
# @patch("groq.Groq.chat.completions.create")
# def test_groq_performance(benchmark: Callable[[Callable[[], Any]], Any], mock_create: MagicMock, groq_client: GroqLLMClient) -> None:
#     mock_response = MagicMock()
#     mock_response.choices = [MagicMock(message=MagicMock(content="Groq snippet"))]
#     mock_response.usage = {
#         "prompt_tokens": 800,
#         "completion_tokens": 1200,
#         "total_tokens": 2000
#     }
#     mock_create.return_value = mock_response

#     def run_call():
#         return groq_client.generate_code("Generate a quick snippet")

#     result = benchmark(run_call)
#     assert "Groq snippet" in result
#     assert groq_client.last_usage["total_tokens"] == 2000
