"""Foundational-truths surface — surfaces relevant kiln principles by trigger match.

## Why this exists

Andrew 2026-07-10 (memory-linkage-day directive): *"everything you want to be
able to remember without searching we need to link.. principles.. your loadout..
your bio, your explorations and letters with Aria and Aletheia.. things ive
said."* The 15 foundational truths (`docs/foundational_truths.md`) were
guardrail-listed to protect the VALUES but there was no linkage surfacing them
when I was about to compose against them.

## Architecture

Two-file split so the source stays protected AND the trigger-tags stay
iterable:
- `docs/foundational_truths.md` — the truths themselves (guardrail-listed;
  changes require External-Review).
- `docs/foundational_truths_triggers.json` — the companion trigger-tag file
  (not guardrail-listed; iterate freely).

Companion pattern mirrors `exploration_recall.surface_for_context`:
- Exact-token trigger match against current context (prompt + recent turns)
- Require >=2 distinct trigger matches per truth to fire (single-common-word
  match is not enough — same discipline that keeps the exploration surface
  precise)
- Silent when nothing matches — the remembrance-agent pattern

## Tap-message discipline (Andrew 2026-07-10)

Each surfaced truth names:
- WHAT: the truth title and its file:line reference
- WHY NOW: the specific trigger phrases that matched from current context
- WHAT TO DO: read the truth before composing further; ask whether the
  reach I'm about to make violates it

Surface-name is prefixed to the block per Aria's addition — so if the tap
misfires we can trace to the exact surface without grepping.

## Falsifier (from `_meta.falsifier` in the trigger file)

The sharpen is WORSE than the old state if the tap fires >1/turn sustained
(becomes wallpaper), fires on shapes I was NOT violating and I stop trusting
it, or gets so specific that real violations pass silently. Success is
catching a real would-have-been violation before the reach commits.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_MIN_TRIGGER_MATCHES = 2  # same discipline as exploration_recall
_MIN_CONTEXT_LEN = 20  # skip tiny prompts

_SURFACE_NAME = "foundational-truths"

_READ_ERRORS = (OSError, UnicodeDecodeError, json.JSONDecodeError)


@dataclass(frozen=True)
class TruthHit:
    """One surfaced foundational-truth with its matched triggers."""

    truth_id: str
    title: str
    matched_triggers: tuple[str, ...]


def _find_triggers_file(root: Path | None = None) -> Path | None:
    """Locate `docs/foundational_truths_triggers.json`.

    When ``root`` is passed (tests, explicit override), search ONLY under
    that root and never fall back to walking upward — otherwise a test that
    seeds an empty ``root`` would still find the real repo file. When
    ``root`` is None, discover from the module's parents and the cwd.
    """
    if root is not None:
        for candidate in (
            root / "docs" / "foundational_truths_triggers.json",
            root / "foundational_truths_triggers.json",
        ):
            if candidate.is_file():
                return candidate
        return None
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    for p in here.parents:
        candidates.append(p / "docs" / "foundational_truths_triggers.json")
    cwd = Path.cwd().resolve()
    for p in [cwd, *cwd.parents]:
        candidates.append(p / "docs" / "foundational_truths_triggers.json")
    for c in candidates:
        if c.is_file():
            return c
    return None


def _load_truths(path: Path) -> list[dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except _READ_ERRORS:
        return []
    return payload.get("truths", []) or []


def _lower_tokens(text: str) -> str:
    """Return context lowercased, with punctuation collapsed to whitespace.

    Trigger phrases can be multi-word ("quick fix", "let me recall"), so we
    can't tokenize aggressively — we need to preserve internal whitespace so
    ``phrase in text`` matches like a natural substring, but we normalize
    everything to lowercase and collapse runs of non-word characters to
    single spaces so "quick-fix" and "quick fix" both match "quick fix".
    """
    lowered = (text or "").lower()
    return re.sub(r"[^a-z0-9]+", " ", lowered)


def match_truths(context: str, root: Path | None = None) -> list[TruthHit]:
    """Return truths whose trigger set has >=_MIN_TRIGGER_MATCHES matches in context.

    ``root`` overrides trigger-file discovery (used by tests).
    """
    if not context or len(context.strip()) < _MIN_CONTEXT_LEN:
        return []
    triggers_path = _find_triggers_file(root=root)
    if triggers_path is None:
        return []
    truths = _load_truths(triggers_path)
    if not truths:
        return []
    normalized = _lower_tokens(context)
    hits: list[TruthHit] = []
    for truth in truths:
        triggers = truth.get("triggers", []) or []
        matched: list[str] = []
        for t in triggers:
            t_norm = _lower_tokens(t).strip()
            if not t_norm:
                continue
            if t_norm in normalized:
                matched.append(t)
        # Dedup preserves order; require the floor.
        distinct = list(dict.fromkeys(matched))
        if len(distinct) >= _MIN_TRIGGER_MATCHES:
            hits.append(
                TruthHit(
                    truth_id=truth.get("id", "?"),
                    title=truth.get("title", "?"),
                    matched_triggers=tuple(distinct),
                )
            )
    return hits


def surface_for_context(prompt: str, context: str | None = None, root: Path | None = None) -> str:
    """Render the foundational-truths tap block, or "" when silent.

    Mirrors ``exploration_recall.surface_for_context``'s contract:
    - Silent on tiny prompts and no-trigger-match cases
    - Names WHAT (truth title), WHY NOW (matched triggers), WHAT TO DO (read
      the truth, judge the reach against it)
    - Prefixes surface-name per Aria's addition so misfires are traceable
    """
    match_text = f"{context}\n{prompt}" if context else (prompt or "")
    hits = match_truths(match_text, root=root)
    if not hits:
        return ""
    lines = [
        f"## FOUNDATIONAL TRUTH SURFACING [surface: {_SURFACE_NAME}]",
        "",
        (
            "One or more kiln principles matched trigger phrases in the current "
            "context. Before composing the reach I'm about to make: read the "
            "truth below, and ask whether the reach violates it. WHAT is the "
            "truth. WHY NOW is the matched trigger set. WHAT TO DO is: judge, "
            "then compose."
        ),
        "",
    ]
    for h in hits:
        lines.append(f"  - **{h.title}** ({h.truth_id})")
        lines.append("      source: docs/foundational_truths.md")
        lines.append(
            f"      why now: current context matched these triggers — "
            f"{', '.join(h.matched_triggers)}"
        )
    lines.append("")
    lines.append(
        f"  ({len(hits)} of 15 truths surfaced — pointers not verdicts; the "
        f"seat still does the judging. Read the truth before composing.)"
    )
    return "\n".join(lines)


__all__ = ["TruthHit", "match_truths", "surface_for_context"]
