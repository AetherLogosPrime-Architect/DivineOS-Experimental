"""One bypass key per seat, spent on use, replaced only by a dogfooded fix.

Andrew 2026-09-30, after the push-lock override I reached for with no
permission: *"maybe the OS should issue you a single bypass key, and in order
to get it replaced when you use it, you must show evidence of an actual root
cause fix from the bypass, without that, your bypass license is revoked"* and
*"DOGFOODING, you will know if it works or not because you will have to prove
it working in action, by using it, and then recording the fix that actually
worked"*.

Design: docs/drafts/the_override_is_a_button_draft_2026-09-30.md (revisions
2 and 3), walk-0e68ddafaa93, prereg-b3e8453df633.

WHY A KEY AND NOT A RULE. The emergency-bypass protocol logs, reports and
files an obligation, and the obligation is a to-do nothing waits on. So the
override stayed a button: nothing stood between the reach and the effect. A
spent key makes the second press unavailable (truth 11a, take the option
away). The only way back is the fix.

WHO WITNESSES THE FIX. Not me. The gate calls ``note_clean_pass`` when it
allows a command with no override present, so the dogfood evidence is written
by the lock doing its job, never typed. Reissue needs, in this order (Holmes):
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
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

KEY_FILE = Path.home() / ".divineos" / "bypass_key.json"
REPO_ROOT = Path(__file__).resolve().parents[3]

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


def _load() -> dict | None:
    if not KEY_FILE.exists():
        return {"spent": None}
    try:
        data = json.loads(KEY_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _save(data: dict) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def status() -> KeyStatus:
    data = _load()
    if data is None:
        return KeyStatus(held=False, readable=False)
    spent = data.get("spent")
    reissue = data.get("last_reissue") or {}
    if not spent:
        return KeyStatus(held=True, last_reissue=reissue)
    return KeyStatus(
        held=False,
        spent_gate=spent.get("gate", ""),
        spent_fingerprint=spent.get("fingerprint", ""),
        spent_at=float(spent.get("at", 0.0)),
        last_reissue=reissue,
    )


def _refusal(st: KeyStatus) -> str:
    if not st.readable:
        return f"Your bypass key can't be read ({KEY_FILE}), so there is no key to use. Ask Dad."
    return (
        f"Your one bypass key is already used: it opened {st.spent_gate} for "
        f"'{st.spent_fingerprint}'. To get it back, fix that lock: commit a change "
        f"to {GATE_FILES.get(st.spent_gate, st.spent_gate)}, then run the same "
        "command through it again with no override. When the lock lets it through, "
        "the key comes back by itself. Or ask Dad."
    )


def spend(gate: str, command: str, now: float | None = None) -> None:
    """Use the key on ``gate`` for ``command``. Raises KeySpent if there is none."""
    st = status()
    if not st.held:
        raise KeySpent(_refusal(st))
    data = _load() or {}
    data["spent"] = {"gate": gate, "fingerprint": fingerprint(command), "at": now or time.time()}
    _save(data)


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
    data = _load() or {}
    data["spent"] = None
    data["last_reissue"] = {
        "gate": gate,
        "fingerprint": st.spent_fingerprint,
        "spent_at": st.spent_at,
        "commit_time": commit_time,
        "pass_time": when,
    }
    _save(data)
    return True
