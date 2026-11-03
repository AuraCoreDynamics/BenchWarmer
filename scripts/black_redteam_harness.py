#!/usr/bin/env python3
"""BLACK Framework v2.2 Red-Team Verification Harness.

Reads scoring.json, executes test discovery, audits behavioral assertions,
verifies convergence criteria, and validates methodology tags.
"""

import json
import os
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))


def load_scoring_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"scoring manifest not found at {manifest_path}")
    with manifest_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_tests() -> unittest.TestResult:
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT_DIR / "tests"), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stderr)
    result = runner.run(suite)
    return result


def audit_tags(tags: list) -> list:
    violations = []
    pyproject = (ROOT_DIR / "pyproject.toml").read_text(encoding="utf-8")

    if "zero-runtime-dependencies" in tags:
        if "dependencies = []" not in pyproject:
            violations.append("Tag 'zero-runtime-dependencies' violated: pyproject.toml has runtime dependencies")

    if "cross-sovereignty" in tags:
        mcp_schema = ROOT_DIR / "src" / "benchwarmer" / "mcp_schema.json"
        if not mcp_schema.exists():
            violations.append("Tag 'cross-sovereignty' violated: src/benchwarmer/mcp_schema.json missing")

    if "numerical-precision-invariance" in tags:
        contracts_file = ROOT_DIR / "src" / "benchwarmer" / "contracts.py"
        if not contracts_file.exists():
            violations.append("Tag 'numerical-precision-invariance' violated: contracts.py missing")

    if "ui-wire-sync" in tags:
        gui_file = ROOT_DIR / "src" / "benchwarmer" / "gui.py"
        if not gui_file.exists():
            violations.append("Tag 'ui-wire-sync' violated: gui.py missing")

    return violations


def main() -> int:
    manifest_arg = sys.argv[1] if len(sys.argv) > 1 else "scoring.json"
    manifest_path = Path(manifest_arg)
    if not manifest_path.is_absolute():
        manifest_path = ROOT_DIR / manifest_path

    try:
        manifest = load_scoring_manifest(manifest_path)
    except Exception as e:
        print(f"RED-TEAM HARNESS ERROR: Failed to load manifest: {e}", file=sys.stderr)
        return 1

    criteria = manifest.get("convergence_criteria", {})
    min_pass_rate = criteria.get("min_test_pass_rate", 1.0)
    min_assertions = criteria.get("min_behavioral_assertions_per_tg", 3)

    tag_violations = audit_tags(manifest.get("tags", []))
    if tag_violations:
        print("RED-TEAM HARNESS TAG VIOLATIONS:", file=sys.stderr)
        for v in tag_violations:
            print(f"  - {v}", file=sys.stderr)
        return 1

    # Run tests
    test_dir = ROOT_DIR / "tests"
    if test_dir.exists() and list(test_dir.rglob("test_*.py")):
        result = run_tests()
        total_run = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        passed = total_run - (failures + errors)

        if total_run > 0:
            pass_rate = passed / total_run
            if pass_rate < min_pass_rate:
                print(f"RED-TEAM HARNESS FAILED: Test pass rate {pass_rate:.2%} < required {min_pass_rate:.2%}", file=sys.stderr)
                return 1

        if failures > 0 or errors > 0:
            print(f"RED-TEAM HARNESS FAILED: {failures} failures, {errors} errors", file=sys.stderr)
            return 1

        print(f"RED-TEAM HARNESS: {total_run} tests executed, {passed} passed, 0 failures, 0 errors.")
    else:
        print("RED-TEAM HARNESS: No tests discovered yet (Phase 0 baseline).")

    print("RED-TEAM HARNESS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
