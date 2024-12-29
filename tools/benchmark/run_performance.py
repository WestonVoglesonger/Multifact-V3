#!/usr/bin/env python3
import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import logging

"""Run performance benchmarks for a single model.

This script runs a set of tests for a single specified LLM model and client,
collecting benchmark and performance data. It sets the environment variables
for LLM_CLIENT_TYPE and LLM_MODEL_TYPE before invoking pytest on the test suite.

Usage:
    python3 run_performance.py --client <client_type> --model <model_type>

Example:
    python3 run_performance.py --client openai --model gpt-4o

Arguments:
    --client: The LLM client type (e.g. "openai" or "groq")
    --model: The LLM model type (e.g. "gpt-4o", "gpt-4o-mini" for OpenAI
            or "gemma2-9b-it", "llama3-8b-8192", etc. for Groq)

Output:
    This script runs pytest on the specified model and client. The test results
    will appear in the console output. It is intended for integration with other
    scripts that handle benchmark JSON outputs and comparisons.
"""


logging.basicConfig(level=logging.INFO)


def main():
    """Run performance benchmarks for a single model."""
    parser = argparse.ArgumentParser(
        description="Run benchmark tests with a specified LLM client and model."
    )
    parser.add_argument(
        "--client",
        choices=["openai", "groq"],
        required=True,
        help="The client type to use (openai or groq)",
    )
    parser.add_argument(
        "--model",
        required=True,
        help=(
            "The model type to use (e.g. gpt-4o, gpt-4o-mini for openai " "or the groq equivalents)"
        ),
    )

    args = parser.parse_args()

    # Set environment variables for the tests
    os.environ["LLM_CLIENT_TYPE"] = args.client
    os.environ["LLM_MODEL_TYPE"] = args.model

    # Create output directory with timestamp and model name
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("benchmark") / "1_model" / f"{now_str}-{args.model}"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"benchmark_{args.client}_{args.model}.json"

    # Run pytest benchmarks
    pytest_cmd = [
        "pytest",
        "snc/test/test_performance/test_llm_performance.py",
        "--benchmark-only",
        f"--benchmark-json={json_path}",
    ]
    logging.info(f"Running single model benchmark for {args.client}/{args.model}...")
    result = subprocess.run(pytest_cmd, stdout=sys.stdout, stderr=sys.stderr)
    if result.returncode != 0:
        logging.error("Benchmark run failed.")
        sys.exit(result.returncode)

    logging.info(f"Benchmark completed. Results saved to {json_path}.")


if __name__ == "__main__":
    main()
