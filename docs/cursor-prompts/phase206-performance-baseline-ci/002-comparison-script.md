Create `scripts/check_benchmark_regression.py`. This script compares a fresh benchmark run against the baseline and exits non-zero if any benchmark degrades beyond the threshold.

```python
#!/usr/bin/env python3
"""
Compare benchmark results against baseline.
Exits 1 if any benchmark regressed beyond REGRESSION_THRESHOLD.
Usage: python scripts/check_benchmark_regression.py benchmarks/baseline.json benchmarks/current.json
"""
import json
import sys

REGRESSION_THRESHOLD = 0.20  # 20% slower = fail

def main():
    if len(sys.argv) != 3:
        print("Usage: check_benchmark_regression.py <baseline.json> <current.json>")
        sys.exit(2)

    baseline_path, current_path = sys.argv[1], sys.argv[2]

    with open(baseline_path) as f:
        baseline = {b["name"]: b["stats"]["mean"] for b in json.load(f)["benchmarks"]}

    with open(current_path) as f:
        current = {b["name"]: b["stats"]["mean"] for b in json.load(f)["benchmarks"]}

    regressions = []
    for name, baseline_mean in baseline.items():
        if name not in current:
            print(f"WARNING: benchmark '{name}' missing from current run")
            continue
        current_mean = current[name]
        delta = (current_mean - baseline_mean) / baseline_mean
        status = "OK" if delta <= REGRESSION_THRESHOLD else "REGRESSION"
        print(f"{status}: {name} — baseline {baseline_mean:.4f}s, current {current_mean:.4f}s ({delta:+.1%})")
        if delta > REGRESSION_THRESHOLD:
            regressions.append(name)

    if regressions:
        print(f"\nFAILED: {len(regressions)} benchmark(s) regressed beyond {REGRESSION_THRESHOLD:.0%} threshold:")
        for name in regressions:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"\nPASSED: all benchmarks within {REGRESSION_THRESHOLD:.0%} threshold")

if __name__ == "__main__":
    main()
```

Also create `scripts/update_benchmark_baseline.py` for intentional baseline updates:

```python
#!/usr/bin/env python3
"""
Update benchmark baseline after intentional performance changes.
Usage: python scripts/update_benchmark_baseline.py
"""
import subprocess, sys, shutil

result = subprocess.run(
    ["pytest", "-m", "benchmark", "--benchmark-json=benchmarks/baseline.json", "-q"],
    cwd="/home/opsconductor/simcloud"
)
if result.returncode != 0:
    print("Benchmark run failed — baseline not updated")
    sys.exit(1)
print("Baseline updated. Commit benchmarks/baseline.json to record the new baseline.")
```
