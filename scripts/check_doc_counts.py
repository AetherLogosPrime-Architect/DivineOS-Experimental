#!/usr/bin/env python3
"""Check that documented test/command counts haven't drifted from reality.

Greps the actual codebase for test functions and CLI commands, then compares
to the numbers in CLAUDE.md, README.md, and seed.json.  Fails if any
documented count has drifted beyond the allowed threshold.

Fast enough for pre-commit: pure grep, no imports or pytest collection.
"""

import re
import sys
from pathlib import Path

# How far the docs can drift before we complain.
TEST_DRIFT_THRESHOLD = 50  # tests get added/removed in batches
CMD_DRIFT_THRESHOLD = 5

ROOT = Path(__file__).resolve().parent.parent


def count_test_functions() -> int:
    """Count 'def test_*' across all test files."""
    total = 0
    for f in (ROOT / "tests").rglob("test_*.py"):
        total += f.read_text(errors="replace").count("\n    def test_")
        total += f.read_text(errors="replace").count("\ndef test_")
    return total


def count_cli_commands() -> int:
    """Count @group.command() decorators in CLI modules."""
    total = 0
    for f in (ROOT / "src" / "divineos" / "cli").rglob("*.py"):
        total += len(re.findall(r"@\w+\.command\b", f.read_text(errors="replace")))
    return total


def extract_documented_counts(path: Path) -> list[tuple[str, int, str]]:
    """Pull (label, number, context) tuples from a file."""
    findings: list[tuple[str, int, str]] = []
    text = path.read_text(errors="replace")

    # Match patterns like "2,608+ tests" or "2608 tests"
    for m in re.finditer(r"([\d,]+)\+?\s+tests", text):
        num = int(m.group(1).replace(",", ""))
        findings.append(("tests", num, f"{path.name}: {m.group(0)}"))

    # Match patterns like "109 commands"
    for m in re.finditer(r"(\d+)\s+commands", text):
        num = int(m.group(1))
        findings.append(("commands", num, f"{path.name}: {m.group(0)}"))

    return findings


def main() -> int:
    actual_tests = count_test_functions()
    actual_cmds = count_cli_commands()

    doc_files = [
        ROOT / "CLAUDE.md",
        ROOT / "README.md",
        ROOT / "src" / "divineos" / "seed.json",
    ]

    errors: list[str] = []

    for doc_file in doc_files:
        if not doc_file.exists():
            continue
        for label, documented, context in extract_documented_counts(doc_file):
            if label == "tests":
                actual = actual_tests
                threshold = TEST_DRIFT_THRESHOLD
            else:
                actual = actual_cmds
                threshold = CMD_DRIFT_THRESHOLD

            drift = abs(actual - documented)
            if drift > threshold:
                errors.append(
                    f"  {context}\n"
                    f"    documented: {documented}, actual: {actual}, drift: {drift}"
                )

    if errors:
        print(f"Doc count drift detected (tests={actual_tests}, commands={actual_cmds}):")
        print("\n".join(errors))
        print(f"\nUpdate the documented counts to match reality.")
        return 1

    print(f"Doc counts OK (tests={actual_tests}, commands={actual_cmds})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
