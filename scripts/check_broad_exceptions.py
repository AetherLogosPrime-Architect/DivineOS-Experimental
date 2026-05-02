#!/usr/bin/env python3
"""Check that broad 'except Exception' catches follow project convention.

DivineOS convention: define a module-level error tuple (_XX_ERRORS) and catch
that instead of bare Exception. Any 'except Exception' without '# noqa: BLE001'
is flagged.

Fast enough for pre-commit: pure grep, no imports.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "divineos"


def find_broad_exceptions() -> list[str]:
    """Find except Exception catches that aren't explicitly allowed."""
    violations: list[str] = []

    for py_file in SRC.rglob("*.py"):
        rel = py_file.relative_to(ROOT)
        text = py_file.read_text(encoding="utf-8", errors="replace")

        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            # Match 'except Exception' with optional 'as e:' suffix
            if re.match(r"except\s+Exception\b", stripped):
                # Allow if explicitly marked with noqa
                if "noqa: BLE001" in line:
                    continue
                violations.append(f"  {rel}:{i}: {stripped}")

    return violations


def main() -> int:
    violations = find_broad_exceptions()

    if violations:
        print(f"Broad 'except Exception' without noqa: BLE001 ({len(violations)} found):")
        for v in violations:
            print(v)
        print(
            "\nFix: Define a _XX_ERRORS tuple (sqlite3.OperationalError, OSError, "
            "KeyError, TypeError, ValueError) and catch that instead."
        )
        print("If truly needed, add '# noqa: BLE001' to suppress.")
        return 1

    print("Broad exception check OK (no unexcused catches)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
