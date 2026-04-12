#!/usr/bin/env python3
"""Run mutation testing on critical modules.

Mutation testing changes your code and checks if tests catch the change.
Surviving mutants = test blind spots.

Two modes:
  --quick   Lightweight built-in mutator (works everywhere, ~2 min)
  --full    Full mutmut run (requires WSL on Windows, thorough)

Usage:
    python scripts/run_mutmut.py                          # Quick mode (default)
    python scripts/run_mutmut.py --quick                  # Same as default
    python scripts/run_mutmut.py --full                   # Full mutmut
    python scripts/run_mutmut.py --module quality_gate    # Specific module
    python scripts/run_mutmut.py --results                # Show last mutmut results
"""

import re
import subprocess
import sys
from pathlib import Path

# Modules where correctness matters most — mutation test these
CRITICAL_MODULES = [
    "src/divineos/cli/pipeline_gates.py",
    "src/divineos/core/trust_tiers.py",
    "src/divineos/core/moral_compass.py",
    "src/divineos/core/guardrails.py",
    "src/divineos/core/knowledge/_text.py",
    "src/divineos/supersession/contradiction_detector.py",
    "src/divineos/core/knowledge/crud.py",
    "src/divineos/core/knowledge/extraction.py",
]

# Map source modules to their test files
MODULE_TEST_MAP = {
    "src/divineos/cli/pipeline_gates.py": "tests/test_quality_gate.py",
    "src/divineos/core/trust_tiers.py": "tests/test_trust_tiers.py",
    "src/divineos/core/moral_compass.py": "tests/test_moral_compass.py",
    "src/divineos/core/guardrails.py": "tests/test_guardrails.py",
    "src/divineos/core/knowledge/_text.py": "tests/test_extraction_noise.py",
    "src/divineos/supersession/contradiction_detector.py": "tests/test_contradiction_resolution_unit.py",
    "src/divineos/core/knowledge/crud.py": "tests/test_consolidation.py",
    "src/divineos/core/knowledge/extraction.py": "tests/test_extraction_pipeline.py",
}


# -- Quick Mutation Tester -----------------------------------------------
# A lightweight mutator that works on any platform. Tests a focused set
# of mutations: boundary conditions, boolean flips, comparison operators.


