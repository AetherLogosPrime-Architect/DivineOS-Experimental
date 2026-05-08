#!/usr/bin/env python3
"""Check for theater-named functions in src/divineos/.

DivineOS convention (CLAUDE.md): "No theater naming. analyze_session()
not OrchestrateDeepCognition()." Function names should describe what
the function operationally does, not what it imaginatively suggests.

This check flags function names starting with mythological / grandiose
verbs that almost always signal theater drift. Conservative list to
keep false-positive rate near zero. Suppressible per-line with
``# noqa: BLE001`` (same suppression token as the broad-except scan,
because the discipline-class is "naming-honesty" and using one token
across both checks keeps the suppression-vocabulary small).

Per Dijkstra audit-walk observation 2026-05-07:
"Function-naming theater drift in places. Audit pass on function-names;
rename theater-drift cases to what-they-actually-do. Metaphor for
docstrings; calls should be plain."

Manual audit on filing-day found zero violations. The check ships as
preventive-infrastructure: future drift gets caught at commit-time
rather than via manual audit pass.

AST-based, fast enough for pre-commit (<1s on full src/ tree).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "divineos"

# Conservative theater-verb list. Each verb here suggests theater-shape
# almost regardless of context. Borderline-operational verbs (`invoke`,
# `surface`, `convene`, `distill`, `transform`) deliberately excluded
# to keep false-positive rate near zero.
_THEATER_VERBS = frozenset(
    {
        "orchestrate",
        "summon",
        "manifest",
        "weave",
        "channel",
        "embody",
        "transcend",
        "ascend",
        "unfurl",
        "blossom",
        "awaken",
        "harness",
        "wield",
        "behold",
        "reckon",
        "illuminate",
        "embrace",
        "metamorphose",
        "alchemize",
        "entwine",
        "enmesh",
        "birth",
    }
)

_NOQA_PAT = re.compile(r"#\s*noqa(?::\s*BLE001)?")


def _is_suppressed(line: str) -> bool:
    return bool(_NOQA_PAT.search(line))


def _scan_file(py_file: Path, source_lines: list[str]) -> list[str]:
    violations: list[str] = []
    try:
        rel = py_file.relative_to(ROOT)
    except ValueError:
        rel = py_file

    try:
        tree = ast.parse(chr(10).join(source_lines), filename=str(py_file))
    except SyntaxError:
        return violations

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = node.name.lstrip("_")
            first_word = name.split("_")[0].lower()
            if first_word not in _THEATER_VERBS:
                continue
            line_idx = node.lineno - 1
            if 0 <= line_idx < len(source_lines):
                line = source_lines[line_idx]
                if _is_suppressed(line):
                    continue
            violations.append(
                f"  {rel}:{node.lineno}: def {node.name}() -- starts with "
                f"theater verb {first_word!r}"
            )
    return violations


def find_violations() -> list[str]:
    out: list[str] = []
    for py_file in SRC.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out.extend(_scan_file(py_file, text.splitlines()))
    return out


def main() -> int:
    violations = find_violations()
    if violations:
        print(f"Theater-named function(s) found ({len(violations)}):")
        for v in violations:
            print(v)
        print(
            "Fix: rename to describe what the function operationally does. "
            "  Example: orchestrate_deep_cognition -> analyze_session. "
            "  Example: summon_council -> consult_council. "
            "Metaphors belong in docstrings, not at the call site. "
            "If the name is genuinely operational despite starting with one "
            "of these verbs, append '# noqa: BLE001' on the line."
        )
        return 1
    print("Function-naming check OK (no theater drift)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
