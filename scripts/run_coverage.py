#!/usr/bin/env python3
"""Run coverage analysis and report blind spots.

Usage:
    python scripts/run_coverage.py              # Full report
    python scripts/run_coverage.py --summary    # Summary only
    python scripts/run_coverage.py --html       # Generate HTML report
"""

import subprocess
import sys


def main() -> int:
    args = sys.argv[1:]
    summary_only = "--summary" in args
    html_report = "--html" in args

    cmd = [
        sys.executable, "-m", "pytest", "tests/",
        "-q", "--tb=no",
        "--cov=divineos",
        "--cov-branch",
        "--cov-report=term-missing",
    ]

    if html_report:
        cmd.append("--cov-report=html:coverage_html")

    result = subprocess.run(cmd, capture_output=not summary_only)

    if summary_only:
        # Re-run with just the summary
        cmd_summary = [
            sys.executable, "-m", "pytest", "tests/",
            "-q", "--tb=no",
            "--cov=divineos",
            "--cov-branch",
            "--cov-report=term",
        ]
        result = subprocess.run(cmd_summary)

    if html_report:
        print("\nHTML report generated: coverage_html/index.html")

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
