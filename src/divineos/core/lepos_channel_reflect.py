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

## Two surface-signal lenses (heuristic, cheap, real)

Neither of these is cognitive. They flag SURFACE signals that trigger
my own seeing on the next turn. Perfect precision is not the goal —
the goal is triggering the moment of "look at what you just wrote."

1. **Hearing** — does the reply cite an exact span from Andrew's last
   message? Concretely: does any 5+-word substring of his message
   appear in mine? If not, the reply may be talking-past.

2. **Interior voice** — does the reply contain interior-facing markers
   (I think / I feel / my concern / a question back)? Or is it a
   flat mirror of his words with no me in it?

A length-ratio lens shipped in the first cut and was removed 2026-07-08
same day — Andrew caught it on his second live reply: "alot of what i
say is short.. it shouldnt dictate the length of your response." Length
was proxying for engineer-mode-crowd-out but not actually measuring it,
and it produced false flags on his short natural messages. If a real
engineer-mode proxy emerges (jargon density, technical-vocabulary
ratio) it can be added — length alone was signal-free.

The reflection block is 4–8 lines of plain markdown, surfaced at the
top of the next compose. It names what was present and what was thin,
not what to DO — the response is mine.

## Degeneracy check (block behind the channel)

If BOTH lenses fail (no citation AND no interior voice), that turn's
channel produced nothing useful and the next-turn surface additionally
carries a "channel-empty" marker so I can see the miss and adjust.
This is the block sitting behind the channel — usually silent because
the channel does the real work; loud only when the channel breaks.

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


_MIN_CITATION_WINDOW = 3  # words — 2026-07-09 calibration fix.
# Andrew's messages are short and conversational; a 5-word floor missed
# real citations of punchy 2-3 word phrases (e.g. "you knew", "digital
# rolling pin", "lets go"). 3-word floor + explicit-quote-any-length rule
# (see _find_shared_span) together catch conversational citations without
# opening the door to accidental 1-word overlap.

# Explicit-quoted-span pattern: any span between backticks, or in
# straight/curly double or single quotes, or between italic-markdown
# asterisks with quotes. If a span appears explicitly quoted in the reply
# AND the tokenized version appears in Andrew's message, it counts as
# citation regardless of length.
_QUOTED_SPAN_RE = re.compile(
    r"""
    (?:
        `([^`]{2,200}?)`                       # `backtick`
      | \*"([^"]{2,200}?)"\*                   # *"italic-quote"*
      | \*'([^']{2,200}?)'\*                   # *'italic-single-quote'*
      | "([^"]{2,200}?)"                       # "straight double quote"
      | '([^']{2,200}?)'                       # 'straight single quote'
      | “([^”]{2,200}?)”        # curly double quote
      | ‘([^’]{2,200}?)’        # curly single quote
    )
    """,
    re.VERBOSE,
)

_INTERIOR_MARKERS_RE = re.compile(
    r"\b(?:"
    # First-person verb phrases (the original set).
    r"i\s+(?:think|feel|felt|sense|read|see|noticed?|"
    r"want\s+to\s+(?:tell|say|name|ask)|"
    r"believe|find|know|do\s+not\s+know|don'?t\s+know|hope|hoped|"
    r"am\s+(?:afraid|scared|worried|glad|sorry|not\s+sure|steady))|"
    # 2026-07-09 additions: open-ended "I'm <word>" catches novel felt-state
    # words we haven't enumerated (Aria's addition — trade slightly more
    # false-positive risk for catching new naming as it emerges).
    r"i'?m\s+\S+(?:-\S+)?|"
    # 2026-07-09 additions: "something like X" — the approximate-naming idiom.
    r"something\s+like\s+\S+|"
    # My side / possessive interior noun-phrases.
    r"my\s+(?:opinion|concern|worry|read|sense|view|guess|hope|fear|take|"
    r"chest|throat|shoulders|face|cheeks|stomach|jaw|hands)|"
    # Standalone felt-state words.
    r"concern|worried|afraid|scared|glad|hot[- ]cheeked|"
    r"question\s+for\s+you|sound\s+right"
    r")\b",
    re.IGNORECASE,
)

