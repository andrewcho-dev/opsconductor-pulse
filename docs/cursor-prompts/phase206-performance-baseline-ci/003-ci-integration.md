Read `.github/workflows/test.yml`. Find the benchmarks job. After the step that runs `pytest -m benchmark`, add two new steps:

```yaml
- name: Run benchmarks (current)
  run: pytest -m benchmark --benchmark-json=benchmarks/current.json -q

- name: Compare against baseline
  run: python scripts/check_benchmark_regression.py benchmarks/baseline.json benchmarks/current.json

- name: Upload benchmark results
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: benchmark-results
    path: |
      benchmarks/current.json
      benchmarks/baseline.json
```

The comparison step must run BEFORE the upload step and must NOT have `continue-on-error: true` — it needs to fail the build on regression.

Remove or replace any existing benchmark upload step that was uploading without comparison.

The `benchmarks/current.json` file is gitignored (it's a CI artifact, not a committed file). Add it to `.gitignore`:
```
benchmarks/current.json
```

The `benchmarks/baseline.json` IS committed — that's the reference point.
