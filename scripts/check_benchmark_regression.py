#!/usr/bin/env python3
"""
Compare benchmark results against baseline and fail on >20% regression.

Usage:
    python scripts/check_benchmark_regression.py benchmarks/baseline.json benchmarks/current.json
"""
import json
import sys

REGRESSION_THRESHOLD = 0.20  # 20% slower = fail


def load_means(path: str) -> dict[str, float]:
    with open(path) as f:
        data = json.load(f)
    benchmarks = data.get("benchmarks") or []
    means = {}
    for b in benchmarks:
        name = b.get("name")
        stats = b.get("stats") or {}
        mean = stats.get("mean")
        if name is None or mean is None:
            continue
        means[name] = float(mean)
    return means


def main():
    if len(sys.argv) != 3:
        print("Usage: check_benchmark_regression.py <baseline.json> <current.json>")
        sys.exit(2)

    baseline_path, current_path = sys.argv[1], sys.argv[2]

    baseline = load_means(baseline_path)
    current = load_means(current_path)

    if not baseline:
        print("WARNING: baseline is empty — cannot detect regressions.")
        sys.exit(0)

    if not current:
        print("ERROR: current benchmark run produced no results.")
        sys.exit(1)

    regressions: list[str] = []
    for name, baseline_mean in baseline.items():
        if name not in current:
            print(f"WARNING: benchmark '{name}' missing from current run")
            continue
        current_mean = current[name]
        delta = (current_mean - baseline_mean) / baseline_mean
        status = "OK" if delta <= REGRESSION_THRESHOLD else "REGRESSION"
        print(
            f"{status}: {name} — baseline {baseline_mean:.4f}s, current {current_mean:.4f}s ({delta:+.1%})"
        )
        if delta > REGRESSION_THRESHOLD:
            regressions.append(name)

    if regressions:
        print(
            f"\nFAILED: {len(regressions)} benchmark(s) regressed beyond {REGRESSION_THRESHOLD:.0%} threshold:"
        )
        for name in regressions:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"\nPASSED: all benchmarks within {REGRESSION_THRESHOLD:.0%} threshold")
        sys.exit(0)


if __name__ == "__main__":
    main()
