#!/usr/bin/env python3
"""Advisory pre-commit checklist for a new core module or a new hook.

Adding a file under ``src/divineos/core/`` or a script under
``.claude/hooks/`` has failed the first push four separate ways, each one only
visible late in the full push gate. This shows them at commit time, with the
exact line or number to add:

1. a new ``core/<file>.py`` with no tree line in ``docs/ARCHITECTURE.md``
   (the rule ``scripts/check_doc_counts.py`` enforces at push time);
2. a changed ``.claude/settings.json`` whose PreToolUse hook count no longer
   matches ``_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN`` in
   ``tests/test_every_exit_passes_every_gate.py``;
3. a new core module needs a prereg id in the commit message (a reminder only:
   the message does not exist yet at this point, so it cannot be checked);
4. a new ``.claude/hooks/*.sh`` not named in ``_NON_GATING_HOOKS`` in
   ``tests/test_gate_deny_messages_name_remedy.py``.

ADVISORY ON PURPOSE. It exits 0 always. A pre-commit step that can hold the
commit shut gets turned off, and then none of this is shown. The real gates
at push time are unchanged; this only moves their news earlier.

It reads those four places as text and never edits them or imports them, so
if one of them changes shape the answer here is "could not look", not a
confident wrong answer. Silence means "looked, nothing to add". A thing it
could not read is always said out loud, because silence and could-not-look
must never read the same.

Everything is read from the git INDEX (what will be committed), not the
working tree, because that is what the push gate will see.

Standard library plus git only.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ARCH_DOC = "docs/ARCHITECTURE.md"
SETTINGS = ".claude/settings.json"
EXIT_TEST = "tests/test_every_exit_passes_every_gate.py"
GATE_TEST = "tests/test_gate_deny_messages_name_remedy.py"
CORE_PREFIX = "src/divineos/core/"
HOOKS_DIR = ".claude/hooks/"


class CouldNotLook(Exception):
    """A thing this check needs to read could not be read."""


def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
        )
    except FileNotFoundError as exc:
        raise CouldNotLook("git is not installed or not on PATH") from exc
    if proc.returncode != 0:
        detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "no message"
        raise CouldNotLook(f"git {args[0]} failed: {detail}")
    return proc.stdout


def staged_changes(repo: Path) -> list[tuple[str, str]]:
    """(status letter, path) pairs from the index.

    ``--no-renames`` on purpose: a rename then shows as delete + add, so a file
    moved into ``core/`` is checked like any other new module.
    """
    # Outside a repository `git diff` falls back to a no-index mode and returns
    # nothing with exit 0, which would read as "looked, all clear".
    _git(repo, "rev-parse", "--git-dir")
    raw = _git(repo, "diff", "--cached", "--name-status", "--no-renames", "-z")
    tokens = raw.split("\0")
    pairs: list[tuple[str, str]] = []
    for i in range(0, len(tokens) - 1, 2):
        pairs.append((tokens[i][:1], tokens[i + 1]))
    return pairs


def staged_text(repo: Path, rel: str) -> str:
    """The version of ``rel`` that will be committed."""
    try:
        return _git(repo, "show", f":{rel}")
    except CouldNotLook as exc:
        raise CouldNotLook(f"{rel} is not in the staged tree ({exc})") from exc


def tree_paths(arch_text: str) -> set[str]:
    """Paths under src/divineos/ listed in the doc's tree block.

    Same reading as ``_parse_tree_block`` in scripts/check_doc_counts.py: the
    tree sits in the first code block after "## The tree", 2-space base indent,
    directories end in "/".
    """
    match = re.search(r"## The tree\s*\n\s*```\s*\n(.*?)```", arch_text, re.DOTALL)
    if not match:
        raise CouldNotLook(f'{ARCH_DOC} has no "## The tree" code block')
    paths: set[str] = set()
    stack: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("src/divineos/"):
            stack = []
            continue
        indent = len(line) - len(line.lstrip())
        depth = max(0, (indent - 2) // 2)
        stack = stack[:depth]
        name = stripped.split(None, 1)[0]
        if name.endswith("/"):
            stack.append(name.rstrip("/"))
        elif name.endswith(".py"):
            paths.add("/".join(stack + [name]))
    return paths


def check_tree_lines(repo: Path, added_core: list[str]) -> list[str]:
    if not added_core:
        return []
    try:
        listed = tree_paths(staged_text(repo, ARCH_DOC))
    except CouldNotLook as exc:
        return [f"could not look at {ARCH_DOC} for the new core module(s): {exc}"]
    out: list[str] = []
    for path in added_core:
        rel = path[len("src/divineos/") :]
        if rel in listed:
            continue
        indent = " " * (2 + 2 * (rel.count("/")))
        out.append(
            f"{rel} has no tree line in {ARCH_DOC} (check_doc_counts.py fails it at push). "
            f"Add this line inside the tree:\n{indent}{rel.rsplit('/', 1)[-1]}   "
            "<one line: what it is>"
        )
    return out


def pre_tool_use_count(settings_text: str) -> int:
    try:
        settings = json.loads(settings_text)
        return sum(len(group.get("hooks", [])) for group in settings["hooks"]["PreToolUse"])
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError) as exc:
        raise CouldNotLook(f"{SETTINGS} has no readable hooks.PreToolUse list ({exc!r})") from exc


def check_pretooluse_count(repo: Path, changes: list[tuple[str, str]]) -> list[str]:
    if not any(path == SETTINGS and status != "D" for status, path in changes):
        return []
    try:
        actual = pre_tool_use_count(staged_text(repo, SETTINGS))
        test_text = staged_text(repo, EXIT_TEST)
        pinned = re.search(
            r"^_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN\s*=\s*(\d+)", test_text, re.MULTILINE
        )
        if not pinned:
            raise CouldNotLook(f"{EXIT_TEST} has no _PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = <number>")
    except CouldNotLook as exc:
        return [f"could not look at the PreToolUse hook count: {exc}"]
    if actual == int(pinned.group(1)):
        return []
    return [
        f"{SETTINGS} now wires {actual} PreToolUse hook commands; {EXIT_TEST} pins "
        f"{pinned.group(1)}. Set it to:\n_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = {actual}\n"
        "(was " + pinned.group(1) + "). Also ask whether the new gate uses the shared "
        "remedy list; the number is a tripwire, not the whole check."
    ]


def declared_non_gating(test_text: str) -> set[str]:
    match = re.search(
        r"_NON_GATING_HOOKS\b[^=]*=\s*frozenset\(\s*\{(.*?)\}\s*\)", test_text, re.DOTALL
    )
    if not match:
        raise CouldNotLook(f"{GATE_TEST} has no _NON_GATING_HOOKS frozenset literal")
    # Comments name hooks too; only a quoted entry is a declaration.
    body = re.sub(r"#[^\n]*", "", match.group(1))
    return set(re.findall(r'"([^"]+)"', body))


def check_non_gating(repo: Path, added_hooks: list[str]) -> list[str]:
    if not added_hooks:
        return []
    try:
        declared = declared_non_gating(staged_text(repo, GATE_TEST))
    except CouldNotLook as exc:
        return [f"could not look at _NON_GATING_HOOKS for the new hook(s): {exc}"]
    out: list[str] = []
    for path in added_hooks:
        name = path.rsplit("/", 1)[-1]
        if name in declared:
            continue
        out.append(
            f"{name} is not named in _NON_GATING_HOOKS in {GATE_TEST}. If it never refuses, "
            f'add this line inside the set:\n        "{name}",\n'
            "    If it CAN refuse, leave it out: the test then checks its deny messages name a remedy."
        )
    return out


PREREG_REMINDER = (
    "The commit message for a new core module must name a prereg id (the commit gate: "
    "'include the relevant prereg ID'). Not checked here, the message is not written yet. "
    "File one with: divineos prereg file ... then put its prereg-<id> in the message."
)


def run(repo: Path) -> list[str]:
    try:
        changes = staged_changes(repo)
    except CouldNotLook as exc:
        return [f"could not look at the staged diff: {exc}"]
    added_core = [
        p
        for s, p in changes
        if s == "A"
        and p.startswith(CORE_PREFIX)
        and p.endswith(".py")
        and not p.endswith("__init__.py")
    ]
    added_hooks = [
        p
        for s, p in changes
        if s == "A"
        and p.startswith(HOOKS_DIR)
        and "/" not in p[len(HOOKS_DIR) :]
        and p.endswith(".sh")
    ]
    findings = check_tree_lines(repo, added_core)
    findings += check_pretooluse_count(repo, changes)
    findings += check_non_gating(repo, added_hooks)
    if added_core:
        findings.append(PREREG_REMINDER)
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo", default=".", help="repository to read (default: cwd)")
    args = parser.parse_args(argv)
    try:
        findings = run(Path(args.repo))
    except Exception as exc:  # noqa: BLE001 - the exit-0 promise is the contract: a crash here must be said out loud and must not hold a commit shut
        findings = [f"could not look: this checklist itself failed ({type(exc).__name__}: {exc})"]
    if findings:
        print("New-module checklist (advisory, never blocks the commit):")
        for item in findings:
            print(f"  - {item}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
