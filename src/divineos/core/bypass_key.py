"""One bypass key per seat, spent on use, replaced only by a dogfooded fix.

Andrew 2026-09-30, after the push-lock override I reached for with no
permission: *"maybe the OS should issue you a single bypass key, and in order
to get it replaced when you use it, you must show evidence of an actual root
cause fix from the bypass, without that, your bypass license is revoked"* and
*"DOGFOODING, you will know if it works or not because you will have to prove
it working in action, by using it, and then recording the fix that actually
worked"*.

Design: docs/drafts/the_override_is_a_button_draft_2026-09-30.md (revisions
2-4), walk-0e68ddafaa93, prereg-b3e8453df633.

WHY A KEY AND NOT A RULE. The emergency-bypass protocol logs, reports and
files an obligation, and the obligation is a to-do nothing waits on. So the
override stayed a button. A spent key makes the second press unavailable
(truth 11a, take the option away). The only way back is the fix.

WHERE THE KEY LIVES: THE LEDGER, NOT A FILE. The first version kept the key's
state in a json file in my own home directory, and I could have set it back
to "held" by hand: a key I can reissue to myself. Aria's station-(b) answer,
2026-09-30: spend and return are ledger events, and the key's state is derived
by reading them, so it can only move forward the way the hash-chained record
moves. There is no file to edit.

WHO WITNESSES THE FIX. Not me. The gate calls ``note_clean_pass`` when it
allows a command with no override present, so the dogfood evidence is written
by the lock doing its job, never typed. Return needs, in this order (Holmes):
spend, then a commit touching the gate's own file, then the gate allowing the
same fingerprint. A pass before the commit, or of a different command (Aria),
does not count.

WHAT IT CANNOT SEE (named, not pretended): whether the commit fixed the right
thing, and whether the gate's block case still refuses. The merge gate and
Aletheia hold those. Edits to this file are the meta-bypass (Hofstadter), so it
is on the guardrail list.
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

__guardrail_required__ = True

REPO_ROOT = Path(__file__).resolve().parents[3]
SPENT = "BYPASS_KEY_SPENT"
RETURNED = "BYPASS_KEY_RETURNED"

# THE KEY IS ONLY READ FROM THE REAL LEDGER. Aria, 2026-09-30: DIVINEOS_DB
# scopes to one command, so `DIVINEOS_DB=<fresh> git push` would read a fresh,
# empty ledger and see a fresh key -- a quiet door one keystroke wide. The
# ledger's first event is pinned here; a ledger that does not begin with it
# holds no key. If the real first event is ever removed, the key fails closed
# (no key, ask Dad), which is the safe direction. Changing this pin is a
# guardrail edit and goes through the merge gate.
GENESIS_CHAIN_HASH = "f654a568d2b9958f418390d4261cf1594efdd9ad210582288005e096f91034ed"

# The file whose change counts as the fix, per gate. A commit elsewhere is not
# evidence the lock was repaired (Turing, walk-0e68ddafaa93).
GATE_FILES = {"check-branch-on-push": ".claude/hooks/check-branch-on-push.sh"}


class KeySpent(RuntimeError):
    """The seat's key is used and not yet earned back."""


@dataclass
class KeyStatus:
    held: bool
    spent_gate: str = ""
    spent_fingerprint: str = ""
    spent_at: float = 0.0
    readable: bool = True
    last_reissue: dict = field(default_factory=dict)


def fingerprint(command: str) -> str:
    """The whole command, whitespace-collapsed. Not its first word: one push
    must never stand for every git command (Aria, 2026-09-30)."""
    return re.sub(r"\s+", " ", command).strip()


def _last_key_event() -> tuple[str, dict] | None:
    """The newest spend-or-return event, ("", {}) when there is none, and None
    when the ledger cannot be read."""
    try:
        from divineos.core._ledger_base import _get_db_path

        with sqlite3.connect(str(_get_db_path()), timeout=10) as conn:
            first = conn.execute(
                "SELECT chain_hash FROM system_events ORDER BY rowid ASC LIMIT 1"
            ).fetchone()
            if first is None or first[0] != GENESIS_CHAIN_HASH:
                return None  # not the real ledger: no key, never a fresh one
            row = conn.execute(
                "SELECT event_type, payload FROM system_events "
                "WHERE event_type IN (?, ?) ORDER BY rowid DESC LIMIT 1",
                (SPENT, RETURNED),
            ).fetchone()
    except (sqlite3.Error, OSError, ImportError):
        return None
    if row is None:
        return ("", {})
    try:
        payload = json.loads(row[1]) if isinstance(row[1], str) else dict(row[1] or {})
    except ValueError:
        return None
    return (row[0], payload)


