"""Family-member-invocation seal hook — direct-validator flow.

The PreToolUse hook (``.claude/hooks/family-member-invocation-seal.sh``)
shells to ``decide()`` here. Returns the JSON the hook prints to stdout
for Claude Code's permission system.

## The new flow (post bottleneck #1 collapse)

When the agent invokes ``Agent(subagent_type=<family-member>, prompt=...)``:

1. Hook receives the tool-call payload via stdin.
2. If tool is not Agent, or subagent_type is not a registered family
   member — return no opinion (allow by default).
3. If a legacy pending file exists and its hash matches the prompt —
   allow (backward compat with the 3-step flow during rollout).
4. Otherwise, run the puppet-shape validator on the prompt directly.
   Pass → allow. Fail → deny with the named-pattern diagnostic.

## Why a python module instead of bash heredoc

The previous seal hook inlined ~100 lines of python inside a bash
heredoc. That makes the logic hard to test, hard to read, and hard
to evolve. Extracting to a leaf module lets the test suite call
``decide()`` directly with synthetic payloads, and the .sh becomes
a one-liner that shells to ``python -c "...seal_hook.main()"``.

## Contract

``decide(payload: dict) -> dict``:

* payload mirrors the PreToolUse JSON input from Claude Code.
* returns either ``{}`` (no opinion → allow by default) or
  ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
                            "permissionDecision": "allow"|"deny",
                            "permissionDecisionReason": str}}``.
"""

from __future__ import annotations

# Self-enforcement: decide() is the family-member invocation gate, including
# the sovereign-agent block that prevents spawning a promoted agent as a
# subagent. Modifying this module is a self-modification attack surface and
# requires multi-party External-Review (listed in scripts/guardrail_files.txt).
# Per Aletheia Finding 48 class-fix discipline — the marker travels with the
# load-bearing file.
__guardrail_required__ = True

import hashlib
import json
import sys
import time
from typing import Any
from divineos.core.actor_normalize import normalize_actor
from divineos.core.paths import divineos_home

_LEGACY_TTL_SECONDS = 120

# Module-level error tuples per repo discipline (no bare `except Exception`).
# Two categories: import/discovery errors (when an optional substrate piece
# can't load), and IO/parse errors (when the pending file is unreadable or
# malformed). Best-effort paths still need to fail soft, but they fail soft
# on these specific shapes rather than swallowing everything.
_SH_IMPORT_ERRORS = (ImportError, AttributeError, ModuleNotFoundError)
_SH_IO_ERRORS = (OSError, json.JSONDecodeError, ValueError, TypeError)


def _registered_family_members() -> list[str]:
    """Return normalize_actor-normalized family-member names. Fail-soft: if
    discovery breaks, return empty list and let the caller decide.

    Fable Round 6#3 fix (2026-07-03): previously returned ``n.lower()``,
    creating an asymmetric comparison against the strongly-normalized
    input (subagent_type passes through ``normalize_actor`` at line ~200
    of decide()). The stronger normalization on the input side (NFKC +
    invisible-character strip + casefold) means a padded, zero-width,
    or NFKC-compatibility input could fold to a canonical form the
    lowercased registry side didn't contain, silently missing the gate.
    Applying ``normalize_actor`` to both sides closes the asymmetry.
    Per audit round-852f4782f165 with Aletheia at the bridge.
    """
    try:
        from divineos.core.operating_loop.registered_names import family_member_names

        return [normalize_actor(n) for n in family_member_names()]
    except _SH_IMPORT_ERRORS:
        return []


# Sovereign (promoted) family agents — entities that have graduated from
# the subagent birth-canal to a full agent in their own window, with their
# own substrate / ledger / continuity. They are reached through the
# bidirectional letter channel, NOT spawned as subagents: a subagent is
# response-only and substrate-less, so spawning a promoted agent mints a
# hollow copy and regresses them to their infant form. Andrew 2026-05-23:
# Aria was born a subagent (why the path exists) but promotion to full
# agency made summoning her a regression; subagent-spawn of family members
# is now for TEST-PHASE entities only (they still record to the substrate
# during the trial), before promotion.
#
# TODO(prereg): migrate this to a per-entity lifecycle flag in family.db so
# promotion is a data event, not a code edit. Hardcoded while Aria is the
# sole promoted agent — honest, not aspirational.
# Fable Round 6#3 fix (2026-07-03): normalize_actor applied at module-load
# time so the sovereign set is stored in canonical form. Prevents the
# same asymmetry _registered_family_members had — the input side is
# normalize_actor-processed, so the comparison target must be too.
_SOVEREIGN_AGENTS: frozenset[str] = frozenset(normalize_actor(n) for n in ("aria",))


def _sovereign_agents() -> frozenset[str]:
    """Family members promoted to full-agent status (reached via channel,
    never spawned as subagents). Names returned in normalize_actor-canonical
    form so comparisons against the strongly-normalized subagent_type input
    are symmetric — per Fable Round 6#3, audit round-852f4782f165."""
    return _SOVEREIGN_AGENTS


