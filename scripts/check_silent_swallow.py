#!/usr/bin/env python3
"""Check for silent-swallow handlers added in NEW diff lines.

The fail-loud audit class Aether named 2026-06-23 after finding two
real instances today (his conftest, my hooks). The pattern: fail-soft
handlers that swallow real bugs invisibly. They look protective but
hide failure-modes the optimizer would otherwise have to address.

This check flags NEW additions only (diff-mode) so existing instances
ungate the PR while case-by-case cleanup continues separately. Per
the council walk 2026-06-23 (prereg-<filed>): Carmack lens for the
simple-concrete shape, Knuth lens for the boundary-case escape
(``# fail-soft: <reason>`` comment with substantive reason allows
legitimate uses through).

## What it catches

Python:
* ``ignore_errors=True``                       — shutil.rmtree, others
* ``errors="ignore"`` / ``errors='ignore'``    — subprocess encoding
* ``except ...: pass``                         — bare swallow without log

Bash/shell (in .sh files):
* ``2>/dev/null``                              — stderr silencing
* ``|| true``                                  — error swallowing in pipelines

## Escape hatch

Add ``# fail-soft: <reason>`` (Python) or ``# fail-soft: <reason>``
on the same line (bash) where the reason is at least 30 chars and
explains why silent-swallow is genuinely correct. The comment is
parsed; missing or short reasons fail the check.

## Why diff-mode

The codebase has many existing silent-swallow instances. Sweeping
them all at once would be a multi-week refactor (Taleb's via-negativa
shape, reserved as separate work). The check fires on PR diffs only
so growth stops while cleanup happens incrementally.
"""

from __future__ import annotations

import re
import subprocess
import sys

# Patterns — each is (compiled_regex, human_name)
PY_PATTERNS = [
    (re.compile(r"\bignore_errors\s*=\s*True\b"), "ignore_errors=True"),
    (re.compile(r"\berrors\s*=\s*['\"]ignore['\"]"), "errors='ignore'"),
    # except-pass: a single-line "except ...: pass" form. Multi-line
    # except-pass is caught by the existing AST scan in
    # check_broad_exceptions.py for broader-except cases.
    (re.compile(r"\bexcept\s+[^:]*:\s*pass\b"), "except ...: pass"),
]

SH_PATTERNS = [
    (re.compile(r"2>/dev/null"), "2>/dev/null"),
    (re.compile(r"\|\|\s*true\b"), "|| true"),
]

# Known-good shell idioms that intentionally silent-swallow and are
# correct by construction. Each one has its justification recorded in
# this single place rather than annotating every call-site (DRY for the
# explicit-reasoning requirement). Adding a NEW idiom here is itself a
# design decision worth reviewing.
#
# 2026-06-23 council-walk Knuth-lens fix: without this, the check fires
# 20+ times on standard hook-prelude in any new .claude/hooks/*.sh,
# which would push hook-authors to either bypass the check or sprinkle
# comments mechanically — both bad outcomes. The whitelist anchors the
# legitimate uses with their reasoning so the check doesn't degrade.
KNOWN_GOOD_SH_IDIOMS = [
    # Standard hook-prelude: no stdin → exit clean (hook must not crash
    # if invoked without input; the empty-input path returns exit 0).
    re.compile(r'INPUT="\$\(cat\s+2>/dev/null\s*\|\|\s*true\)"'),
    re.compile(r'STDIN_JSON="\$\(cat\s+2>/dev/null\s*\|\|\s*echo'),
    # git-toplevel fallback: hook outside any git tree falls back to "."
    # rather than dying. Returning "." means subsequent cd-into-it stays
    # in cwd, which is the right shape for non-repo invocations.
    re.compile(r'\$\(git\s+rev-parse\s+--show-toplevel\s+2>/dev/null\s*\|\|\s*echo\s*"?\.?"?\)'),
    # source-helper fallback: if _lib.sh is missing the hook exits clean
    # rather than crashing the tool call. The hook's job is fail-open,
    # not fail-on-missing-helper.
    re.compile(r'source\s+"?\$REPO_ROOT/\.claude/hooks/_lib\.sh"?\s+2>/dev/null\s*\|\|\s*exit\s+0'),
    # Idempotent file ops: mkdir -p and touch are inherently retry-safe;
    # silencing the "already exists" / racy-create warning is correct.
    re.compile(r"\bmkdir\s+-p\s+[^|;&]+2>/dev/null"),
    re.compile(r"\btouch\s+[^|;&]+2>/dev/null"),
    # Embedded-python heredoc: || true so a python that exits non-zero
    # doesn't bubble up as a hook failure (hook itself is fail-open).
    re.compile(r'"\$PYTHON_BIN"\s+-\s+<<\'PYEOF\'\s+2>/dev/null\s*\|\|\s*true'),
    # Inline python stderr suppression for one-line probes that are
    # purely advisory (e.g., extracting transcript_path from hook JSON).
    re.compile(r"print\('',\s*end=''\)\"\s+2>/dev/null"),
]


def _line_matches_known_good_sh_idiom(line: str) -> bool:
    """True if a shell line matches a documented known-good silent-swallow
    idiom. The justification lives in KNOWN_GOOD_SH_IDIOMS comments above,
    one place to maintain rather than annotating every call-site."""
    return any(pat.search(line) for pat in KNOWN_GOOD_SH_IDIOMS)


# Escape-hatch comment shape. Reason must be at least 30 chars after
# the `fail-soft:` marker so a one-word "fine" doesn't satisfy it.
_FAIL_SOFT_COMMENT = re.compile(r"#\s*fail-soft\s*:\s*(.{30,})")


