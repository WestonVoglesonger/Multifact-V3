import subprocess
import json
import os
from pathlib import Path
import csv
import sys
from typing import List, Dict, Any, Union
import argparse
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)

"""
Script: benchmark_compare_two_models.py

This script compares the performance of two LLM models by running a specified set
of benchmark tests twice: once for the first (client, model) pair and once for the
second (client, model) pair. It saves JSON results and generates a comparison report.

Usage:
    python3 backend/script/benchmark_compare_two_models.py --client1 <client1> --model1 <model1> --client2 <client2> --model2 <model2> [--version <version>]

Example:
    python3 backend/script/benchmark_compare_two_models.py --client1 openai --model1 gpt-4o --client2 groq --model2 gemma2-9b-it --version v2

Arguments:
    --client1: First LLM client (e.g. "openai" or "groq")
    --model1: First LLM model type (e.g. "gpt-4o" for OpenAI)
    --client2: Second LLM client
    --model2: Second LLM model type
    --version: Optional label for the benchmark run (defaults to current datetime)

Output:
    - JSON benchmark results saved into a directory under benchmark/<version>/
    - A CSV comparison report (benchmark_comparison_report.csv) that shows metrics,
      such as mean execution time, tokens, and cost for each benchmark run.
    - Logging output to console with a summary.

This script is useful for quickly determining which of two models is faster or more efficient
on a given test suite.
"""

parser = argparse.ArgumentParser(
    description="Run and compare benchmarks between two LLM models."
)
parser.add_argument(
    "--client1",
    type=str,
    required=True,
    help="First LLM client type (e.g., 'openai' or 'groq').",
)
parser.add_argument("--model1", type=str, required=True, help="First LLM model type.")
parser.add_argument(
    "--client2", type=str, required=True, help="Second LLM client type."
)
parser.add_argument("--model2", type=str, required=True, help="Second LLM model type.")
parser.add_argument(
    "--test_path",
    type=str,
    default="backend/test/test_performance/test_llm_performance.py",
    help="Path to the performance test file.",
)
args = parser.parse_args()

now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_dir = Path("benchmark") / "2_model" / f"{now_str}-{args.model1}-{args.model2}"
output_dir.mkdir(parents=True, exist_ok=True)

MODEL1_BENCH_JSON = output_dir / f"benchmark_{args.client1}_{args.model1}.json"
MODEL2_BENCH_JSON = output_dir / f"benchmark_{args.client2}_{args.model2}.json"
CSV_REPORT_PATH = output_dir / "benchmark_comparison_report.csv"


def run_pytest_benchmark(test_path: str, json_path: Path, client: str, model: str):
    env = os.environ.copy()
    env["LLM_CLIENT_TYPE"] = client
    env["LLM_MODEL_TYPE"] = model

    cmd = [
        "pytest",
        test_path,
        "--benchmark-only",
        f"--benchmark-json={json_path}",
    ]
    logging.info(f"Running benchmarks for {client}/{model} on {test_path}...")
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0:
        logging.error(
            f"Error running benchmarks for {client}/{model}:\n{result.stderr}"
        )
        sys.exit(1)
    logging.info(
        f"Benchmarks for {client}/{model} completed. Results saved to {json_path}.\n"
    )


def load_benchmark_data(json_path: Path) -> List[Dict]:
    if not json_path.exists():
        logging.error(f"Benchmark JSON file not found: {json_path}")
        sys.exit(1)
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


