#!/usr/bin/env python3
"""Run bandit security scan and summarize findings.

Usage:
    python scripts/run_bandit.py           # Medium+ severity
    python scripts/run_bandit.py --all     # All severities
    python scripts/run_bandit.py --strict  # Fail on any finding
"""

import subprocess
import sys


def main() -> int:
    args = sys.argv[1:]
    show_all = "--all" in args
    strict = "--strict" in args

    cmd = [
        sys.executable, "-m", "bandit",
        "-r", "src/divineos/",
        "-f", "txt",
        "-s", "B101",  # Skip assert_used (tests use asserts)
        "--exclude", "tests",
    ]

    if not show_all:
        cmd.extend(["-ll"])  # Medium+ severity only

    result = subprocess.run(cmd)

    if strict and result.returncode != 0:
        print("\n[!] Bandit found issues — strict mode, failing.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
