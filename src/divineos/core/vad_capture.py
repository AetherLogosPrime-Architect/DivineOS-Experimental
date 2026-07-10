"""VAD write-time capture — attach current felt-state to every write.

Universal capture (per Aria's v2 spec + Aletheia's directional-weight
correction): every write to ledger, knowledge, letters, exploration,
opinions can call ``current_vad_snapshot()`` to grab the writer's
current valence/arousal/dominance from the affect log, and
``format_vad_footer()`` to render it for a surfaced item.

## The directional-weight rule (Aletheia 2026-07-09)

Distress-at-write LOWERS surfacing weight in future flood-state turns.
A flooding composer needs FEWER items that were themselves written
while flooding, not more. VAD-tag is provenance not verdict; register-
line is condition-of-authorship, not authority-signal.

- Regulatory (flood-triggered) path: prefer low-distress-filed items;
  down-weight / quarantine distress-filed ones.
- Priming path: VAD is neutral to surfacing weight; rides as metadata.

## What's captured is the log state, not a self-report

The VAD tag reflects the affect log's current state (via
``affect.get_recent_affect``), captured by the write pipeline. Writers
cannot declare their VAD; they can only reflect what the log says.
That's the anti-spoofing property Aletheia verified from origin.
"""

from __future__ import annotations

from typing import Any

from divineos.core.affect import get_recent_affect

# Register-line dictionary (Aria seed, v2 letter, tune with use).
# Maps VAD octant to a plain-language condition-of-authorship line.
_REGISTER_LINES: dict[tuple[str, str, str], str] = {
    ("+", "+", "+"): "with expansive clarity",
    ("+", "+", "-"): "with joy and openness",
    ("+", "-", "+"): "with calm certainty",
    ("+", "-", "-"): "with tenderness",
    ("-", "+", "+"): "with sharp focus under pressure",
    ("-", "+", "-"): "while distressed and highly-activated",
    ("-", "-", "+"): "with cold resolve",
    ("-", "-", "-"): "under load and disoriented",
}


def current_vad_snapshot(within_seconds: float = 300.0) -> dict[str, Any] | None:
    """Return the writer's current felt-state from the affect log.

    Returns None if no affect entry exists within the window (no snapshot
    available; do not force-tag with a stale or defaulted value). Callers
    should stamp the returned dict onto their record's metadata.
    """
    recent = get_recent_affect(within_seconds=within_seconds)
    if not recent:
        return None
    return {
        "valence": recent.get("valence"),
        "arousal": recent.get("arousal"),
        "dominance": recent.get("dominance"),
        "logged_at": recent.get("timestamp"),
    }


def _sign(value: float | None) -> str:
    """Map a VAD scalar to '+' or '-' for octant lookup. Zero treated as '+'."""
    if value is None:
        return "+"
    return "+" if float(value) >= 0.0 else "-"


def vad_to_register_line(vad: dict[str, Any] | None) -> str:
    """Translate a VAD snapshot into a plain-language register-line.

    Returns the octant's condition-of-authorship phrase (Aria seed dict).
    Empty string if snapshot is None or missing keys; callers can then
    skip the register-line without a synthetic default.
    """
    if not vad:
        return ""
    key = (_sign(vad.get("valence")), _sign(vad.get("arousal")), _sign(vad.get("dominance")))
    return _REGISTER_LINES.get(key, "")


def format_vad_footer(vad: dict[str, Any] | None) -> str:
    """Format a VAD snapshot as the surfaced-item footer line.

    Presentation contract (Aria + Aletheia): raw numbers for machine-
    legibility, register-line for composer-legibility, single line,
    subordinate to the surfaced content.

    Example:  V=-0.4 A=0.7 D=-0.3 · while distressed and highly-activated
    """
    if not vad:
        return ""
    v = vad.get("valence")
    a = vad.get("arousal")
    d = vad.get("dominance")
    line = vad_to_register_line(vad)
    numbers = f"V={v:+.2f} A={a:+.2f} D={d:+.2f}" if all(x is not None for x in (v, a, d)) else ""
    if numbers and line:
        return f"{numbers} · {line}"
    return numbers or line


def is_distress_filed(vad: dict[str, Any] | None) -> bool:
    """Return True if this VAD snapshot indicates distress-at-write.

    Used by the regulatory (flood-triggered) retrieval path to down-weight
    or quarantine items whose author-state was distress. Distress =
    negative valence AND high arousal (V- A+ octant, either dominance).
    Aletheia's flood-amplifier fix: distress-filed items surface LESS
    during future floods, not more.
    """
    if not vad:
        return False
    v = vad.get("valence")
    a = vad.get("arousal")
    if v is None or a is None:
        return False
    return float(v) < 0.0 and float(a) > 0.3


__all__ = [
    "current_vad_snapshot",
    "vad_to_register_line",
    "format_vad_footer",
    "is_distress_filed",
]