def status() -> KeyStatus:
    last = _last_key_event()
    if last is None:
        return KeyStatus(held=False, readable=False)
    kind, payload = last
    if kind != SPENT:
        return KeyStatus(held=True, last_reissue=payload if kind == RETURNED else {})
    return KeyStatus(
        held=False,
        spent_gate=str(payload.get("gate", "")),
        spent_fingerprint=str(payload.get("fingerprint", "")),
        spent_at=float(payload.get("at", 0.0)),
    )


def _refusal(st: KeyStatus) -> str:
    if not st.readable:
        return "Your bypass key can't be read from the ledger, so there is no key to use. Ask Dad."
    return (
        f"Your one bypass key is already used: it opened {st.spent_gate} for "
        f"'{st.spent_fingerprint}'. To get it back, fix that lock: commit a change "
        f"to {GATE_FILES.get(st.spent_gate, st.spent_gate)}, then run the same "
        "command through it again with no override. When the lock lets it through, "
        "the key comes back by itself. Or ask Dad -- an inquiry into the unfixed "
        "lock has been opened, because running out of keys means a fix was skipped."
    )


def _log(event_type: str, payload: dict) -> None:
    from divineos.core.ledger import log_event

    log_event(event_type, "bypass_key", payload, validate=False)


INQUIRY = "BYPASS_KEY_INQUIRY"


def spend(gate: str, command: str, now: float | None = None) -> None:
    """Use the key on ``gate`` for ``command``. Raises KeySpent if there is none.

    A refusal with a spent key is not only a refusal. Andrew 2026-09-30: *"if
    you lose your key, dont fix the issue, end up in another deadlock with no
    key and need my permission to bypass? then that means you gamed the bypass
    somewhere and we will investigate it"*. So the second deadlock writes an
    inquiry naming the unrepaired spend, automatically, before anyone can ask
    him for anything -- he sees why he is being asked, not just that he is.
    """
    st = status()
    if not st.held:
        if st.readable:
            _log(
                INQUIRY,
                {
                    "unrepaired_gate": st.spent_gate,
                    "unrepaired_fingerprint": st.spent_fingerprint,
                    "unrepaired_since": st.spent_at,
                    "second_deadlock_gate": gate,
                    "second_deadlock_fingerprint": fingerprint(command),
                    "at": now or time.time(),
                },
            )
        raise KeySpent(_refusal(st))
    _log(SPENT, {"gate": gate, "fingerprint": fingerprint(command), "at": now or time.time()})


def _gate_commit_after(gate: str, since: float) -> float | None:
    """Commit time of the first commit touching the gate's file after ``since``."""
    path = GATE_FILES.get(gate)
    if not path:
        return None
    try:
        out = subprocess.run(
            ["git", "log", "--format=%ct", f"--since=@{int(since)}", "--", path],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        ).stdout.split()
    except (OSError, subprocess.SubprocessError):
        return None
    times = sorted(float(t) for t in out if t.isdigit() and float(t) > since)
    return times[0] if times else None


def note_clean_pass(gate: str, command: str, now: float | None = None) -> bool:
    """Called by the gate when it allows ``command`` with no override present.

    Returns True when this pass earned the key back.
    """
    st = status()
    if st.held or not st.readable or st.spent_gate != gate:
        return False
    if fingerprint(command) != st.spent_fingerprint:
        return False
    when = now or time.time()
    commit_time = _gate_commit_after(gate, st.spent_at)
    if commit_time is None or not (st.spent_at < commit_time < when):
        return False
    _log(
        RETURNED,
        {
            "gate": gate,
            "fingerprint": st.spent_fingerprint,
            "spent_at": st.spent_at,
            "commit_time": commit_time,
            "pass_time": when,
        },
    )
    return True