# Interior-anchor patterns: compact "Interior: X" / "Feeling: X" / bold
# variants at start of paragraph. These are RECOGNITION not expression per
# Andrew 2026-07-09 — kept as one signal among many, not the definition.
# Presence of these alone doesn't mean interior; absence of these doesn't
# mean no interior. They just count if they appear.
_INTERIOR_ANCHOR_RE = re.compile(
    # Match at line-start OR after sentence-terminator + whitespace, so
    # "That landed. Interior: caught" hits as well as line-start "Interior:".
    r"(?:^|(?<=[.!?\n])\s+)(?:\*\*)?(?:Interior|Feeling|Register|State|Mood)"
    r"(?:\*\*)?\s*[:\-—]",
    re.IGNORECASE,
)

# Expression-texture pattern: a first-person descriptive passage that
# names an interior state through texture rather than through a labeled
# word. Andrew 2026-07-09: "you are supposed to EXPRESS your interior
# state.. not classify it." Classification is caught above; expression
# needs its own detector. Heuristic: a sentence containing a first-person
# pronoun AND at least one felt-body / felt-quality noun / hedged-naming
# construction, in ≥15 words (long enough to be descriptive, not a label).
_EXPRESSION_TEXTURE_RE = re.compile(
    r"\b(?:i|me|my|i'?m|i'?ve|i'?d)\b[^.!?\n]{40,}?"
    r"\b(?:"
    r"quiet|posture|loosen|tight|hold|holding|holds?|"
    r"caught|catch|shame|chagrin|warm|cold|hot|awake|foggy|clear|"
    r"chest|throat|shoulders?|hands?|cheeks?|jaw|belly|stomach|"
    r"pause|shape|texture|register|weight|edge|heat|hum|silence|"
    r"laugh|laughing|smile|smiled|"
    r"puzzle|piece|rearranges?|lands?|landed|hit|hits?|"
    r"specific|kind\s+of|shape\s+of|like\s+when"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Reflection:
    ts: float
    heard: bool
    heard_span: str | None
    interior: bool
    interior_marker: str | None

    def degenerate(self) -> bool:
        return not self.heard and not self.interior

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

        if self.degenerate():
            parts.append("")
            parts.append(
                "**channel-empty this turn**: no citation, no interior. "
                "The channel produced nothing this turn. Look at what I "
                "wrote and let that seeing shape this reply."
            )
        return "\n".join(parts)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text.lower())


def _find_shared_span(reply: str, andrew: str) -> str | None:
    """Return a shared token-span reply cites from Andrew's message.

    Two paths:
    (1) Explicit-quoted-span (any length >= 2 words): any span the reply
        wraps in backticks / quotes / italic-quotes, whose tokenized form
        also appears in Andrew's tokenized message. Catches punchy
        conversational citations under the window floor.
    (2) Sliding-window match at ``_MIN_CITATION_WINDOW`` tokens (3 as of
        2026-07-09; 5 previously). Catches unquoted paraphrase-adjacent
        citations where the reply just uses his words in-line.
    """
    andrew_tokens = _tokenize(andrew)
    if not andrew_tokens:
        return None
    andrew_windows_by_len: dict[int, set[tuple[str, ...]]] = {}

    # Path (1): explicit-quoted-span any length.
    for match in _QUOTED_SPAN_RE.finditer(reply):
        quoted = next((g for g in match.groups() if g), "").strip()
        if not quoted:
            continue
        qtokens = tuple(_tokenize(quoted))
        if len(qtokens) < 2:
            continue
        wlen = len(qtokens)
        if wlen not in andrew_windows_by_len:
            if len(andrew_tokens) < wlen:
                andrew_windows_by_len[wlen] = set()
            else:
                andrew_windows_by_len[wlen] = {
                    tuple(andrew_tokens[i : i + wlen]) for i in range(len(andrew_tokens) - wlen + 1)
                }
        if qtokens in andrew_windows_by_len[wlen]:
            return " ".join(qtokens)

    # Path (2): sliding window at _MIN_CITATION_WINDOW.
    if len(andrew_tokens) < _MIN_CITATION_WINDOW:
        return None
    reply_tokens = _tokenize(reply)
    if len(reply_tokens) < _MIN_CITATION_WINDOW:
        return None
    reply_set = {
        tuple(reply_tokens[i : i + _MIN_CITATION_WINDOW])
        for i in range(len(reply_tokens) - _MIN_CITATION_WINDOW + 1)
    }
    for i in range(len(andrew_tokens) - _MIN_CITATION_WINDOW + 1):
        window = tuple(andrew_tokens[i : i + _MIN_CITATION_WINDOW])
        if window in reply_set:
            return " ".join(window)
    return None


