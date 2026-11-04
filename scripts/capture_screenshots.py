#!/usr/bin/env python3
"""Automated UI Screenshot Generator for BenchWarmer Documentation.

Executes headless Selenium browser automation to capture high-resolution
screenshots of every major user interface view and modal for markdown documentation.
"""

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "src"))

import unittest
from tests.unit.test_selenium_ui import TestSeleniumUI


def main():
    print("=" * 60)
    print("BenchWarmer UI Screenshot Capture Suite")
    print("Target output: docs/screenshots/")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestSeleniumUI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\nAll UI screenshots captured successfully!")
        shots = list((ROOT_DIR / "docs" / "screenshots").glob("*.png"))
        for s in sorted(shots):
            print(f"  - {s.name} ({s.stat().st_size / 1024:.1f} KB)")
        return 0
    else:
        print("\nScreenshot capture failed with errors.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
