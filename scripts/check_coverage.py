#!/usr/bin/env python3
"""Check coverage for critical modules."""

import subprocess
import sys
import xml.etree.ElementTree as ET

CRITICAL_MODULES = {
    # Critical paths: enforce 90% minimum
    "services/ui_iot/middleware/auth.py": 90,
    "services/ui_iot/middleware/tenant.py": 90,
    "services/ui_iot/db/pool.py": 90,
    "services/ui_iot/utils/url_validator.py": 90,
}

OVERALL_MINIMUM = 70


def get_coverage_from_xml(xml_path: str) -> dict:
    """Parse coverage.xml and return per-file coverage."""
    tree = ET.parse(xml_path)
    root = tree.getroot()
    coverage = {}
    for package in root.findall(".//package"):
        for cls in package.findall(".//class"):
            filename = cls.get("filename")
            if filename:
                if filename.startswith("services/ui_iot/"):
                    pass
                elif filename.startswith("services/"):
                    filename = f"services/ui_iot/{filename}"
                else:
                    filename = f"services/ui_iot/{filename}"
            line_rate = float(cls.get("line-rate", 0)) * 100
            coverage[filename] = line_rate
    return coverage


def main():
    result = subprocess.run(
        ["pytest", "-m", "not e2e", "--cov=services/ui_iot", "--cov-report=xml", "-q"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("Tests failed!")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)

    coverage = get_coverage_from_xml("coverage.xml")

    failed = False
    for module, minimum in CRITICAL_MODULES.items():
        actual = coverage.get(module, 0)
        status = "✓" if actual >= minimum else "✗"
        print(f"{status} {module}: {actual:.1f}% (minimum: {minimum}%)")
        if actual < minimum:
            failed = True

    tree = ET.parse("coverage.xml")
    root = tree.getroot()
    overall = float(root.get("line-rate", 0)) * 100
    status = "✓" if overall >= OVERALL_MINIMUM else "✗"
    print(f"\n{status} Overall: {overall:.1f}% (minimum: {OVERALL_MINIMUM}%)")

    if overall < OVERALL_MINIMUM:
        failed = True

    if failed:
        print("\n⚠️ Coverage requirements not met.")
        sys.exit(1)

    print("\n✅ All coverage requirements met!")
    sys.exit(0)


if __name__ == "__main__":
    main()
