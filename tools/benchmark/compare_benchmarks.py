import json
import os
import sys
from statistics import mean
from typing import Dict, List, Any, Tuple
from math import nan

"""
Script: compare_benchmarks.py

This script takes multiple benchmark result JSON files generated from previous runs
of LLM performance tests and:
- Produces a consolidated comparison across all provided scenarios (scenario-level).
- Aggregates model-level performance statistics (average execution time and cost).

Usage:
    python3 backend/script/compare_benchmarks.py <results_dir_or_json_file_paths...>

For example:
    python3 backend/script/compare_benchmarks.py ./benchmark_results/
    python3 backend/script/compare_benchmarks.py run_modelA.json run_modelB.json run_modelC.json

Arguments:
    <results_dir_or_json_file_paths...>: One or more directories or file paths.
        - If a directory is provided, all JSON files in that directory are processed.
        - If file paths are provided, only those files are processed.

Output:
    - Prints a scenario-wise comparison report to the console (existing functionality).
    - Prints a model-level summary that shows average mean execution time and average cost across all tested scenarios.

This script is useful for both post-hoc scenario-level analysis and for identifying
which model (from each file) generally performs better on average, considering both
time and cost.
"""


def load_benchmarks_from_file(file_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Load and return benchmark data from a single JSON file.
    Returns a dict of {scenario_name: stats_data}.
    Each stats_data includes timing stats and we will also retrieve cost from extra_info.
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    benchmarks = data.get("benchmarks", [])
    scenario_data = {}

    for bench in benchmarks:
        name = bench.get("name")
        stats = bench.get("stats", {})
        extra_info = bench.get("extra_info", {})

        # Include cost in the stats_data for later aggregation
        # We'll keep 'mean' execution time and 'cost' side-by-side.
        scenario_stats = {"mean": stats.get("mean"), "cost": extra_info.get("cost")}
        scenario_data[name] = scenario_stats
    return scenario_data


def aggregate_benchmarks(
    files: List[str],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Dict[str, List[float]]]]:
    """
    Given a list of JSON files, load and combine their benchmark data.
    Returns:
        combined (dict): {scenario_name: [list_of_stats_dicts_from_each_file]} for scenario-level comparison.
        model_data (dict): {model_name: {'means': [mean_times], 'costs': [costs]}} for model-level aggregation.
    """
    combined = {}
    model_data = {}

    for fpath in files:
        if not os.path.isfile(fpath):
            print(f"Warning: {fpath} is not a file. Skipping.")
            continue

        # Infer model name from filename (you can customize this)
        model_name = os.path.splitext(os.path.basename(fpath))[0]

        if model_name not in model_data:
            model_data[model_name] = {"means": [], "costs": []}

        scenario_data = load_benchmarks_from_file(fpath)
        for scenario_name, stats in scenario_data.items():
            if scenario_name not in combined:
                combined[scenario_name] = []
            combined[scenario_name].append(stats)

            # If we have a mean and cost, add them to the model_data
            scenario_mean = stats.get("mean")
            scenario_cost = stats.get("cost")
            if scenario_mean is not None:
                model_data[model_name]["means"].append(scenario_mean)
            if scenario_cost is not None:
                model_data[model_name]["costs"].append(scenario_cost)

    return combined, model_data


def compare_scenarios(
    combined_data: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Dict[str, Any]]:
    """
    Compare scenarios across multiple runs scenario-wise.
    This computes the combined mean of scenario means, min, and max.
    """
    comparison_results = {}
    for scenario, stats_list in combined_data.items():
        means = [s.get("mean") for s in stats_list if s.get("mean") is not None]
        means = [m for m in means if m is not None]

        if means:
            comparison_results[scenario] = {
                "num_runs": len(means),
                "combined_mean": mean(means),
                "min_of_means": min(means),
                "max_of_means": max(means),
            }
        else:
            comparison_results[scenario] = {
                "num_runs": len(stats_list),
                "error": "No mean execution time found in these results",
            }
    return comparison_results


def print_scenario_comparison(comparison_results: Dict[str, Dict[str, Any]]):
    """
    Print out scenario-level comparison results in a readable format.
    """
    print("Scenario Comparison Results:\n")
    for scenario, data in comparison_results.items():
        print(f"Scenario: {scenario}")
        if "error" in data:
            print(f"  Runs: {data['num_runs']} - {data['error']}")
        else:
            print(f"  Runs: {data['num_runs']}")
            print(f"  Combined Mean (of means): {data['combined_mean']:.6f}s")
            print(f"  Min of means: {data['min_of_means']:.6f}s")
            print(f"  Max of means: {data['max_of_means']:.6f}s")
        print("")


def print_model_summary(model_data: Dict[str, Dict[str, List[float]]]):
    """
    Print a summary per model, showing average execution time and average cost.
    """
    print("Model-Level Summary:\n")
    for model_name, data in model_data.items():
        means = data["means"]
        costs = data["costs"]
        if means:
            avg_mean_time = mean(means)
        else:
            avg_mean_time = nan

        if costs:
            avg_cost = mean(costs)
        else:
            avg_cost = float("nan")

        num_scenarios = len(means)  # Counting scenarios that had a mean time
        # Note: If some scenarios have no mean time but have costs, this logic could be adjusted.
        # For now, we tie scenario count to those that have mean times.

        print(f"Model: {model_name}")
        print(f"  Number of scenarios: {num_scenarios}")
        print(
            f"  Average Mean Time: {avg_mean_time:.6f}s"
            if not (avg_mean_time is float("nan"))
            else "  Average Mean Time: N/A"
        )
        print(
            f"  Average Cost: {avg_cost:.6f}"
            if not (avg_cost is float("nan"))
            else "  Average Cost: N/A"
        )
        print("")


def main():
    if len(sys.argv) < 2:
        print("Usage: python compare_benchmarks.py results_dir_or_files...")
        sys.exit(1)

    inputs = sys.argv[1:]
    # If a single directory is provided, read all *.json files from it.
    files = []
    for inp in inputs:
        if os.path.isdir(inp):
            # Collect all json files in the directory
            for fname in os.listdir(inp):
                if fname.endswith(".json"):
                    files.append(os.path.join(inp, fname))
        else:
            files.append(inp)

    if not files:
        print("No JSON files found to process.")
        sys.exit(1)

    combined_data, model_data = aggregate_benchmarks(files)
    comparison = compare_scenarios(combined_data)
    print_scenario_comparison(comparison)
    print_model_summary(model_data)


if __name__ == "__main__":
    main()
