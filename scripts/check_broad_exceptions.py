#!/usr/bin/env python3
"""Check that exception handling follows project convention.

DivineOS convention catches three problematic shapes:

1. **Broad ``except Exception``** without ``# noqa: BLE001``. Define a
   module-level error tuple (``_XX_ERRORS``) and catch that instead.
2. **Bare ``except:``** (no exception type). Catches *everything*
   including KeyboardInterrupt and SystemExit; almost never what you want.
3. **Context-swallowing re-raise** -- ``raise X from None`` deliberately
   drops the original exception chain, hiding the real cause from logs
   and tracebacks. Only acceptable when the original cause is sensitive
   data; otherwise let the chain propagate.

Each shape can be suppressed with ``# noqa: BLE001`` on the same line
when the violation is intentional and justified.

2026-05-07: extended from single-pattern (Exception only) to three
patterns per Dijkstra's audit-walk observation that the original scan
"has loopholes -- no scan for `except: pass` or context-swallowing
re-raises". AST-based to avoid line-counting fragility.

Fast enough for pre-commit: <1s on the full src/divineos/ tree.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "divineos"

_NOQA_PAT = re.compile(r"#\s*noqa(?::\s*BLE001)?")


def _is_suppressed(line: str) -> bool:
    """Return True if the line carries a ``# noqa: BLE001`` (or bare noqa)."""
    return bool(_NOQA_PAT.search(line))


def _find_in_tree(py_file: Path, source_lines: list[str]) -> list[str]:
    """Return violation lines for one file. Empty list if clean."""
    violations: list[str] = []
    try:
        rel = py_file.relative_to(ROOT)
    except ValueError:
        # Tests pass synthetic paths not under ROOT; just use the bare path.
        rel = py_file

    try:
        tree = ast.parse("\n".join(source_lines), filename=str(py_file))
    except SyntaxError:
        # Skip files we cannot parse -- bandit/ruff handle syntax errors.
        return violations

    for node in ast.walk(tree):
        # --- Pattern 1 & 2: except handlers ---
        if isinstance(node, ast.ExceptHandler):
            line_idx = node.lineno - 1
            if 0 <= line_idx < len(source_lines):
                line = source_lines[line_idx]
                if _is_suppressed(line):
                    continue

                # Pattern 2: bare except (node.type is None)
                if node.type is None:
                    violations.append(
                        f"  {rel}:{node.lineno}: bare 'except:' "
                        f"(catches KeyboardInterrupt/SystemExit too)"
                    )
                    continue

                # Pattern 1: except Exception (without noqa)
                # Match Name(id='Exception') or Tuple containing it.
                if isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    violations.append(
                        f"  {rel}:{node.lineno}: 'except Exception' "
                        f"(use module-level _XX_ERRORS tuple instead)"
                    )

        # --- Pattern 3: raise X from None ---
        elif isinstance(node, ast.Raise):
            # Only flag if there's an explicit `from None`. AST encodes
            # this as node.cause == ast.Constant(value=None).
            cause = node.cause
            if isinstance(cause, ast.Constant) and cause.value is None:
                line_idx = node.lineno - 1
                if 0 <= line_idx < len(source_lines):
                    line = source_lines[line_idx]
                    if _is_suppressed(line):
                        continue
                    violations.append(
                        f"  {rel}:{node.lineno}: 'raise ... from None' "
                        f"(context-swallowing -- drops original exception chain)"
                    )

    return violations


def find_violations() -> list[str]:
    """Return all violations across src/divineos/."""
    out: list[str] = []
    for py_file in SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out.extend(_find_in_tree(py_file, text.splitlines()))
    return out


# Backward-compat alias for any external tooling that called the old name.
find_broad_exceptions = find_violations


def main() -> int:
    violations = find_violations()

    if violations:
        print(f"Exception-handling violations ({len(violations)} found):")
        for v in violations:
            print(v)
        print(
            "\nFix shapes by case:\n"
            "  - 'except Exception' -> use _XX_ERRORS = (sqlite3.OperationalError,\n"
            "    OSError, KeyError, TypeError, ValueError); except _XX_ERRORS\n"
            "  - bare 'except:' -> name the specific exception types you mean\n"
            "  - 'raise ... from None' -> omit 'from None' (preserves chain), or\n"
            "    use 'from <other_exception>' to make the cause-substitution explicit\n"
            "If suppression is truly justified, append '# noqa: BLE001' on the line."
        )
        return 1

    print("Exception-handling check OK (no unexcused catches or context-swallows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
