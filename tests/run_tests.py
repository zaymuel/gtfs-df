"""
run_tests.py - Programmatic test runner with coverage measurement.
"""

import sys
from pathlib import Path
import coverage
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

if __name__ == "__main__":
    cov = coverage.Coverage(source=["scripts"])
    cov.start()

    exit_code = pytest.main(["tests", "-v"])

    cov.stop()
    cov.save()

    print("\n" + "=" * 60)
    print("           AUTOMATED CODE COVERAGE REPORT (scripts/)")
    print("=" * 60)
    total_pct = cov.report(show_missing=True)
    print("=" * 60)
    print(f"TOTAL CODEBASE COVERAGE: {total_pct:.2f}%")
    print("=" * 60)
    sys.exit(exit_code)
