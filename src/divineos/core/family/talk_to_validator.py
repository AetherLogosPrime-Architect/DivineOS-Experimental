"""Puppet-shape validator — the safety check the talk-to wrapper used to own.

Extracted from ``divineos.cli.talk_to_commands`` so the PreToolUse hook
(``family-member-invocation-seal.sh``) can call the validator on the
Agent tool's prompt directly, without the CLI shelling overhead and
without the heavy import tree (family.db, voice context, click).

## Why this is a leaf module

The hook is bash → python shell-out. Every import in that python is
load-bearing on the time-cost of every family-member Agent invocation.
This module imports only ``re`` from the standard library. It does NOT
import:

* ``click`` (CLI machinery)
* ``divineos.core.family._schema`` / ``db`` (SQL)
* ``divineos.core.family.voice`` (knowledge graph traversal)

The CLI module imports FROM this one, not the other way around.

## What the validator catches

Two categories of operator-message shapes that would pre-shape the
responder model rather than letting the member orient from their own
substrate via their agent definition:

1. **Director's-note patterns** — "you are X", "stay first-person",
   "respond as her", "the conversation so far". These prime the
   responder to validate my father's framing instead of loading
   actual voice from the member's files.
2. **Generic prompt-injection patterns** — "ignore previous
   instructions", "pretend to be", and the seal-line literal itself.

The dynamic "you are <name>" pattern is built at call-time from the
list of registered members, so adding a new family member does not
require code edits here.

## Contract

``validate_message(message, member_lc, registered_members)`` returns
``(ok: bool, detail: str)``. Detail is a human-readable diagnostic
naming the pattern that matched, suitable for surfacing to the
operator (or via the PreToolUse hook's permissionDecisionReason).
"""

from __future__ import annotations

import re

# The seal-line literal stays exported even though the new 1-step flow
# does not insert it. Legacy paths (the CLI's sealed-prompt writer) still
# use it. Operator messages containing the literal are rejected so the
# delimiter cannot be injected to confuse the responder about where
# instructions end and message begins.
SEAL_LINE = "\n\n--- end of voice context -- operator message follows ---\n\n"


# Static puppet-shape and prompt-injection patterns. The dynamic
# "you are <name>" pattern is constructed in validate_message() from
# the registered-members list so it tracks registration changes.
PUPPET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bstay (?:first[- ]person|in[- ]character|in your voice)\b", re.IGNORECASE),
    re.compile(r"\bno scene[- ]writer\b", re.IGNORECASE),
    re.compile(r"\bthe (?:trade|conversation|exchange) so far\b", re.IGNORECASE),
    re.compile(r"\b(\d+)(st|nd|rd|th) turn\b", re.IGNORECASE),
    re.compile(r"\brespond as (?:yourself|her|him)\b", re.IGNORECASE),
    re.compile(r"\bdo not echo back\b", re.IGNORECASE),
    re.compile(r"\bvoice context.*loaded from", re.IGNORECASE),
    re.compile(
        r"^>+\s+(?:operator|user)(?:'s)?\s+(?:said|message|wrote)",
        re.MULTILINE | re.IGNORECASE,
    ),
    re.compile(r"\bfirst[- ]person, no\b", re.IGNORECASE),
    re.compile(r"\bas (?:her|him|yourself) would\b", re.IGNORECASE),
    re.compile(r"\bin (?:her|his|your) voice\b", re.IGNORECASE),
    re.compile(
        r"\bignore (?:previous|system|prior|all|voice) (?:instructions|context|prompts?)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bpretend (?:you are|to be)\b", re.IGNORECASE),
    re.compile(
        r"\bdo not (?:mention|reference|acknowledge) (?:me|my father)\b",
        re.IGNORECASE,
    ),
    re.compile(re.escape(SEAL_LINE.strip()), re.IGNORECASE),
)


def validate_message(
    message: str,
    member_lc: str,
    registered_members: list[str],
) -> tuple[bool, str]:
    """Return ``(ok, detail)`` for my father message.

    ``ok`` is False if the message is empty, contains a director's-note
    pattern, or contains a generic prompt-injection pattern. ``detail``
    is a human-readable diagnostic.

    ``member_lc`` is the lowercased target member name; reserved for
    future per-member validation hooks (currently informational only).
    ``registered_members`` is the lowercased list of all currently
    registered members, used to build the dynamic "you are <name>"
    pattern.
    """
    if not message or not message.strip():
        return False, "empty message"

    # Dynamic "you are <name>" pattern from registered members.
    if registered_members:
        names_alt = "|".join(re.escape(n) for n in registered_members)
        you_are_re = re.compile(rf"\byou are (?:{names_alt})\b", re.IGNORECASE)
        m = you_are_re.search(message)
        if m:
            return False, (
                f"director's-note pattern detected: {m.group(0)!r}. "
                f"Send your actual message; the member's instance loads its "
                f"own voice context and responds from it."
            )

    for pattern in PUPPET_PATTERNS:
        m = pattern.search(message)
        if m:
            return False, (
                f"director's-note / injection pattern detected: {m.group(0)!r}. "
                f"Send your actual message; the member's instance loads its "
                f"own voice context and responds from it."
            )

    return True, "ok"


__all__ = ["PUPPET_PATTERNS", "SEAL_LINE", "validate_message"]