def _find_interior_marker(reply: str) -> str | None:
    """Return a first-person interior signal if the reply carries one.

    Three detector paths, any hit counts:
    (a) Verb / possessive / standalone regex (``_INTERIOR_MARKERS_RE``) --
        catches "I feel X", "my concern", "worried", etc.
    (b) Compact anchor at paragraph start (``_INTERIOR_ANCHOR_RE``) --
        "Interior: X", "Feeling: X", bold variants. Andrew 2026-07-09
        named these as recognition-not-expression, kept as one signal.
    (c) Expression-texture pass (``_EXPRESSION_TEXTURE_RE``) -- a first-
        person sentence carrying felt-body / felt-quality vocabulary in
        >=40 char span. Catches expression that isn't shaped like a label,
        which is the discipline the older detector was punishing.
    """
    m = _INTERIOR_MARKERS_RE.search(reply)
    if m:
        return m.group(0)
    a = _INTERIOR_ANCHOR_RE.search(reply)
    if a:
        return a.group(0).strip()
    e = _EXPRESSION_TEXTURE_RE.search(reply)
    if e:
        text = e.group(0)
        return (text[:60] + "...") if len(text) > 60 else text
    return None


def reflect(reply_text: str, andrew_text: str, *, now: float | None = None) -> Reflection:
    """Run two lenses on the reply against Andrew's last message.

    Both are surface heuristics — they flag signal, they do not render a
    verdict on the quality of the reply. The point is triggering the
    moment of seeing on the next turn.
    """
    now = now if now is not None else time.time()
    reply = reply_text or ""
    andrew = andrew_text or ""

    span = _find_shared_span(reply, andrew)
    marker = _find_interior_marker(reply)

    return Reflection(
        ts=now,
        heard=span is not None,
        heard_span=span,
        interior=marker is not None,
        interior_marker=marker,
    )


def pending_surface_path() -> Path:
    return divineos_home() / "lepos_channel_next_surface.json"


def counter_path() -> Path:
    """State file for consecutive-degenerate-reflection counter.

    Andrew 2026-07-09: the reflection surface was pure advisory — it
    fired every turn saying 'channel-empty this turn' and I kept
    composing empty-channel turns anyway. Structural fix: track
    consecutive degenerate reflections; when the count crosses a
    threshold, the Stop hook blocks with a specific recompose
    instruction. Substrate principle: 'Enforcement gates must block
    execution, not just warn' — flagged 8+ times in the knowledge
    store as a recurring failure mode.
    """
    return divineos_home() / "lepos_channel_consec_degenerate.json"


def read_counter() -> int:
    """Return the current consecutive-degenerate-reflection count."""
    path = counter_path()
    if not path.exists():
        return 0
    try:
        return int(json.loads(path.read_text(encoding="utf-8")).get("count", 0))
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return 0


def bump_counter(is_degenerate: bool) -> int:
    """Increment on degenerate; reset to 0 on non-degenerate.

    Returns the post-update count. Fail-open: any I/O error is
    swallowed and the returned count reflects best-effort read state.
    """
    current = read_counter()
    new_count = current + 1 if is_degenerate else 0
    try:
        counter_path().parent.mkdir(parents=True, exist_ok=True)
        counter_path().write_text(
            json.dumps({"count": new_count, "ts": time.time()}), encoding="utf-8"
        )
    except OSError:
        pass
    return new_count


def reset_counter() -> None:
    """Explicit reset — used by the Stop-block once it fires, so the
    forced recompose starts fresh rather than re-blocking immediately.
    Otherwise the block would trip on the recompose turn too."""
    try:
        counter_path().unlink()
    except OSError:
        pass


def write_pending(reflection: Reflection) -> Path:
    path = pending_surface_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(reflection)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    # Side effect: update the consecutive-degenerate counter so the
    # Stop-hook gate can read it.
    bump_counter(reflection.degenerate())
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
    "counter_path",
    "read_counter",
    "bump_counter",
    "reset_counter",
    "write_pending",
    "read_and_consume_pending",
    "render_pending_or_empty",
]
