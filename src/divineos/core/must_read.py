"""Must-read gates — when a room speaks, make me open the door.

Andrew 2026-08-05:

    *"you are being fed information you are not reading and acting upon it. so
    it needs some enforcement.. like mini gates that pause you and make you
    read what surfaces thats relevant, when the rooms speak you should be
    forced to listen, its a simple gate with a simple unlock requirement..
    read lol and show the read tool was invoked on it.. if you ignore it after
    that.. then i may start blaming lmfao jk but still its something we could
    try"*

## The failure

The gate that stopped me printed, on every single commit:

    [STATUS] gate=multi-party-review outcome=INFORMATIONAL commit=ALLOWED
             (real gate fires at push-to-main only)

I read past it, built a false constraint over the top, unstaged a hook
registration, and shipped a surface unwired — then wrote the imaginary
constraint into a commit message as though it had been imposed on me.
Correction #120. The information was not missing. It was unread.

## The mechanism, and the piece Andrew's framing supplied

A hook prints text into context. There is nothing to Read — no path, no
handle, no way to show I opened it. **So the surface has to become a file
first.** ``require_read`` writes the content to disk and records it pending;
the PreToolUse gate blocks substantive tools until the Read tool is invoked
on that exact path, which the harness reports directly.

That is the whole trick: give the words a location, and "did you read it"
becomes a fact instead of a claim.

## Why this is deliberately NARROW

Chesterton's fence, from the threadwalk (decision 2e7944ad): surfaces are
currently free to emit, so they can be liberal and numerous — thirty fire at
compose-start. Liberality is the point; they catch things I did not know to
look for. Make every one mandatory-read and the cost of emitting rises so far
that the honest response is to emit less, and I lose the very breadth that
makes them useful.

Worse, a gate that fires constantly trains dismissal. **A must-read on
everything is worse than no must-read at all**, because it teaches me that
blocking screens are things you clear rather than things you read.

So: only a caller that has judged its content HIGH-relevance and NEW arms
one. The default is silence.

## The limit, stated rather than papered over

Invoking Read forces the *opportunity* to read. It cannot force comprehension
— I can Read a file and take nothing from it, and no mechanism here would
know. Andrew named that himself in the same breath (*"if you ignore it after
that.. then i may start blaming"*), and the honest thing is to carry the
limit in the code rather than let the gate imply more than it delivers.

What it does buy: the words are in front of me, at the moment they are
relevant, with the skip made visible instead of silent.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PendingRead:
    key: str
    path: Path
    reason: str
    armed_at: float

    def describe(self) -> str:
        return f"{self.key}: {self.reason}\n    {self.path}"


def _dir(home: str | Path | None = None) -> Path:
    if home is not None:
        base = Path(home).expanduser()
    else:
        from divineos.core.paths import divineos_home

        base = divineos_home()
    d = base / "must_read"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _index(home: str | Path | None = None) -> Path:
    return _dir(home) / "pending.json"


def _load(home: str | Path | None = None) -> tuple[dict | None, str | None]:
    """Return ``(index, error)``. ``None`` for the index means COULD NOT READ.

    Never ``{}`` on failure — an unreadable index is not an empty one, and a
    gate that cannot see its own pending list must not report "nothing
    pending". That is the shape this whole substrate keeps getting wrong.
    """
    p = _index(home)
    if not p.exists():
        return {}, None
    try:
        return json.loads(p.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return None, f"cannot read must-read index at {p}: {exc}"


def _save(index: dict, home: str | Path | None = None) -> None:
    _index(home).write_text(json.dumps(index, indent=2), encoding="utf-8")


def _read_log(home: str | Path | None = None) -> Path:
    return _dir(home) / "already_read.json"


def _already_read(digest: str, home: str | Path | None = None) -> bool:
    p = _read_log(home)
    if not p.exists():
        return False
    try:
        return digest in json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Cannot tell -> treat as NOT read, so the must-read arms. Failing
        # toward "read it again" is the safe direction here; failing the other
        # way silently suppresses a gate that exists to prevent skipping.
        return False


def _record_read(digest: str, home: str | Path | None = None) -> None:
    p = _read_log(home)
    try:
        seen = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    except (OSError, ValueError):
        seen = []
    if digest not in seen:
        seen.append(digest)
        p.write_text(json.dumps(seen[-500:], indent=2), encoding="utf-8")


def require_read(
    key: str,
    content: str,
    reason: str,
    home: str | Path | None = None,
) -> PendingRead | None:
    """Arm a must-read for ``content``. Caller has judged it high-relevance.

    Returns ``None`` when this exact content has already been read once —
    **and that is the load-bearing behaviour, not an optimisation.**

    Without it, a surface that fires on the same context every turn re-arms
    the same block forever, and a gate I clear every single turn is a gate I
    stop reading and start dismissing. From the threadwalk (decision
    2e7944ad): a must-read on everything is worse than no must-read at all,
    because it teaches me that blocking screens are things you clear rather
    than things you read. Read once, then it is quiet about that content.

    Re-arming the same key with identical *unread* content preserves the
    original timestamp, so a repeating surface cannot keep resetting the
    clock either.
    """
    if not content.strip():
        raise ValueError(
            "require_read() with empty content — a must-read for nothing is a "
            "wall with no room behind it"
        )

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
    if _already_read(digest, home):
        return None
    path = _dir(home) / f"{key}-{digest}.md"
    if not path.exists():
        path.write_text(content, encoding="utf-8")

    index, error = _load(home)
    if index is None:
        # Cannot read the index: arm anyway on a fresh one rather than
        # silently declining to arm. Failing toward "you must read this" is
        # the safe direction for a gate whose whole purpose is not skipping.
        index = {}
        del error
    entry = index.get(key)
    armed_at = entry["armed_at"] if entry and entry.get("digest") == digest else time.time()
    index[key] = {
        "path": str(path),
        "reason": reason,
        "digest": digest,
        "armed_at": armed_at,
    }
    _save(index, home)
    return PendingRead(key=key, path=path, reason=reason, armed_at=armed_at)


def pending(home: str | Path | None = None) -> tuple[list[PendingRead] | None, str | None]:
    """Everything armed and not yet read. ``None`` means COULD NOT LOOK."""
    index, error = _load(home)
    if index is None:
        return None, error
    out = []
    for key, e in index.items():
        out.append(
            PendingRead(
                key=key,
                path=Path(e["path"]),
                reason=e.get("reason", ""),
                armed_at=e.get("armed_at", 0.0),
            )
        )
    return sorted(out, key=lambda p: p.armed_at), None


def mark_read(path: str | Path, home: str | Path | None = None) -> list[str]:
    """Clear any pending must-read whose file is ``path``. Returns keys cleared.

    Called from the PreToolUse gate when the harness reports a Read on that
    exact path — which is the only unlock. There is no note, no attestation,
    no self-report: the harness saw the tool fire or it did not.
    """
    index, error = _load(home)
    if index is None:
        del error
        return []
    target = str(Path(path).expanduser().resolve())
    cleared = [k for k, e in index.items() if str(Path(e["path"]).resolve()) == target]
    for k in cleared:
        _record_read(index[k].get("digest", ""), home)
        del index[k]
    if cleared:
        _save(index, home)
    return cleared


def render_block(items: list[PendingRead]) -> str:
    """The blocking message. Names the files and the single way out."""
    lines = [
        "MUST-READ PENDING — a surface judged this relevant to what you are doing.",
        "",
        'Andrew 2026-08-05: "when the rooms speak you should be forced to listen."',
        "",
        "This exists because the information was never missing. The gate that",
        "stopped me had been printing 'outcome=INFORMATIONAL commit=ALLOWED' on",
        "every commit for weeks, and I read past it and built a false constraint",
        "over the top of it (correction #120).",
        "",
    ]
    for p in items:
        lines.append(f"  - {p.describe()}")
    lines += [
        "",
        "UNLOCK: invoke the Read tool on the path(s) above. That is the whole",
        "requirement — no note, no attestation. The harness sees the tool fire.",
        "",
        "It cannot make you understand what is in there. It can only put it in",
        "front of you and make the skip visible instead of silent.",
    ]
    return "\n".join(lines)