def compare_benchmarks(
    benchmarks_1: List[Dict], benchmarks_2: List[Dict]
) -> List[Dict]:
    comparison_results = []
    map1 = {bench["name"]: bench for bench in benchmarks_1}

    def safe_get(d: Dict, k: str, default: Union[int, float] = 0) -> Union[int, float]:
        return d.get(k, default)

    for bench2 in benchmarks_2:
        name = bench2["name"]
        bench1 = map1.get(name)
        if not bench1:
            logging.warning(f"No matching benchmark found for test: {name}")
            continue

        b1_stats = bench1.get("stats", {})
        b2_stats = bench2.get("stats", {})
        b1_extra = bench1.get("extra_info", {})
        b2_extra = bench2.get("extra_info", {})

        percentage_change = (
            (b2_stats.get("mean", 0) - b1_stats.get("mean", 0))
            / (b1_stats.get("mean", 1))
        ) * 100

        comparison = {
            "Benchmark": name,
            f"{args.client1}/{args.model1} Mean (s)": b1_stats.get("mean", 0),
            f"{args.client2}/{args.model2} Mean (s)": b2_stats.get("mean", 0),
            "Percentage Change (%)": percentage_change,
            f"{args.client1}/{args.model1} Prompt Tokens": safe_get(
                b1_extra, "prompt_tokens"
            ),
            f"{args.client2}/{args.model2} Prompt Tokens": safe_get(
                b2_extra, "prompt_tokens"
            ),
            f"{args.client1}/{args.model1} Completion Tokens": safe_get(
                b1_extra, "completion_tokens"
            ),
            f"{args.client2}/{args.model2} Completion Tokens": safe_get(
                b2_extra, "completion_tokens"
            ),
            f"{args.client1}/{args.model1} Total Tokens": safe_get(
                b1_extra, "total_tokens"
            ),
            f"{args.client2}/{args.model2} Total Tokens": safe_get(
                b2_extra, "total_tokens"
            ),
            f"{args.client1}/{args.model1} Cost": safe_get(b1_extra, "cost", 0.0),
            f"{args.client2}/{args.model2} Cost": safe_get(b2_extra, "cost", 0.0),
            f"{args.client1}/{args.model1} Median (s)": b1_stats.get("median", 0),
            f"{args.client2}/{args.model2} Median (s)": b2_stats.get("median", 0),
            f"{args.client1}/{args.model1} Std Dev (s)": b1_stats.get("stddev", 0),
            f"{args.client2}/{args.model2} Std Dev (s)": b2_stats.get("stddev", 0),
            f"{args.client1}/{args.model1} Min (s)": b1_stats.get("min", 0),
            f"{args.client2}/{args.model2} Min (s)": b2_stats.get("min", 0),
            f"{args.client1}/{args.model1} Max (s)": b1_stats.get("max", 0),
            f"{args.client2}/{args.model2} Max (s)": b2_stats.get("max", 0),
            f"{args.client1}/{args.model1} 95th Percentile (s)": b1_stats.get(
                "percentile95", 0
            ),
            f"{args.client2}/{args.model2} 95th Percentile (s)": b2_stats.get(
                "percentile95", 0
            ),
            "Status": determine_status(percentage_change),
        }

        comparison_results.append(comparison)

    return comparison_results


def print_comparison_report(comparisons: List[Dict]):
    logging.info("Benchmark Comparison Report\n")
    if not comparisons:
        logging.info("No comparison data available.")
        return
    headers = list(comparisons[0].keys())
    header_line = " | ".join(headers)
    logging.info(header_line)
    logging.info("-" * len(header_line))
    for comp in comparisons:
        row = " | ".join(str(comp[h]) for h in headers)
        logging.info(row)
    logging.info("\nLegend:")
    logging.info("⬆️ Slower: Second model is significantly slower than first.")
    logging.info("⬇️ Faster: Second model is significantly faster than first.")
    logging.info(
        "➡️ No Significant Change: Performance difference is within acceptable range."
    )


def save_to_csv(comparisons: List[Dict], csv_path: Path):
    if not comparisons:
        logging.warning("No comparison data to save.")
        return
    headers = comparisons[0].keys()
    with open(csv_path, mode="w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        for comp in comparisons:
            writer.writerow(comp)
    logging.info(f"Comparison report saved to {csv_path}.")


def main():
    run_pytest_benchmark(args.test_path, MODEL1_BENCH_JSON, args.client1, args.model1)
    run_pytest_benchmark(args.test_path, MODEL2_BENCH_JSON, args.client2, args.model2)

    model1_benchmarks = load_benchmark_data(MODEL1_BENCH_JSON)
    model2_benchmarks = load_benchmark_data(MODEL2_BENCH_JSON)

    comparisons = compare_benchmarks(model1_benchmarks, model2_benchmarks)
    print_comparison_report(comparisons)
    save_to_csv(comparisons, CSV_REPORT_PATH)


if __name__ == "__main__":
    main()