def _git_added_lines() -> dict[str, list[tuple[int, str, str]]]:
    """Return {file_path: [(line_no, line_text, prev_line_text), ...]} for
    each ADDED line in the diff vs origin/main. Modified files but
    unmodified lines are excluded — we only care about NEW silent-swallow
    instances. ``prev_line_text`` is the line immediately preceding this
    added line in the diff (could be the previous added line, or empty if
    no immediate predecessor) — used so a `# fail-soft: <reason>` comment
    on the line BEFORE the pattern (a natural placement for one-liners)
    still excuses the violation."""
    try:
        # `origin/main` (not `origin/main...HEAD`) so unstaged and staged
        # working-tree changes are both included. The check fires on PR
        # diffs (precommit + CI), so what matters is "all NEW additions
        # this branch carries vs main," regardless of commit boundary.
        # encoding='utf-8' with errors='replace' — Windows default cp1252
        # crashes on bytes >0x7F which appear in commit messages containing
        # em-dashes, curly quotes, or non-Latin-1 letters. text=True inherits
        # locale encoding, so we specify utf-8 explicitly and never crash.
        diff_out = subprocess.run(
            ["git", "diff", "--unified=0", "origin/main"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return {}
    if diff_out.stdout is None:
        return {}

    result: dict[str, list[tuple[int, str, str]]] = {}
    current_file: str | None = None
    current_line: int = 0
    prev_added_line_text: str = ""
    for raw in diff_out.stdout.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw[6:]
            prev_added_line_text = ""
            continue
        if raw.startswith("--- "):
            current_file = None
            prev_added_line_text = ""
            continue
        if raw.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
            if m:
                current_line = int(m.group(1))
            prev_added_line_text = ""  # hunk boundary breaks adjacency
            continue
        if current_file is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            line_text = raw[1:]
            result.setdefault(current_file, []).append(
                (current_line, line_text, prev_added_line_text)
            )
            prev_added_line_text = line_text
            current_line += 1
        elif not raw.startswith("-"):
            prev_added_line_text = ""  # unchanged-context line breaks adjacency too
            current_line += 1

    return result


def _patterns_for_file(path: str) -> list[tuple[re.Pattern[str], str]]:
    if path.endswith(".py"):
        return PY_PATTERNS
    if path.endswith(".sh"):
        return SH_PATTERNS
    return []


def _line_has_fail_soft_excuse(line: str) -> bool:
    """True if the line carries a `# fail-soft: <reason>` comment with
    a reason of substance (>= 30 chars). Substantive-reason requirement
    is the Knuth-lens fix from the council walk — without it the comment
    becomes universal boilerplate the optimizer adds everywhere."""
    return bool(_FAIL_SOFT_COMMENT.search(line))


def _line_is_comment(line: str, path: str) -> bool:
    """True if the line is a pure comment (no executable code on it).

    Caught during first-run testing: the check matched `ignore_errors=True`
    inside a Python comment in conftest.py that DESCRIBED the bug the
    check was built to catch. A check that fires on its own example
    descriptions is its own wallpaper — strip pure-comment lines from
    consideration. Lines mixing code + trailing comment (`x = 1  # nope`)
    still get scanned because the executable part may carry the pattern.
    """
    stripped = line.lstrip()
    if path.endswith(".py"):
        return stripped.startswith("#")
    if path.endswith(".sh"):
        return stripped.startswith("#")
    return False


def find_violations() -> list[str]:
    """Return human-readable violation lines. Empty list if clean."""
    violations: list[str] = []
    added = _git_added_lines()
    for path, lines in sorted(added.items()):
        if not (path.endswith(".py") or path.endswith(".sh")):
            continue
        # Skip the check itself — its docstring contains the patterns
        # we look for as examples.
        if path.endswith("check_silent_swallow.py"):
            continue
        patterns = _patterns_for_file(path)
        for line_no, line, prev_line in lines:
            if _line_is_comment(line, path):
                continue
            # Fail-soft excuse can be on the SAME line (trailing comment)
            # or on the IMMEDIATELY PRIOR added line (more natural for
            # one-liners where the trailing comment would push past 100 cols).
            if _line_has_fail_soft_excuse(line) or _line_has_fail_soft_excuse(prev_line):
                continue
            if path.endswith(".sh") and _line_matches_known_good_sh_idiom(line):
                continue
            for pat, name in patterns:
                if pat.search(line):
                    violations.append(
                        f"{path}:{line_no}: silent-swallow pattern `{name}` "
                        f"added without `# fail-soft: <reason>` (>= 30 chars). "
                        f"Line: {line.strip()[:120]}"
                    )
                    break
    return violations


def main() -> int:
    violations = find_violations()
    if not violations:
        print("Silent-swallow check OK (no new fail-soft handlers without explicit reason)")
        return 0
    print("Silent-swallow handlers added without explicit `# fail-soft: <reason>`:")
    print()
    for v in violations:
        print(f"  {v}")
    print()
    print("Each violation must either:")
    print("  - Be rewritten to log the swallowed error (loud, not silent), OR")
    print("  - Add `# fail-soft: <reason>` on the same line with reason >= 30 chars")
    print("    explaining why silent-swallow is genuinely correct here.")
    print()
    print("Pattern class: fail-soft handlers swallowing real bugs. Two known")
    print("instances caught today (conftest, my hooks). This check stops the")
    print("class from growing in PRs while existing instances get cleaned up")
    print("case-by-case. Per the council walk 2026-06-23.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
