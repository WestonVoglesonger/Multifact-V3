import pytest
from pathlib import Path
import json
import csv
from typing import Dict, List
from unittest.mock import patch, MagicMock
from ..benchmark_compare_two_models import (
    compare_benchmark_results,
    generate_comparison_report,
    calculate_percentage_change,
)


@pytest.fixture
def sample_benchmark_results(tmp_path: Path) -> tuple[Path, Path]:
    """Create sample benchmark result files for comparison."""
    base_data = {
        "benchmarks": [
            {
                "name": "test_case_1",
                "stats": {
                    "mean": 1.0,
                    "median": 0.9,
                    "stddev": 0.1,
                    "min": 0.8,
                    "max": 1.2,
                },
                "extra_info": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150,
                    "cost": 0.001,
                },
            }
        ]
    }

    new_data = {
        "benchmarks": [
            {
                "name": "test_case_1",
                "stats": {
                    "mean": 0.8,  # 20% faster
                    "median": 0.7,
                    "stddev": 0.1,
                    "min": 0.6,
                    "max": 1.0,
                },
                "extra_info": {
                    "prompt_tokens": 90,
                    "completion_tokens": 45,
                    "total_tokens": 135,
                    "cost": 0.0009,
                },
            }
        ]
    }

    base_path = tmp_path / "base_benchmark.json"
    new_path = tmp_path / "new_benchmark.json"

    base_path.write_text(json.dumps(base_data))
    new_path.write_text(json.dumps(new_data))

    return base_path, new_path


def test_calculate_percentage_change():
    """Test percentage change calculation."""
    assert abs(calculate_percentage_change(1.0, 0.8) - (-20.0)) < 1e-10  # 20% faster
    assert abs(calculate_percentage_change(0.8, 1.0) - 25.0) < 1e-10  # 25% slower
    assert abs(calculate_percentage_change(1.0, 1.0)) < 1e-10  # No change
    assert calculate_percentage_change(0.0, 1.0) == float("inf")  # From zero
    assert abs(calculate_percentage_change(1.0, 0.0) - (-100.0)) < 1e-10  # To zero


def test_compare_benchmark_results(sample_benchmark_results: tuple[Path, Path]):
    """Test benchmark results comparison."""
    base_path, new_path = sample_benchmark_results
    comparison = compare_benchmark_results(base_path, new_path)

    assert len(comparison) == 1
    result = comparison[0]

    assert result["Benchmark"] == "test_case_1"
    assert abs(result["openai/gpt-4 Mean (s)"] - 1.0) < 1e-10
    assert abs(result["groq/mixtral-8x7b Mean (s)"] - 0.8) < 1e-10
    assert abs(result["Percentage Change (%)"] - (-20.0)) < 1e-10  # 20% faster


def test_generate_comparison_report(tmp_path: Path, sample_benchmark_results: tuple[Path, Path]):
    """Test generation of comparison report CSV."""
    base_path, new_path = sample_benchmark_results
    report_path = tmp_path / "comparison_report.csv"

    generate_comparison_report(base_path, new_path, report_path)

    # Verify CSV file was created
    assert report_path.exists()

    # Read and verify CSV contents
    with open(report_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

        assert len(rows) == 1
        row = rows[0]

        # Check required columns
        assert "Benchmark" in row
        assert "openai/gpt-4 Mean (s)" in row
        assert "groq/mixtral-8x7b Mean (s)" in row
        assert "Percentage Change (%)" in row


def test_compare_benchmark_results_missing_benchmark(tmp_path: Path):
    """Test comparison with missing benchmark in new results."""
    base_data = {
        "benchmarks": [
            {
                "name": "test_case_1",
                "stats": {"mean": 1.0},
                "extra_info": {"total_tokens": 100, "cost": 0.001},
            }
        ]
    }

    new_data = {
        "benchmarks": [
            {
                "name": "test_case_2",  # Different benchmark
                "stats": {"mean": 0.8},
                "extra_info": {"total_tokens": 90, "cost": 0.0009},
            }
        ]
    }

    base_path = tmp_path / "base.json"
    new_path = tmp_path / "new.json"

    base_path.write_text(json.dumps(base_data))
    new_path.write_text(json.dumps(new_data))

    comparison = compare_benchmark_results(base_path, new_path)
    assert len(comparison) == 0


def test_generate_comparison_report_empty_results(tmp_path: Path):
    """Test report generation with empty benchmark results."""
    empty_data = {"benchmarks": []}

    base_path = tmp_path / "empty_base.json"
    new_path = tmp_path / "empty_new.json"
    report_path = tmp_path / "empty_report.csv"

    base_path.write_text(json.dumps(empty_data))
    new_path.write_text(json.dumps(empty_data))

    generate_comparison_report(base_path, new_path, report_path)

    # Empty CSV should still be created with headers
    assert report_path.exists()
    with open(report_path, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        assert len(list(reader)) == 0  # No data rows
        assert len(reader.fieldnames or []) > 0  # But has headers
