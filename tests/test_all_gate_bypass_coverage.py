"""Meta-class-fix for the bypass-coverage class.

Aletheia Finding 56 (2026-05-15) named the layer-4 failure shape:
Finding 37's class-fix test was scoped only to Gate 1.48
(stale_engagement). Two new gates shipped on the same branch — Gate
4.5 (os-engagement-for-os-work) and sleep-readiness — both with
deny-messages naming recovery commands NOT in the bypass list
(`council`, `claim`). The narrow scope of the original class-fix
test allowed the same class-failure to ship twice immediately
after it was first caught.

THIS TEST IS THE META-CLASS-FIX. It walks the source of
pre_tool_use_gate.py, finds every _make_deny(...) call, extracts
the message string, regex-scans for `divineos <subcmd>` references,
and asserts each first subcommand token is in the bypass list.

If a future gate ships with a deny-message that names a command
NOT in the bypass list — regardless of which gate, regardless of
which area — this test fails CI.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


def _gate_source() -> str:
    src_path = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "divineos"
        / "hooks"
        / "pre_tool_use_gate.py"
    )
    return src_path.read_text(encoding="utf-8")


_DIVINEOS_SUBCMD_RE = re.compile(r"\bdivineos\s+(\w[\w-]*)")

# List-style recovery hint: "divineos X, Y, or Z" / "divineos X, Y, Z".
# After the prefixed first match, additional comma-separated bare words
# (with optional "or"/"and") are also recovery-command references.
_LIST_TAIL_RE = re.compile(
    r"\bdivineos\s+\w[\w-]*((?:\s*,\s*(?:or\s+|and\s+)?\w[\w-]*)+)"
)
_BARE_WORD_RE = re.compile(r"(?:,\s*(?:or\s+|and\s+)?)(\w[\w-]*)")


def _extract_deny_strings(source: str) -> list[str]:
    """Find every _make_deny() call and extract the string argument."""
    tree = ast.parse(source)
    deny_strings: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name != "_make_deny":
            continue

        if not node.args:
            continue
        arg = node.args[0]

        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            deny_strings.append(arg.value)
            continue

        if isinstance(arg, ast.JoinedStr):
            parts: list[str] = []
            for piece in arg.values:
                if isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                    parts.append(piece.value)
                elif isinstance(piece, ast.FormattedValue):
                    parts.append(" ")
            deny_strings.append("".join(parts))
            continue

        if isinstance(arg, ast.BinOp):
            try:
                collected = ast.unparse(arg)
                deny_strings.append(collected)
            except Exception:
                pass

    return deny_strings


def _extract_divineos_subcommands(text: str) -> set[str]:
    """Extract every divineos-subcommand referenced in text, including
    list-style continuations like 'divineos ask, recall, or council'."""
    refs: set[str] = set()
    # First-position prefixed matches: "divineos X"
    for m in _DIVINEOS_SUBCMD_RE.finditer(text):
        refs.add(m.group(1))
    # List-tail continuations: "divineos X, Y, or Z" → also capture Y, Z
    for m in _LIST_TAIL_RE.finditer(text):
        tail = m.group(1)
        for bare in _BARE_WORD_RE.finditer(tail):
            refs.add(bare.group(1))
    return refs


def test_every_deny_message_subcommand_is_bypassed() -> None:
    """LOAD-BEARING (meta-class-fix per Aletheia Finding 56):
    every divineos-subcommand referenced in any gate's deny-message
    must be in _BYPASS_DIVINEOS_SUBCOMMANDS.
    """
    from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS

    source = _gate_source()
    deny_strings = _extract_deny_strings(source)

    assert deny_strings, (
        "No _make_deny() calls extracted from pre_tool_use_gate.py — "
        "the test isn't seeing any gates."
    )

    all_referenced: set[str] = set()
    per_string_refs: dict[int, set[str]] = {}
    for idx, msg in enumerate(deny_strings):
        refs = _extract_divineos_subcommands(msg)
        all_referenced.update(refs)
        if refs:
            per_string_refs[idx] = refs

    missing = all_referenced - _BYPASS_DIVINEOS_SUBCOMMANDS

    diagnostic_lines: list[str] = []
    if missing:
        for idx, refs in per_string_refs.items():
            local_missing = refs - _BYPASS_DIVINEOS_SUBCOMMANDS
            if local_missing:
                snippet = deny_strings[idx][:120].replace("\n", " ")
                diagnostic_lines.append(
                    f"  - deny-message #{idx} ({snippet!r}...): "
                    f"missing {sorted(local_missing)}"
                )

    assert not missing, (
        f"Catch-22 risk: these divineos subcommands are named as "
        f"recovery paths in deny-messages but NOT in "
        f"_BYPASS_DIVINEOS_SUBCOMMANDS: {sorted(missing)}\n\n"
        f"Per-gate diagnostic:\n" + "\n".join(diagnostic_lines)
    )


def test_at_least_one_deny_message_references_a_subcommand() -> None:
    """Sanity check: AT LEAST ONE gate names a recovery command."""
    source = _gate_source()
    deny_strings = _extract_deny_strings(source)
    all_referenced: set[str] = set()
    for msg in deny_strings:
        all_referenced.update(_extract_divineos_subcommands(msg))
    assert all_referenced


def test_bypass_list_contains_load_bearing_recovery_commands() -> None:
    """Anchor test: load-bearing recovery commands must always remain."""
    from divineos.hooks.pre_tool_use_gate import _BYPASS_DIVINEOS_SUBCOMMANDS

    load_bearing = {"briefing", "ask", "recall", "compass-ops", "learn"}
    missing = load_bearing - _BYPASS_DIVINEOS_SUBCOMMANDS
    assert not missing
