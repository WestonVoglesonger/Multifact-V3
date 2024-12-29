import pytest
from pathlib import Path
import json
import os
from unittest.mock import patch, MagicMock
import subprocess
from typing import Dict, List

from ..benchmark_all_models import (
    run_pytest_benchmark,
    load_benchmark_data,
    determine_status,
    OPENAI_MODELS,
    GROQ_MODELS,
)


@pytest.fixture
def sample_benchmark_json(tmp_path: Path) -> Path:
    """Create a sample benchmark JSON file."""
    data = {
        "benchmarks": [
            {
                "name": "test_benchmark_1",
                "stats": {
                    "mean": 1.5,
                    "median": 1.4,
                    "stddev": 0.2,
                    "min": 1.2,
                    "max": 1.8
                },
                "extra_info": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "cost": 0.002
                }
            }
        ]
    }
    json_path = tmp_path / "test_benchmark.json"
    json_path.write_text(json.dumps(data))
    return json_path


def test_load_benchmark_data(sample_benchmark_json: Path):
    """Test loading benchmark data from JSON."""
    data = load_benchmark_data(sample_benchmark_json)
    assert len(data) == 1
    assert data[0]["name"] == "test_benchmark_1"
    assert data[0]["stats"]["mean"] == 1.5
    assert data[0]["extra_info"]["total_tokens"] == 150


def test_load_benchmark_data_missing_file(tmp_path: Path):
    """Test loading benchmark data from non-existent file."""
    missing_file = tmp_path / "missing.json"
    data = load_benchmark_data(missing_file)
    assert data == []


def test_determine_status():
    """Test benchmark status determination."""
    assert determine_status(10.0) == "⬆️ Slower"
    assert determine_status(-10.0) == "⬇️ Faster"
    assert determine_status(0.0) == "➡️ No Significant Change"
    assert determine_status(3.0) == "➡️ No Significant Change"


@pytest.mark.parametrize("client,model", [
    ("openai", "gpt-4o"),
    ("groq", "llama-3.1-8b-instant")
])
def test_run_pytest_benchmark(tmp_path: Path, client: str, model: str):
    """Test running pytest benchmark with different clients/models."""
    test_path = tmp_path / "test_performance.py"
    json_path = tmp_path / f"benchmark_{client}_{model}.json"
    
    # Create a mock test file
    test_path.write_text("def test_dummy(): pass")
    
    # Mock subprocess.run to avoid actual test execution
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = "Test completed successfully"
    
    with patch("subprocess.run", return_value=mock_process) as mock_run:
        run_pytest_benchmark(client, model, test_path, json_path)
        
        # Verify subprocess.run was called with correct arguments
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "pytest" in args
        assert str(test_path) in args
        assert "--benchmark-only" in args
        assert any(arg.startswith("--benchmark-json=") for arg in args)
        
        # Verify environment variables were set correctly
        env = mock_run.call_args[1]["env"]
        assert env["LLM_CLIENT_TYPE"] == client
        assert env["LLM_MODEL_TYPE"] == model


def test_run_pytest_benchmark_failure(tmp_path: Path):
    """Test handling of pytest benchmark failure."""
    test_path = tmp_path / "test_performance.py"
    json_path = tmp_path / "benchmark_failed.json"
    
    # Create a mock test file
    test_path.write_text("def test_dummy(): assert False")
    
    # Mock subprocess.run to simulate failure
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "Test failed"
    
    with patch("subprocess.run", return_value=mock_process):
        with pytest.raises(SystemExit):
            run_pytest_benchmark("openai", "gpt-4o", test_path, json_path)


def test_model_lists():
    """Test that model lists are properly defined."""
    assert len(OPENAI_MODELS) > 0
    assert "gpt-4o" in OPENAI_MODELS
    assert len(GROQ_MODELS) > 0
    assert "llama-3.1-8b-instant" in GROQ_MODELS


@pytest.mark.integration
def test_benchmark_output_format(tmp_path: Path):
    """Test the format of benchmark output files."""
    # Create a minimal benchmark result
    result = {
        "benchmarks": [{
            "name": "test_case",
            "stats": {
                "mean": 1.0,
                "median": 0.9,
                "stddev": 0.1,
                "min": 0.8,
                "max": 1.2
            },
            "extra_info": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "cost": 0.001
            }
        }]
    }
    
    json_path = tmp_path / "benchmark_test.json"
    with open(json_path, "w") as f:
        json.dump(result, f)
    
    # Load and verify the format
    loaded_data = load_benchmark_data(json_path)
    assert len(loaded_data) == 1
    benchmark = loaded_data[0]
    
    # Check required fields
    assert "name" in benchmark
    assert "stats" in benchmark
    assert "extra_info" in benchmark
    
    # Check stats fields
    stats = benchmark["stats"]
    assert all(key in stats for key in ["mean", "median", "stddev", "min", "max"])
    
    # Check extra_info fields
    extra_info = benchmark["extra_info"]
    assert all(key in extra_info for key in [
        "prompt_tokens", "completion_tokens", "total_tokens", "cost"
    ]) 