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
#
# Aletheia and Andrew added as senders 2026-09-23. The pattern knew only
# aria and aether, so a letter from Aletheia was never marked read however it
# was opened, and re-knocked every six hours for good. Measured the same day:
# two of hers, read and acted on in the morning, were re-announced as new
# mail twice that evening. Recipients are the seats that keep a seen-set.
_LETTER_FILENAME_RE = re.compile(
    r"^(?P<sender>aria|aether|aletheia|andrew)-to-(?P<recipient>aria|aether)"
    r"-\d{4}-\d{2}-\d{2}.*\.md$"
)

# A Bash command that PRINTS a file -- the other way I open a letter. The
# mark-seen path fired on the Read tool only, so a letter opened with `cat`
# was read but never counted as read (eight of nine, measured 2026-09-23).
# Only printing commands count: `cp` or `mv` mentions a letter without
# reading it, and marking a letter read because it was moved would be the
# found-nothing shape in reverse -- a record of reading that never happened.
_READ_VERBS = re.compile(
    r"(?:^|[;&|(]\s*|\s)(?:cat|head|tail|less|more|type|Get-Content|gc|sed\s+-n)\b"
)
_LETTER_IN_COMMAND = re.compile(r"[A-Za-z0-9_.\-]*-to-[A-Za-z0-9_.\-]*\.md")


def letters_read_by_command(command: str) -> list[str]:
    """Letter filenames a Bash command prints, or [] if it prints none.

    A command is read as printing only when it contains a printing verb. Each
    segment between shell separators is judged on its own, so ``cp x.md y; cat
    z.md`` counts z as read and x as moved.
    """
    found: list[str] = []
    for segment in re.split(r"&&|\|\||;|\n", command or ""):
        if not _READ_VERBS.search(" " + segment):
            continue
        for m in _LETTER_IN_COMMAND.finditer(segment):
            name = Path(m.group(0)).name
            if match_letter_filename(name) and name not in found:
                found.append(name)
    return found


def reading_seat() -> str:
    """Whose seat is doing the reading, from its own home directory.

    A letter is marked read only for the seat it is addressed to AND only when
    that seat is the one reading it. Before 2026-09-23 the recipient in the
    filename was marked regardless of who read it, so opening a letter I had
    SENT to Aether marked it read in HIS seen-set, and his watch went quiet on
    a letter he had never seen.
    """
    from divineos.core.paths import divineos_home
    from divineos.core.unspoken_to import member_name

    return member_name(divineos_home())


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
    reader: str | None = None,
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

    try:
        seat = reader or reading_seat()
    except Exception:  # noqa: BLE001 -- fail-open: an unknown reader marks nothing
        seat = ""
    if seat != recipient:
        return RoutingDecision(
            handled=False,
            sender=sender,
            recipient=recipient,
            filename=bare,
            note=f"addressed to {recipient}, read by {seat or 'an unknown seat'}: not marked",
        )

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