def _find_numeric_comparisons(source: str) -> list[dict]:
    """Find comparison operators with numeric values — prime mutation targets."""
    pattern = re.compile(
        r"(\w+)\s*(>=|<=|>|<|==|!=)\s*(\d+\.?\d*)",
    )
    mutations = []
    for i, line in enumerate(source.splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        for match in pattern.finditer(line):
            var, op, val = match.groups()
            mutations.append(
                {
                    "line": i,
                    "original": f"{var} {op} {val}",
                    "op": op,
                    "val": val,
                    "col": match.start(),
                }
            )
    return mutations


def _mutate_op(op: str) -> list[str]:
    """Generate mutations for a comparison operator."""
    opposites = {
        ">=": [">", "<=", "=="],
        "<=": ["<", ">=", "=="],
        ">": [">=", "<"],
        "<": ["<=", ">"],
        "==": ["!="],
        "!=": ["=="],
    }
    return opposites.get(op, [])


def _find_boolean_returns(source: str) -> list[dict]:
    """Find 'return True' and 'return False' — flip them."""
    mutations = []
    for i, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if stripped == "return True":
            mutations.append({"line": i, "original": "return True", "flip": "return False"})
        elif stripped == "return False":
            mutations.append({"line": i, "original": "return False", "flip": "return True"})
    return mutations


def run_quick_mutations(target: str, test_file: str | None = None) -> dict:
    """Run quick mutation tests on a single source file.

    Returns {tested, killed, survived, kill_rate, survivors}.
    """
    source_path = Path(target)
    if not source_path.exists():
        return {"error": f"File not found: {target}"}

    source = source_path.read_text(encoding="utf-8")
    lines = source.splitlines()

    # Gather mutation candidates
    comparisons = _find_numeric_comparisons(source)
    booleans = _find_boolean_returns(source)

    tested = 0
    killed = 0
    survived = 0
    survivors: list[str] = []

    test_cmd = [sys.executable, "-m", "pytest", "-x", "-q", "--tb=no"]
    if test_file and Path(test_file).exists():
        test_cmd.append(test_file)
    else:
        test_cmd.append("tests/")

    # Test comparison mutations
    for mut in comparisons:
        for new_op in _mutate_op(mut["op"]):
            mutated_line = lines[mut["line"] - 1].replace(
                f" {mut['op']} {mut['val']}",
                f" {new_op} {mut['val']}",
                1,
            )
            if mutated_line == lines[mut["line"] - 1]:
                continue  # Replacement didn't change anything

            mutated_source = lines.copy()
            mutated_source[mut["line"] - 1] = mutated_line

            # Write mutated file
            source_path.write_text("\n".join(mutated_source), encoding="utf-8")
            try:
                result = subprocess.run(
                    test_cmd,
                    capture_output=True,
                    timeout=60,
                )
                tested += 1
                if result.returncode != 0:
                    killed += 1
                else:
                    survived += 1
                    survivors.append(
                        f"  L{mut['line']}: {mut['op']} -> {new_op} ({mut['original']})"
                    )
            except subprocess.TimeoutExpired:
                killed += 1  # Timeout = caught
                tested += 1
            finally:
                # Restore original
                source_path.write_text(source, encoding="utf-8")

    # Test boolean mutations
    for mut in booleans:
        mutated_source = lines.copy()
        mutated_source[mut["line"] - 1] = lines[mut["line"] - 1].replace(
            mut["original"], mut["flip"]
        )

        source_path.write_text("\n".join(mutated_source), encoding="utf-8")
        try:
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                timeout=60,
            )
            tested += 1
            if result.returncode != 0:
                killed += 1
            else:
                survived += 1
                survivors.append(f"  L{mut['line']}: {mut['original']} -> {mut['flip']}")
        except subprocess.TimeoutExpired:
            killed += 1
            tested += 1
        finally:
            source_path.write_text(source, encoding="utf-8")

    kill_rate = (killed / tested * 100) if tested > 0 else 0.0
    return {
        "tested": tested,
        "killed": killed,
        "survived": survived,
        "kill_rate": kill_rate,
        "survivors": survivors,
    }


def run_full_mutmut(targets: list[str]) -> int:
    """Run full mutmut (requires WSL on Windows)."""
    for target in targets:
        print(f"\n{'=' * 60}")
        print(f"Mutating: {target}")
        print(f"{'=' * 60}\n")

        cmd = [
            sys.executable,
            "-m",
            "mutmut",
            "run",
            "--paths-to-mutate",
            target,
            "--tests-dir",
            "tests/",
            "--runner",
            f"{sys.executable} -m pytest tests/ -q --tb=no -x",
        ]

        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n[!] Mutants survived in {target} — review with: mutmut results")

    return 0


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

    if "--full" in args:
        return run_full_mutmut(targets)

    # Quick mode (default)
    print("Quick Mutation Testing — critical modules")
    print("=" * 55)
    print()

    total_tested = 0
    total_killed = 0
    all_survivors: list[str] = []

    for target in targets:
        test_file = MODULE_TEST_MAP.get(target)
        short_name = Path(target).stem
        print(f"  {short_name}...", end=" ", flush=True)

        result = run_quick_mutations(target, test_file)

        if "error" in result:
            print(f"SKIP ({result['error']})")
            continue

        if result["tested"] == 0:
            print("no mutation candidates")
            continue

        total_tested += result["tested"]
        total_killed += result["killed"]

        rate = result["kill_rate"]
        color = "OK" if rate >= 80 else "WARN" if rate >= 60 else "FAIL"
        print(f"{color} {result['killed']}/{result['tested']} killed ({rate:.0f}%)")

        if result["survivors"]:
            all_survivors.append(f"\n  {short_name}:")
            all_survivors.extend(result["survivors"])

    print()
    overall_rate = (total_killed / total_tested * 100) if total_tested > 0 else 0
    print(f"Overall: {total_killed}/{total_tested} mutations killed ({overall_rate:.0f}%)")

    if all_survivors:
        print(f"\nSurviving mutants ({len(all_survivors) - len(targets)} blind spots):")
        for s in all_survivors:
            print(s)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