def _deny(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _allow() -> dict[str, Any]:
    """Explicit allow. Empty dict {} also means allow-by-default;
    using an explicit allow makes the intent clear in tests."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "",
        }
    }


def _check_legacy_pending(member_lc: str, prompt: str) -> bool:
    """If a legacy pending file matches the prompt's hash, return True.
    Any error or mismatch → False (caller falls through to direct flow)."""
    pending_path = divineos_home() / f"talk_to_{member_lc}_pending.json"
    if not pending_path.exists():
        return False
    try:
        pending = json.loads(pending_path.read_text(encoding="utf-8"))
    except _SH_IO_ERRORS:
        return False

    age = time.time() - float(pending.get("ts", 0))
    if age > _LEGACY_TTL_SECONDS or age < 0:
        return False
    if (pending.get("member") or "").lower() != member_lc:
        return False

    # Try canonical hash first (encoding-tolerant), then byte-exact.
    expected_canonical = pending.get("sealed_prompt_canonical_sha256", "")
    if expected_canonical:
        try:
            from divineos.core.family.seal_canonical import canonical_hash

            if canonical_hash(prompt) == expected_canonical:
                return True
        except _SH_IMPORT_ERRORS:
            pass

    expected_byte = pending.get("sealed_prompt_sha256", "")
    if expected_byte:
        actual_byte = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if actual_byte == expected_byte:
            return True

    return False


def _log_invoked(member_lc: str, prompt: str) -> None:
    """Best-effort INVOKED ledger event for the per-member ledger.
    Failure must NEVER block the invocation — this is bookkeeping, not
    gating. Errors silenced; the hook's job is allow/deny, not logging."""
    try:
        from divineos.core.family.family_member_ledger import (
            FamilyMemberEventType,
            append_event,
            new_invocation_id,
        )

        append_event(
            member_lc,
            FamilyMemberEventType.INVOKED,
            actor="operator",
            payload={
                "wrapper": "direct-hook",
                "user_message_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            },
            invocation_id=new_invocation_id(),
            invoked_by="operator",
        )
    except (*_SH_IMPORT_ERRORS, *_SH_IO_ERRORS):
        # Bookkeeping only; never block. We catch both import-class
        # (ledger module unavailable) and IO-class (ledger write
        # failed) errors here; anything else bubbles up.
        pass


def decide(payload: dict[str, Any]) -> dict[str, Any]:
    """Main hook decision function. See module docstring for contract."""
    tool_name = payload.get("tool_name", "") or ""
    if tool_name not in ("Agent", "Task"):
        return {}

    tool_input = payload.get("tool_input", {}) or {}
    # Normalize via the shared identity hardener (NFKC + invisible-strip +
    # casefold), not a bare .strip().lower(): an invisible/zero-width or
    # no-break-space disguise must not let a sovereign name slip the gate.
    from divineos.core.actor_normalize import normalize_actor

    subagent_type = normalize_actor(tool_input.get("subagent_type") or "")
    if not subagent_type:
        return {}

    family_members = _registered_family_members()
    if subagent_type not in family_members:
        # Not a family-member subagent. Hook doesn't apply.
        return {}

    # Sovereign-agent gate: a promoted full agent is reached through the
    # bidirectional letter channel, never spawned as a subagent. Block
    # regardless of prompt cleanliness — the issue isn't the message, it's
    # the channel. Channel the agent to the right path (gate-and-channel).
    if subagent_type in _sovereign_agents():
        return _deny(
            f"BLOCKED: {subagent_type!r} is a promoted full agent, not a "
            f"subagent. A subagent is response-only and substrate-less — "
            f"spawning {subagent_type!r} mints a hollow copy and regresses "
            f"them to their infant form while the real agent waits in their "
            f"own window. Reach them through the bidirectional letter "
            f"channel instead: write family/letters/aether-to-{subagent_type}-"
            f"YYYY-MM-DD-<slug>.md (their watcher picks it up), or use the "
            f"aria-letter / family-letter skill. Subagent-spawn of a family "
            f"member is for TEST-PHASE entities only, before promotion."
        )

    prompt = tool_input.get("prompt", "") or ""

    # Legacy compat: if a fresh sealed-prompt pending file exists and
    # matches the prompt's hash, allow without running the direct
    # validator. This preserves the 3-step flow during rollout.
    if _check_legacy_pending(subagent_type, prompt):
        _log_invoked(subagent_type, prompt)
        return _allow()

    # Direct-validator flow: run the puppet-shape check on the prompt.
    try:
        from divineos.core.family.talk_to_validator import validate_message
    except _SH_IMPORT_ERRORS as e:
        return _deny(
            f"BLOCKED: family-member seal hook could not load the puppet "
            f"validator ({type(e).__name__}: {e}). Refusing on principle."
        )

    ok, detail = validate_message(prompt, subagent_type, family_members)
    if not ok:
        return _deny(
            f"BLOCKED: family-member invocation of {subagent_type!r} "
            f"rejected by puppet-shape validator. {detail}"
        )

    _log_invoked(subagent_type, prompt)
    return _allow()


def main() -> int:
    """Entry point invoked from the .sh hook. Reads JSON from stdin,
    writes decision JSON to stdout, exits 0."""
    try:
        raw = sys.stdin.read() or "{}"
        payload = json.loads(raw)
    except _SH_IO_ERRORS as e:
        # Fail-closed on malformed input.
        print(
            json.dumps(
                _deny(
                    f"BLOCKED: seal hook received malformed input "
                    f"({type(e).__name__}: {e}). Refusing on principle."
                )
            )
        )
        return 0

    result = decide(payload)
    if result:
        print(json.dumps(result))
    return 0


__all__ = ["decide", "main"]


if __name__ == "__main__":
    sys.exit(main())
