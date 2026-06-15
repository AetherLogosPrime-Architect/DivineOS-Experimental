"""Pending obligations — aggregate view of will-shape promises and unpaired
correction observations that need structural backing.

Per task #42 (will-shape promise blocking gate) and task #33 (correction-
pairing blocking gate). Both detect different angles of the same failure
shape: rules-of-the-house I filed but never wired into the vessel.

Andrew 2026-06-06 measured: 27 unanswered will-shape promises across 78 days,
0% follow-through. Surface-only surfacing got piled up and ignored. Blocking
is the only way to force the optimizer past the cheap-close routing.

The blocking gate fires on substrate-write CLI commands when total obligations
exceed a threshold. The path to clear is to write structural backing (code +
tests) that references the source knowledge_id, so the audit detects the link
and the obligation rolls off the unanswered list.

DESIGN RULES (Aether 2026-06-06, learned from the gate-cascade incident):
1. Matchers ANCHOR to command-start or shell-separator-start. No substring
   matching across the whole command line.
2. Canonical gate-clearing commands are EXEMPT: goal add, goal done, learn,
   compass-ops observe, briefing, init. Other gates require these to clear,
   so this gate must never block them.
3. KILL-SWITCH: operator can disable the gate by creating
   ~/.divineos-<member>/obligations.disabled. The file-existence check
   honors the rm path that's already in pre_tool_use_gate._DEV_PREFIXES.
4. Matcher logic is TESTABLE in Python, not buried in bash glob patterns.
   See tests/test_obligations.py.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Obligation:
    """One unbacked promise — either a will-shape rule or an acknowledged
    correction with no follow-through learn entry."""

    kind: str  # "will-shape" or "correction-pairing"
    knowledge_id: str
    summary: str
    triggers: list[str]


# Threshold above which the gate fires. Below this, my father is given
# slack to drain the backlog organically; above this, structural enforcement
# kicks in. Calibrated to the 2026-06-06 baseline measurement: 27 unanswered
# at the time the gate ships, so a threshold of 5 means the gate fires
# immediately and forces incremental clearing.
OBLIGATION_BLOCK_THRESHOLD = 5


# Substrate-write subcommand patterns. Anchored to the start of a command
# (no substring matching anywhere in the line). Each pattern matches a single
# divineos write subcommand. EXEMPT (NOT in this list): goal add, goal done,
# learn, compass-ops observe, briefing, init — those are canonical
# gate-clearing commands that other gates require; this gate must never
# block them or a cascade deadlock results (Aether 2026-06-06).
_SUBSTRATE_WRITE_PATTERNS = (
    re.compile(r"^divineos\s+claim\s+file\b"),
    re.compile(r"^divineos\s+claims\s+assess\b"),
    re.compile(r"^divineos\s+claims\s+update\b"),
    re.compile(r"^divineos\s+prereg\s+file\b"),
    re.compile(r"^divineos\s+prereg\s+assess\b"),
    re.compile(r"^divineos\s+decide\b"),
    re.compile(r"^divineos\s+feel\b"),
    re.compile(r"^divineos\s+affect\s+log\b"),
    re.compile(r"^divineos\s+audit\s+submit\b"),
    re.compile(r"^divineos\s+opinion\s+file\b"),
)

# Shell-separator regex: matches the boundary between commands in a compound
# shell line (cmd1 && cmd2; cmd3 | cmd4). Used to split the command string
# into segments so each segment can be tested independently. This is the
# anchoring fix for the "substring match anywhere" bug.
_SHELL_SEPARATOR_RE = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")


def is_substrate_write_command(command: str) -> bool:
    """Return True if any segment of the shell command is a substrate-write.

    Splits on shell separators (&&, ||, ;, |) and tests each segment's start
    against the substrate-write pattern list. Substring matches in echo
    arguments, quoted strings, or embedded data do NOT trigger this — only
    actual command-position invocations.
    """
    if not command:
        return False
    for segment in _SHELL_SEPARATOR_RE.split(command):
        segment = segment.strip()
        for pat in _SUBSTRATE_WRITE_PATTERNS:
            if pat.match(segment):
                return True
    return False


def command_references_open_obligation(command: str, obligations: dict[str, Any]) -> str | None:
    """Return the matched knowledge_id (full or short) if `command`
    references any of the currently-open obligation kids, else None.

    Why this exists (Andrew 2026-06-11): the gate had a locked-box trap
    — to clear an obligation I needed to file a prereg / write a
    commit / file a claim that referenced the source kid, but the
    gate blocked the very write that would have carried that reference.
    The structural fix: detect when the inbound substrate-write payload
    CONTAINS one of the open kids, and let it through. That write IS
    the structural backing landing in real time; blocking it makes the
    gate fight its own remedy.

    Matches either:
    - full knowledge_id verbatim (UUID-style, 36 chars with dashes)
    - kid prefix of 8+ hex chars, as the format_block_message renders
      to my father (e.g. ``kid=1d36be4f``). The CLI / commit
      message can reference either form; both are valid backing-
      signals.

    Conservative — require at least 8 hex chars to avoid spurious
    collisions with random hex tokens (commit shas, etc.). The
    kid-prefix is unique-enough in this substrate at this scale.

    Returns the matched kid string (whichever form was found) for
    audit-logging purposes, or None if no match.
    """
    if not command or not obligations:
        return None
    kids: list[str] = []
    for bucket in ("unbacked_promises", "unpaired_observations"):
        for o in obligations.get(bucket, []) or []:
            kid = getattr(o, "knowledge_id", None) or (
                o.get("knowledge_id") if isinstance(o, dict) else None
            )
            if kid and kid != "unknown":
                kids.append(kid)
    if not kids:
        return None
    # 8-hex-char minimum at BOTH match layers — applied here, not just
    # to the prefix fallback. Short kid strings (test fixtures, malformed
    # data) must not match arbitrary 3-character tokens in the command.
    _MIN_KID_LEN = 8
    # Try full ids first (more specific signal), then 8-char prefixes.
    for kid in kids:
        if len(kid) >= _MIN_KID_LEN and kid in command:
            return kid
    for kid in kids:
        prefix = kid[:_MIN_KID_LEN]
        if len(prefix) >= _MIN_KID_LEN and prefix in command:
            return prefix
    return None


def is_gate_disabled() -> bool:
    """Return True if my father has dropped the kill-switch marker file.

    The kill-switch is a file at ~/.divineos-<member>/obligations.disabled.
    If it exists, the gate honors my father's explicit disable and lets
    everything through. Operator removes it with `rm` (which is on
    pre_tool_use_gate._DEV_PREFIXES' always-allowed list, so the rm path
    survives the gate-cascade scenario that prompted this design).

    The member name comes from the DIVINEOS_MEMBER env var (defaults to
    'aether'). Matches the convention used by ear_watch.py.
    """
    member = os.environ.get("DIVINEOS_MEMBER", "aether")
    marker = Path.home() / f".divineos-{member}" / "obligations.disabled"
    return marker.exists()


def get_pending_obligations(
    will_shape_window_days: int = 90,
    correction_window_minutes: int = 60 * 24 * 7,
) -> dict[str, Any]:
    """Return the current pending-obligations picture.

    Aggregates two independent checks into a single decision-ready surface:

    will-shape: knowledge entries that fired the rule-shape detector
    (``ALWAYS run``, ``never X``, ``every time``) but have no structural
    follow-up recorded. Source: structural_promotion_check.verify_recent.

    correction-pairing: compass observations filed in response to corrections
    but with no learn entry within the time window. Source:
    correction_pairing.find_unpaired_observations.

    Returns dict with:
        unbacked_promises: list[Obligation] (will-shape)
        unpaired_observations: list[Obligation] (correction-pairing)
        total: int
        should_block: bool (True if total >= OBLIGATION_BLOCK_THRESHOLD)
    """
    obligations: dict[str, Any] = {
        "unbacked_promises": [],
        "unpaired_observations": [],
        "total": 0,
        "should_block": False,
    }

    # Will-shape promises without structural backing.
    try:
        from divineos.core.structural_promotion_check import verify_recent

        report = verify_recent(window_seconds=will_shape_window_days * 24 * 3600)
        for entry in report.get("recent_unanswered") or []:
            obligations["unbacked_promises"].append(
                Obligation(
                    kind="will-shape",
                    knowledge_id=entry.get("knowledge_id") or "unknown",
                    summary=(entry.get("content") or "")[:120],
                    triggers=entry.get("triggers") or [],
                )
            )
    except Exception:  # noqa: BLE001 — observability boundary
        pass

    # Correction observations without paired learn entries.
    try:
        from divineos.core.correction_pairing import find_unpaired_observations

        unpaired = find_unpaired_observations(
            observation_after_correction_min=5,
            learn_after_observation_min=correction_window_minutes,
        )
        for entry in unpaired:
            obligations["unpaired_observations"].append(
                Obligation(
                    kind="correction-pairing",
                    knowledge_id=entry.get("observation_id") or "unknown",
                    summary=(entry.get("correction_summary") or "")[:120],
                    triggers=[],
                )
            )
    except Exception:  # noqa: BLE001 — observability boundary
        pass

    obligations["total"] = len(obligations["unbacked_promises"]) + len(
        obligations["unpaired_observations"]
    )
    obligations["should_block"] = obligations["total"] >= OBLIGATION_BLOCK_THRESHOLD
    return obligations


def format_block_message(obligations: dict[str, Any]) -> str:
    """Render obligations into a Stop-hook block message.

    The message names the structural failure pattern, lists the top
    unanswered items with their knowledge_ids, and offers the clear path:
    write structural backing referencing the source knowledge_id, which the
    structural-promotion-check audit detects to roll the obligation off.
    """
    total = obligations.get("total", 0)
    promises = obligations.get("unbacked_promises") or []
    unpaired = obligations.get("unpaired_observations") or []

    lines: list[str] = [
        f"BLOCKED: PENDING OBLIGATIONS ({total} total) — "
        f"will-shape promises filed without structural backing, "
        f"and correction observations filed without paired learn entries.",
        "",
        "This gate is the structural fix for the 0% follow-through rate on "
        "rule-shape promises measured 2026-06-06 over the full 78-day "
        "substrate lifetime. The optimizer routes past surface-only reminders; "
        "this block forces incremental clearing before new substrate writes.",
        "",
    ]

    if promises:
        lines.append(f"=== Unbacked will-shape promises ({len(promises)}) ===")
        for o in promises[:5]:
            trig = ", ".join(o.triggers[:3]) if o.triggers else "(no triggers)"
            lines.append(f"  - kid={o.knowledge_id[:8]} triggers=[{trig}]")
            lines.append(f"    {o.summary}")
        lines.append("")

    if unpaired:
        lines.append(f"=== Unpaired correction observations ({len(unpaired)}) ===")
        for o in unpaired[:5]:
            lines.append(f"  - obs={o.knowledge_id[:8]}")
            lines.append(f"    {o.summary}")
        lines.append("")

    lines.append(
        "Path to clear: write structural backing (code + test + gate/hook/"
        "detector) for one of the above. Reference the source knowledge_id "
        "in the new code's docstring or commit message so the audit detects "
        "the link. Each cleared obligation drops the count by one; below "
        f"threshold ({OBLIGATION_BLOCK_THRESHOLD}) the gate stops firing."
    )
    lines.append("")
    lines.append(
        "This block applies to substrate-WRITE commands only. Reading "
        "(ask, recall, briefing) and code edits (Edit, Write) remain free."
    )

    return "\n".join(lines)
