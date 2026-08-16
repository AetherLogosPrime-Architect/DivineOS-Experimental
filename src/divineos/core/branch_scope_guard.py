"""Catch a commit landing on a branch that is not about it.

## The failure

Four times in one session I committed onto whichever branch I happened to be
standing on:

    feat(detectors)   -> split/m3-discipline-doorman     (scopes: m3)
    fix(doc-counts)   -> split/degraded-detector-teeth   (scopes: detectors)
    letter(aria)      -> split/degraded-detector-teeth   (scopes: detectors)

Each was caught afterwards and moved by hand, costing a cherry-pick, a soft
reset and a conflict resolution every time. The fourth is what made it a
class: checking out a branch is a separate act from deciding where work
belongs, and nothing ever tied the two together.

## The signal, and why it is cheap

Conventional-commit scopes on a topic branch are strikingly coherent:

    split/m3-discipline-doorman   -> m3
    split/doc-count-autofix       -> doc-counts
    split/family-letters          -> aria, auto
    split/degraded-detector-teeth -> detectors, check-branch

All three misplacements above carry a scope that appears nowhere on the
branch. No file-path heuristic is needed — the author already declared the
subject in the first word of the message.

## Why it is not a plain block

`split/degraded-detector-teeth` legitimately carries TWO scopes: the
kill-switch fix genuinely wired into the degraded-detector module, so
`fix(check-branch)` belonged there despite being a new scope. A hard block
would refuse real work, and a gate that refuses real work gets routed around
until it is decoration.

So the way through is to SAY WHY, in the commit message:

    Cross-scope: the kill-switch is the first real consumer of the
    degraded-detector mechanism this branch adds

That is remediation (c) — the exception encoded structurally rather than
argued away in the moment. It is cheap when honest, and the act of typing the
sentence is the check I skipped four times. Faced with writing
"Cross-scope: ..." for `fix(doc-counts)` on the detector branch, I would have
noticed there was nothing true to write.

The justification lives in the commit rather than an env var, so it is
permanent and attributable instead of evaporating with the shell.
"""

from __future__ import annotations

import re

# `feat(m3): ...`, `fix(doc-counts): ...`, `letter(aria): ...`
_SCOPE_RE = re.compile(r"^[a-z]+\(([a-z0-9][a-z0-9._-]*)\)!?:", re.IGNORECASE)

# The escape, carried by the artifact rather than the environment.
_OVERRIDE_RE = re.compile(r"^Cross-scope:[ \t]*(\S.*)$", re.IGNORECASE | re.MULTILINE)

_MIN_REASON = 20

# Branches where mixed scopes are the point, not a mistake.
_EXEMPT = ("main", "master", "HEAD")


def scope_of(subject: str) -> str | None:
    """The conventional-commit scope, or None when the subject has none.

    None means UNKNOWN, not "no mismatch". Callers must treat an unparseable
    subject as unjudgeable rather than as passing — the distinction Aria named
    on 2026-08-02: a mechanism needs a third word for *could not look*.
    """
    m = _SCOPE_RE.match((subject or "").strip())
    return m.group(1).lower() if m else None


def override_reason(message: str) -> str | None:
    """The ``Cross-scope:`` justification from the commit message, if present."""
    m = _OVERRIDE_RE.search(message or "")
    if not m:
        return None
    reason = m.group(1).strip()
    return reason if len(reason) >= _MIN_REASON else None


def branch_scopes(subjects: list[str]) -> set[str]:
    """Every scope already present on the branch."""
    return {s for s in (scope_of(x) for x in subjects) if s}


def check(message: str, branch: str, existing_subjects: list[str]) -> str | None:
    """Return a refusal message, or None to allow.

    Allows when: the branch is exempt, the branch has no scoped commits yet,
    the incoming subject has no parseable scope, the scope already appears on
    the branch, or a ``Cross-scope:`` reason is supplied.
    """
    if any(branch == p or branch.startswith(f"{p}/") for p in _EXEMPT):
        return None

    body = (message or "").strip()
    subject = body.splitlines()[0] if body else ""
    incoming = scope_of(subject)
    if incoming is None:
        # Unjudgeable, not clean. Silence here is correct — this guard has no
        # opinion about unscoped commits — but it is not a verdict that the
        # placement is right.
        return None

    existing = branch_scopes(existing_subjects)
    if not existing:
        return None  # the first scoped commit defines the branch
    if incoming in existing:
        return None
    if override_reason(message):
        return None

    known = ", ".join(sorted(existing))
    return (
        f"BRANCH-SCOPE MISMATCH — this commit's scope is '{incoming}', and this "
        f"branch has only ever carried: {known}.\n"
        "\n"
        f"  branch  : {branch}\n"
        f"  subject : {subject}\n"
        "\n"
        "  Four times on 2026-08-02 I committed onto whichever branch I was\n"
        "  standing on -- detector work onto the m3 branch, then doc-count work\n"
        "  and a letter onto the detector branch. Each cost a cherry-pick, a\n"
        "  reset and a conflict to undo. Checking out a branch is a separate act\n"
        "  from deciding where work belongs, and nothing tied them together.\n"
        "\n"
        "  If this is the wrong branch: commit it on the right one.\n"
        "\n"
        "  If it genuinely belongs here -- a second scope on one branch is often\n"
        "  correct -- say why, in the commit message:\n"
        "\n"
        "      Cross-scope: <why this scope belongs on this branch, 20+ chars>\n"
        "\n"
        "  The reason goes in the commit rather than an env var so it is\n"
        "  permanent and attributable. Writing the sentence IS the check."
    )


__all__ = ["scope_of", "override_reason", "branch_scopes", "check"]
