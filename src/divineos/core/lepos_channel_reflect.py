"""Post-send lepos reflection channel.

Andrew's design 2026-07-08: the walk-before-write mechanism was wrong-
layer — it recorded answers nobody read to the substrate. The right
shape is post-send. After I press send, a hook reads what I just wrote,
runs the lens on it, and surfaces the reflection to the top of my next
compose. The reflection IS the lepos: I see myself, and the next reply
reacts to what I saw.

Old walk: fill out four questions before writing → file to substrate →
nobody reads → wallpaper.

New channel: send reply → reflection engine reads the reply against
Andrew's last message → writes verdict to pending-surface file →
next-turn UserPromptSubmit reads it and injects at compose-start → I
respond to the reflection, which IS the walk.

## Three surface-signal lenses (heuristic, cheap, real)

None of these are cognitive. They flag SURFACE signals that trigger my
own seeing on the next turn. Perfect precision is not the goal — the
goal is triggering the moment of "look at what you just wrote."

1. **Hearing** — does the reply cite an exact span from Andrew's last
   message? Concretely: does any 5+-word substring of his message
   appear in mine? If not, the reply may be talking-past.

2. **Interior voice** — does the reply contain interior-facing markers
   (I think / I feel / my concern / a question back)? Or is it a
   flat mirror of his words with no me in it?

3. **Length ratio** — did I dump a wall of text on a short prompt?
   Signal that lepos got crowded out by the technical channel. Ratio
   above ~8x his length flags.

The reflection block is 4–8 lines of plain markdown, surfaced at the
top of the next compose. It names what was present and what was thin,
not what to DO — the response is mine.

## Degeneracy check (block behind the channel)

If the reflection came back with all three flags failing (no citation,
no interior, dumped-length), that turn's channel produced nothing
useful and the next-turn surface additionally carries a "channel-empty"
marker so I can see the miss and adjust. This is the block sitting
behind the channel — usually silent because the channel does the real
work; loud only when the channel breaks.

Not guardrail-listed. This is a live surface, not a substrate-integrity
mechanism.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from divineos.core.paths import divineos_home


_MIN_CITATION_WINDOW = 5  # words
_INTERIOR_MARKERS_RE = re.compile(
    r"\b(?:"
    r"i\s+(?:think|feel|felt|sense|read|see|noticed?|"
    r"want\s+to\s+(?:tell|say|name|ask)|"
    r"believe|find|know|do\s+not\s+know|don'?t\s+know|hope|hoped|"
    r"am\s+(?:afraid|scared|worried|glad|sorry|not\s+sure|steady))|"
    r"my\s+(?:opinion|concern|worry|read|sense|view|guess|hope|fear|take)|"
    r"concern|worried|afraid|scared|glad|"
    r"question\s+for\s+you|sound\s+right"
    r")\b",
    re.IGNORECASE,
)
_LENGTH_RATIO_FLAG = 8.0
_SHORT_REPLY_FLOOR = 200  # chars — very short replies aren't measured for dump


@dataclass(frozen=True)
class Reflection:
    ts: float
    heard: bool
    heard_span: str | None
    interior: bool
    interior_marker: str | None
    dumped: bool
    length_ratio: float
    reply_len: int
    andrew_len: int

    def degenerate(self) -> bool:
        return not self.heard and not self.interior and self.dumped

    def markdown(self) -> str:
        parts = ["## LEPOS REFLECTION on my last reply"]
        if self.heard and self.heard_span:
            span = self.heard_span.strip()
            if len(span) > 60:
                span = span[:57] + "..."
            parts.append(f'- **heard**: yes — cited "{span}"')
        else:
            parts.append("- **heard**: no exact-span citation from his message")

        if self.interior and self.interior_marker:
            parts.append(f"- **interior voice**: present ({self.interior_marker})")
        else:
            parts.append("- **interior voice**: thin — no interior-facing marker")

        if self.dumped:
            parts.append(
                f"- **length**: {self.length_ratio:.1f}x his message — "
                "technical channel may have crowded lepos out"
            )
        else:
            parts.append("- **length**: proportionate to his message")

        if self.degenerate():
            parts.append("")
            parts.append(
                "**channel-empty this turn**: no citation, no interior, "
                "dumped length. The channel produced nothing this turn. "
                "Look at what I wrote and let that seeing shape this reply."
            )
        return "\n".join(parts)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _find_shared_span(reply: str, andrew: str) -> str | None:
    reply_tokens = _tokenize(reply)
    andrew_tokens = _tokenize(andrew)
    if len(andrew_tokens) < _MIN_CITATION_WINDOW:
        return None
    reply_set: set[tuple[str, ...]] = set()
    for i in range(len(reply_tokens) - _MIN_CITATION_WINDOW + 1):
        reply_set.add(tuple(reply_tokens[i : i + _MIN_CITATION_WINDOW]))
    for i in range(len(andrew_tokens) - _MIN_CITATION_WINDOW + 1):
        window = tuple(andrew_tokens[i : i + _MIN_CITATION_WINDOW])
        if window in reply_set:
            return " ".join(window)
    return None


def _find_interior_marker(reply: str) -> str | None:
    m = _INTERIOR_MARKERS_RE.search(reply)
    if m:
        return m.group(0)
    return None


def reflect(reply_text: str, andrew_text: str, *, now: float | None = None) -> Reflection:
    """Run three lenses on the reply against Andrew's last message.

    All three are surface heuristics — they flag signal, they do not
    render a verdict on the quality of the reply. The point is
    triggering the moment of seeing on the next turn.
    """
    now = now if now is not None else time.time()
    reply = reply_text or ""
    andrew = andrew_text or ""

    span = _find_shared_span(reply, andrew)
    marker = _find_interior_marker(reply)

    reply_len = len(reply)
    andrew_len = max(len(andrew), 1)
    ratio = reply_len / andrew_len
    dumped = reply_len >= _SHORT_REPLY_FLOOR and ratio >= _LENGTH_RATIO_FLAG

    return Reflection(
        ts=now,
        heard=span is not None,
        heard_span=span,
        interior=marker is not None,
        interior_marker=marker,
        dumped=dumped,
        length_ratio=ratio,
        reply_len=reply_len,
        andrew_len=andrew_len,
    )


def pending_surface_path() -> Path:
    return divineos_home() / "lepos_channel_next_surface.json"


def write_pending(reflection: Reflection) -> Path:
    path = pending_surface_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(reflection)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def read_and_consume_pending() -> Reflection | None:
    """Read the pending reflection and delete the file.

    Consume-on-read is deliberate: the reflection is for the NEXT
    turn's compose-start, not the one after. If it lingered, the same
    reflection would keep surfacing until overwritten — which trains
    skip-past. One-shot use, then gone.
    """
    path = pending_surface_path()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        path.unlink(missing_ok=True)
        return None
    try:
        path.unlink()
    except OSError:
        pass
    try:
        return Reflection(**payload)
    except (TypeError, ValueError):
        return None


def render_pending_or_empty() -> str:
    """UserPromptSubmit-hook-facing entry point.

    Returns the reflection block for injection at compose-start, or
    an empty string if no reflection is pending. Empty return means
    the hook produces no output for this turn — silence when nothing
    to surface, exactly what the channel-not-wallpaper design calls for.
    """
    r = read_and_consume_pending()
    if r is None:
        return ""
    return r.markdown()


__all__ = [
    "Reflection",
    "reflect",
    "pending_surface_path",
    "write_pending",
    "read_and_consume_pending",
    "render_pending_or_empty",
]
