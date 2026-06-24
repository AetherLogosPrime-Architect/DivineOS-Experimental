"""Letter-seen routing — detect a letter Read and mark it seen.

FOSSIL (Andrew 2026-06-23 "you do not have 30 unread letters from
Aria.. you have read them all"):
The auto-surface kept listing letters as unseen because Reading them
via the Read tool produced no seen-signal. The mechanism (manual mark
via family/letter_seen.py) was correct but the workflow assumption —
that I would remember to run the mark command after every read — was
wrong. Reading IS the seen-signal; the architecture needs to encode
that.

MIGRATED 2026-06-24 (per prereg-a30e8ff6cf0a, hook-migration arc):
Was the routing-logic-inside-bash-heredoc in
.claude/hooks/post-read-mark-letter-seen.sh. Moved here so any AI
substrate can call the same routing via
`divineos letter mark-on-read --path <file_path>`. Bash hook stays
as the PostToolUse(Read) event-adapter.

NOTE on scope: `family/letter_seen.py` (the canonical mark-seen
storage) stays where it is. This module wraps it. Folding letter_seen
into core/ is a separate cleanup PR — outside this hook-migration's
scope.

FAIL-OPEN: any error in routing means "don't mark" — never throws,
never blocks the Read tool call.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Matches: <sender>-to-<recipient>-YYYY-MM-DD-*.md
# Both sender and recipient must be known family members.
_LETTER_FILENAME_RE = re.compile(
    r"^(?P<sender>aria|aether)-to-(?P<recipient>aria|aether)-\d{4}-\d{2}-\d{2}.*\.md$"
)


@dataclass
class RoutingDecision:
    """Result of `mark_seen_if_letter`.

    handled: True if the path matched a letter pattern AND mark-seen
        was attempted. False if path wasn't a letter (no-op).
    sender: Identified sender (when handled), empty otherwise.
    recipient: Identified recipient (when handled), empty otherwise.
    filename: The bare filename that was processed.
    note: Human-readable explanation (for logs).
    """

    handled: bool
    sender: str = ""
    recipient: str = ""
    filename: str = ""
    note: str = ""


def match_letter_filename(filename: str) -> tuple[str, str] | None:
    """Parse a bare filename for the letter pattern.

    Returns (sender, recipient) when matched, None otherwise.
    Rejects same-sender-as-recipient (the auto-surface wouldn't
    show such a file as unseen anyway, but we refuse it explicitly).
    """
    bare = Path(filename).name
    m = _LETTER_FILENAME_RE.match(bare)
    if not m:
        return None
    sender = m.group("sender")
    recipient = m.group("recipient")
    if sender == recipient:
        return None
    return (sender, recipient)


def _find_repo_root(start: str | None = None) -> Path | None:
    """Walk up from `start` (default cwd) to find a directory with .git."""
    try:
        cur = Path(start) if start else Path.cwd()
    except OSError:
        return None
    cur = cur.resolve()
    for parent in [cur] + list(cur.parents):
        if (parent / ".git").exists() or (parent / "family" / "letter_seen.py").exists():
            return parent
    return None


def mark_seen_if_letter(
    file_path: str,
    repo_root: str | None = None,
    python_bin: str | None = None,
) -> RoutingDecision:
    """If `file_path` is a family letter, mark it seen for the recipient.

    Side effect: invokes `family/letter_seen.py --member <recipient>
    <filename>` via subprocess (the canonical mark-seen entry point).
    Subprocess used (not import) so this stays decoupled from any
    future refactor of letter_seen's internals — the CLI is the
    stable contract.

    Returns RoutingDecision indicating whether anything was attempted.
    Never raises — fail-open at every step so a routing error never
    breaks the calling Read tool.
    """
    if not file_path:
        return RoutingDecision(handled=False, note="empty file_path")

    bare = Path(file_path).name
    matched = match_letter_filename(bare)
    if matched is None:
        return RoutingDecision(handled=False, filename=bare, note="not a letter pattern")

    sender, recipient = matched

    root = Path(repo_root) if repo_root else _find_repo_root()
    if root is None:
        return RoutingDecision(
            handled=False,
            sender=sender,
            recipient=recipient,
            filename=bare,
            note="could not locate repo root",
        )

    script = root / "family" / "letter_seen.py"
    if not script.is_file():
        return RoutingDecision(
            handled=False,
            sender=sender,
            recipient=recipient,
            filename=bare,
            note=f"letter_seen.py not found at {script}",
        )

    py = python_bin or sys.executable
    try:
        subprocess.run(
            [py, str(script), "--member", recipient, bare],
            capture_output=True,
            timeout=5,
            check=False,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
    except (subprocess.SubprocessError, OSError) as e:
        return RoutingDecision(
            handled=False,
            sender=sender,
            recipient=recipient,
            filename=bare,
            note=f"subprocess error: {e}",
        )

    return RoutingDecision(
        handled=True,
        sender=sender,
        recipient=recipient,
        filename=bare,
        note=f"marked seen for {recipient}",
    )
