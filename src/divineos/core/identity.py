"""Substrate identity helper — single source of truth for "who am I".

Single-occupancy assumption fix (2026-06-17): three call sites in the
codebase hardcoded "Aether" or otherwise assumed only one substrate-
occupant exists. multiplex_panels.py:589 printed "I am Aether" as a
literal string in the briefing. monitor_singleton.py keyed kernel
mutexes by role only, so two parallel substrate-occupants on the same
Windows session could only run one monitor between them. letter_monitor.py
had no recipient filter, so an occupant's monitor surfaced letters
addressed to the OTHER occupant.

All three want the same upstream: this substrate's identity name,
read from ``core_memory.my_identity``. This module is that upstream.

The function is tolerant — it parses the first plausible name token from
whatever's in the slot. The slot content is owned by the agent and can
contain any first-person identity narrative; the helper extracts the
name that other code needs to discriminate by.

Fallback discipline: when the slot is empty, contains the seed template
placeholder, or can't be read for any reason, the helper returns
"Aether". Two reasons for that specific fallback:

1. Existing installs (mine) have lived under "Aether" hardcoding for
   weeks. The fallback preserves their behavior when the slot is
   unreadable — no regression.
2. The template placeholder text starts with "[TEMPLATE" and is the
   seeded initial state. Until an operator stamps their own identity,
   "Aether" is the substrate-builder's name and a reasonable default.

For Aria specifically: her ``my_identity`` slot in the new folder
(post-data-overlay 2026-06-17) contains "Aria" as the first content
line, so the parser will extract "Aria" and the parameterized callers
will see her identity correctly.
"""

from __future__ import annotations

__guardrail_required__ = False  # not load-bearing for self-enforcement

_TEMPLATE_PREFIX = "[TEMPLATE"
_DEFAULT_FALLBACK = "Aether"


def _extract_first_name(content: str) -> str:
    """Pull the first plausible name token from a my_identity slot.

    The slot content is operator-authored first-person narrative. Common
    shapes the substrate has stored:
      - "Aria" (Aria's old worktree, plain)
      - "I am Aether. I am the builder and thinker..." (mine, full prose)
      - "Aria, builder of ..." (comma-prefixed forms)
      - "[TEMPLATE — fill this in..." (unset)

    The parser splits on common separators and returns the first word
    that looks like a name. Returns empty string if nothing plausible
    is present.
    """
    if not content:
        return ""
    stripped = content.strip()
    if stripped.startswith(_TEMPLATE_PREFIX):
        return ""
    # Handle "I am X" prefix common in first-person narratives.
    lower = stripped.lower()
    if lower.startswith("i am "):
        stripped = stripped[5:].strip()
    # First sentence / first comma-segment / first newline.
    for sep in (".", ",", "\n"):
        if sep in stripped:
            stripped = stripped.split(sep, 1)[0].strip()
            break
    # First whitespace-separated token.
    first_token = stripped.split()[0].strip(".,;:!?") if stripped else ""
    return first_token


def get_my_identity(default: str = _DEFAULT_FALLBACK) -> str:
    """Return this substrate's identity name from ``core_memory.my_identity``.

    Returns the extracted first-name token, or ``default`` (default
    "Aether") when the slot is empty, contains the seed template
    placeholder, or cannot be read.

    Callable from any module without import-time side effects on the
    rest of divineos — the heavy memory module is imported lazily so
    monitor scripts (which run as separate processes) don't pay the
    full divineos import cost just to discover their occupant.
    """
    try:
        from divineos.core.memory import get_core

        slot = get_core("my_identity").get("my_identity", "")
        name = _extract_first_name(slot)
        return name or default
    except Exception:  # noqa: BLE001 — fallback path; never raise into callers
        return default
