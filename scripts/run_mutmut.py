#!/usr/bin/env python3
"""Run mutation testing on critical modules.

Mutation testing changes your code and checks if tests catch the change.
Surviving mutants = test blind spots.

Usage:
    python scripts/run_mutmut.py                          # Default critical modules
    python scripts/run_mutmut.py --module quality_gate    # Specific module
    python scripts/run_mutmut.py --results                # Show last run results
"""

import subprocess
import sys

# Modules where correctness matters most — mutation test these
CRITICAL_MODULES = [
    "src/divineos/core/quality_gate.py",
    "src/divineos/core/trust_tiers.py",
    "src/divineos/core/moral_compass.py",
    "src/divineos/core/guardrails.py",
    "src/divineos/core/knowledge/_text.py",
    "src/divineos/supersession/contradiction_detector.py",
]


def main() -> int:
    args = sys.argv[1:]

    if "--results" in args:
        result = subprocess.run([sys.executable, "-m", "mutmut", "results"])
        return result.returncode

    if "--module" in args:
        idx = args.index("--module")
        if idx + 1 < len(args):
            module_name = args[idx + 1]
            targets = [m for m in CRITICAL_MODULES if module_name in m]
            if not targets:
                targets = [f"src/divineos/core/{module_name}.py"]
        else:
            print("Usage: --module <name>")
            return 1
    else:
        targets = CRITICAL_MODULES

    for target in targets:
        print(f"\n{'='*60}")
        print(f"Mutating: {target}")
        print(f"{'='*60}\n")

        cmd = [
            sys.executable, "-m", "mutmut", "run",
            "--paths-to-mutate", target,
            "--tests-dir", "tests/",
            "--runner", f"{sys.executable} -m pytest tests/ -q --tb=no -x",
        ]

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n[!] Mutants survived in {target} — review with: mutmut results")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
