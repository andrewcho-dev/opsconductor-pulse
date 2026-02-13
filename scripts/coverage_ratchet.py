#!/usr/bin/env python3
"""Coverage ratchet: prevent coverage from decreasing."""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BASELINE_FILE = Path(".coverage_baseline.json")
COVERAGE_XML = Path("coverage.xml")
TOLERANCE = 1.0  # Allow 1% fluctuation


def get_current_coverage() -> dict[str, float]:
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()
    result: dict[str, float] = {"_overall": float(root.get("line-rate", 0)) * 100}
    for pkg in root.findall(".//package"):
        for cls in pkg.findall(".//class"):
            fn = cls.get("filename", "")
            result[fn] = float(cls.get("line-rate", 0)) * 100
    return result


def main() -> int:
    if not COVERAGE_XML.exists():
        print("No coverage.xml found. Run tests with coverage first.")
        return 1

    current = get_current_coverage()

    if not BASELINE_FILE.exists():
        print("No baseline found. Creating initial baseline.")
        BASELINE_FILE.write_text(json.dumps(current, indent=2))
        return 0

    baseline = json.loads(BASELINE_FILE.read_text())
    regressions: list[str] = []

    for module, old_cov in baseline.items():
        new_cov = current.get(module, 0)
        if old_cov - new_cov > TOLERANCE:
            regressions.append(
                f"  {module}: {old_cov:.1f}% -> {new_cov:.1f}% "
                f"(dropped {old_cov - new_cov:.1f}%)"
            )

    if regressions:
        print("Coverage regressions detected:")
        for item in regressions:
            print(item)
        print(f"\nBaseline: {BASELINE_FILE}")
        print(
            "Fix the regressions or update baseline with: "
            "python scripts/coverage_ratchet.py --update"
        )
        return 1

    if "--update" in sys.argv:
        BASELINE_FILE.write_text(json.dumps(current, indent=2))
        print(f"Baseline updated: {BASELINE_FILE}")
    else:
        updated = False
        for module, new_cov in current.items():
            old_cov = baseline.get(module, 0)
            if new_cov > old_cov:
                baseline[module] = new_cov
                updated = True
        if updated:
            BASELINE_FILE.write_text(json.dumps(baseline, indent=2))

    print(f"Coverage check passed. Overall: {current.get('_overall', 0):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
