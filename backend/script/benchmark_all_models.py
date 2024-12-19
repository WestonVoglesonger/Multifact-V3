#!/usr/bin/env python3
"""
Script: benchmark_all_models.py

This script runs benchmarks for all supported models from both OpenAI and Groq,
compares them, and produces a comprehensive CSV report. It executes a suite of
performance tests for each (client, model) combination, aggregates the results,
and identifies the fastest model per benchmark and overall.

It saves results in a directory named with the current date and time under `benchmark/all_models/`.

Usage:
    python3 benchmark_all_models.py

No arguments are required. The script will use the current date and time as the directory name.

Output:
    - JSON benchmark files for each model in benchmark/all_models/{date-time}/
    - A CSV report (benchmark_all_models_comparison_report.csv) summarizing all models' 
      performance on each benchmark (mean, median, stddev, min, max, tokens, cost).
    - Logs ranking each model by how many benchmarks it "won" (fastest mean time).

This script provides a broad overview of performance across all available models,
helping identify not only per-benchmark winners but also the overall best model.
"""

import subprocess
import json
import os
from pathlib import Path
import csv
import sys
from typing import List, Dict
from datetime import datetime
import logging
from statistics import mean

logging.basicConfig(level=logging.INFO)

# Define test path
TEST_PATH = Path("backend/test/services/test_llm_performance.py")

# Define the sets of models for OpenAI and Groq
# Not including o1 and o1-mini because I do not have access to them
OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini"]
GROQ_MODELS = [
    "gemma2-9b-it",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-guard-3-8b",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768"
]

# Compute current date-time string
current_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Define benchmark directory and versioned subdirectory
BENCHMARK_DIR = Path("benchmark") / "all_models" / current_timestamp
BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)

def run_pytest_benchmark(client: str, model: str, test_path: Path, json_path: Path):
    """
    Runs pytest with benchmark for given client/model and outputs JSON report.
    Environment variables LLM_CLIENT_TYPE and LLM_MODEL_TYPE must be set before run.
    """
    env = os.environ.copy()
    env["LLM_CLIENT_TYPE"] = client
    env["LLM_MODEL_TYPE"] = model

    cmd = [
        "pytest",
        str(test_path),
        "--benchmark-only",
        f"--benchmark-json={json_path}",
    ]
    logging.info(f"Running benchmarks for {client}/{model} on {test_path}...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        logging.error(f"Error running benchmarks for {client}/{model}:\n{result.stderr}")
        sys.exit(1)
    logging.info(f"Benchmarks for {client}/{model} completed. Results saved to {json_path}.\n")


def load_benchmark_data(json_path: Path) -> List[Dict]:
    """
    Loads benchmark data from a JSON file.
    """
    if not json_path.exists():
        logging.error(f"Benchmark JSON file not found: {json_path}")
        return []
    with open(json_path, "r") as f:
        data = json.load(f)
    return data.get("benchmarks", [])

def determine_status(percentage_change: float) -> str:
    if percentage_change > 5:
        return "⬆️ Slower"
    elif percentage_change < -5:
        return "⬇️ Faster"
    else:
        return "➡️ No Significant Change"

def main():
    # Run all benchmarks for all models
    results_map = {}  # (client, model) -> benchmark json file path
    for om in OPENAI_MODELS:
        json_path = BENCHMARK_DIR / f"benchmark_openai_{om}.json"
        run_pytest_benchmark("openai", om, TEST_PATH, json_path)
        results_map[("openai", om)] = json_path

    for gm in GROQ_MODELS:
        json_path = BENCHMARK_DIR / f"benchmark_groq_{gm}.json"
        run_pytest_benchmark("groq", gm, TEST_PATH, json_path)
        results_map[("groq", gm)] = json_path

    # Load all benchmark data
    all_data = {}
    for k,v in results_map.items():
        all_data[k] = load_benchmark_data(v)

    # Build an index by benchmark name
    benchmark_index = {}
    for (client, model), benchmarks in all_data.items():
        for b in benchmarks:
            name = b["name"]
            if name not in benchmark_index:
                benchmark_index[name] = {}
            benchmark_index[name][(client,model)] = b

    # Prepare CSV headers
    all_models = list(results_map.keys())
    headers = ["Benchmark"]
    for (c,m) in all_models:
        prefix = f"{c}/{m}"
        headers.extend([
            f"{prefix} Mean (s)",
            f"{prefix} Median (s)",
            f"{prefix} Std Dev (s)",
            f"{prefix} Min (s)",
            f"{prefix} Max (s)",
            f"{prefix} Prompt Tokens",
            f"{prefix} Completion Tokens",
            f"{prefix} Total Tokens",
            f"{prefix} Cost"
        ])

    CSV_REPORT_PATH = BENCHMARK_DIR / "benchmark_all_models_comparison_report.csv"

    # Count wins per model
    wins_count = {mm:0 for mm in all_models}

    with open(CSV_REPORT_PATH, mode="w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()

        for bench_name, model_data in benchmark_index.items():
            row = {"Benchmark": bench_name}
            min_mean = float('inf')
            min_model = None
            for mm in all_models:
                bdata = model_data.get(mm)
                if bdata is not None:
                    stats = bdata.get("stats", {})
                    mean_val = stats.get("mean", 0)
                    if mean_val < min_mean:
                        min_mean = mean_val
                        min_model = mm

            if min_model is not None:
                wins_count[min_model] += 1

            for mm in all_models:
                bdata = model_data.get(mm)
                prefix = f"{mm[0]}/{mm[1]}"
                if bdata is None:
                    row[f"{prefix} Mean (s)"] = ""
                    row[f"{prefix} Median (s)"] = ""
                    row[f"{prefix} Std Dev (s)"] = ""
                    row[f"{prefix} Min (s)"] = ""
                    row[f"{prefix} Max (s)"] = ""
                    row[f"{prefix} Prompt Tokens"] = ""
                    row[f"{prefix} Completion Tokens"] = ""
                    row[f"{prefix} Total Tokens"] = ""
                    row[f"{prefix} Cost"] = ""
                else:
                    stats = bdata.get("stats", {})
                    extra_info = bdata.get("extra_info", {})
                    row[f"{prefix} Mean (s)"] = stats.get("mean", 0)
                    row[f"{prefix} Median (s)"] = stats.get("median", 0)
                    row[f"{prefix} Std Dev (s)"] = stats.get("stddev", 0)
                    row[f"{prefix} Min (s)"] = stats.get("min", 0)
                    row[f"{prefix} Max (s)"] = stats.get("max", 0)
                    row[f"{prefix} Prompt Tokens"] = extra_info.get("prompt_tokens",0)
                    row[f"{prefix} Completion Tokens"] = extra_info.get("completion_tokens",0)
                    row[f"{prefix} Total Tokens"] = extra_info.get("total_tokens",0)
                    row[f"{prefix} Cost"] = extra_info.get("cost",0)

            writer.writerow(row)

    # Compute overall best model by wins
    sorted_wins = sorted(wins_count.items(), key=lambda x: x[1], reverse=True)
    logging.info("Model wins tally (fastest per benchmark):")
    for mm, count_w in sorted_wins:
        logging.info(f"{mm[0]}/{mm[1]}: {count_w}")

    best_model = sorted_wins[0][0]
    logging.info(f"Overall best model: {best_model[0]}/{best_model[1]}")
    logging.info(f"Comparison report saved to {CSV_REPORT_PATH}.")
    logging.info("Done.")

if __name__ == "__main__":
    main()
