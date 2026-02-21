#!/usr/bin/env python3
"""
Update benchmark baseline after intentional performance changes.
Usage: python scripts/update_benchmark_baseline.py
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        ["pytest", "-m", "benchmark", "--benchmark-json=benchmarks/baseline.json", "-q"],
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        print("Benchmark run failed — baseline not updated")
        return 1
    print("Baseline updated. Commit benchmarks/baseline.json to record the new baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
