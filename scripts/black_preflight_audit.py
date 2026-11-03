#!/usr/bin/env python3
"""BLACK Framework v2.2 Pre-Flight Audit Gate.

Verifies repository hygiene, zero-dependency invariants, banned tokens,
AST-level precision rules, and test-fixture immutability under remediation mode.
"""

import ast
import argparse
import subprocess
import sys
from pathlib import Path

BANNED_STRINGS = [
    "localhost",
    "127.0.0.1",
    "TODO",
    "FIXME",
]

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
ROOT_DIR = Path(__file__).resolve().parent.parent


def check_banned_tokens(allow_stubs: bool = False) -> list:
    violations = []
    tokens = list(BANNED_STRINGS)
    if not allow_stubs:
        tokens.append("NotImplementedError")

    for py_file in SRC_DIR.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
        except Exception as e:
            violations.append(f"Failed to read {py_file}: {e}")
            continue

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            for token in tokens:
                if token in line:
                    violations.append(f"{py_file.relative_to(ROOT_DIR)}:{idx} contains banned token '{token}'")
    return violations


def check_zero_dependencies() -> list:
    violations = []
    pyproject = ROOT_DIR / "pyproject.toml"
    if not pyproject.exists():
        return ["pyproject.toml not found"]

    content = pyproject.read_text(encoding="utf-8")
    if "dependencies = []" not in content:
        violations.append("pyproject.toml must declare 'dependencies = []' (zero runtime dependencies)")
    return violations


def check_ast_rules() -> list:
    violations = []
    for target_name in ["api.py", "connector.py"]:
        matches = list(SRC_DIR.rglob(target_name))
        for target in matches:
            try:
                tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
            except Exception as e:
                violations.append(f"AST parse error in {target}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    if isinstance(func, ast.Name) and func.id == "round":
                        violations.append(
                            f"Rule 18 violation: Call to round() detected in {target.relative_to(ROOT_DIR)}:{node.lineno}"
                        )
    return violations


def check_remediation_mode() -> list:
    violations = []
    try:
        cmd = ["git", "diff", "--name-only", "HEAD", "--", "tests/"]
        res = subprocess.run(cmd, cwd=str(ROOT_DIR), capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            modified = res.stdout.strip().splitlines()
            violations.append(
                f"Rule 17 violation: Test files modified during remediation mode: {modified}"
            )
    except Exception as e:
        violations.append(f"Git check error in remediation mode: {e}")
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="BLACK Pre-Flight Audit Gate")
    parser.add_argument("--remediation-mode", action="store_true", help="Verify tests/ is untouched")
    parser.add_argument("--allow-stubs", action="store_true", help="Allow NotImplementedError stubs (Phase 0 only)")
    args = parser.parse_args()

    all_violations = []

    dep_violations = check_zero_dependencies()
    all_violations.extend(dep_violations)

    token_violations = check_banned_tokens(allow_stubs=args.allow_stubs)
    all_violations.extend(token_violations)

    ast_violations = check_ast_rules()
    all_violations.extend(ast_violations)

    if args.remediation_mode:
        remed_violations = check_remediation_mode()
        all_violations.extend(remed_violations)

    if all_violations:
        print("BLACK PRE-FLIGHT AUDIT FAILED:")
        for v in all_violations:
            print(f"  - {v}")
        return 1

    print("BLACK GATE PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
