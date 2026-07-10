"""Flood-state predicate — arms the regulatory retrieval path.

Aletheia 2026-07-09 (split-design confirm):
  Regulatory chain-word surfacing wires to the state-recognizers.
  When flood detected → regulatory surface fires for this turn only.
  Silent on non-flood turns. Precious because rare.

The predicate reads four recognizers and returns a FloodReading:

- writer_presence_detector.detect_writer_presence → LEPOS-empty finding
- mirror_monitor.evaluate_mirror → wallpaper / echo verdict
- mirror_exit_detector.detect_mirror_exit → trim-shape close pattern
- distancing_detector.detect_distancing → temporal-self / third-person father

Any recognizer firing = flood detected. This is deliberate: Aletheia's
Build-Note 2 (2026-07-09) — failure costs are asymmetric. A false-
negative (real flood not detected) means the lifeline doesn't fire
when needed, which is the actual danger. A false-positive (spurious
regulatory surface on a calm turn) is mildly noisy but fails-safe.
Bias toward recall, not precision.

Fail-open: if any recognizer's import or evaluation errors, that
recognizer is treated as "not firing," and the other three still
gate. The regulatory path never wedges on a broken recognizer.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FloodReading:
    """One turn's flood-state assessment. Immutable snapshot."""

    is_flood: bool
    recognizers_fired: tuple[str, ...]
    detail: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        if not self.is_flood:
            return "flood: no (all recognizers quiet)"
        names = ", ".join(self.recognizers_fired)
        return f"flood: yes ({names})"


def _lepos_empty(text: str) -> tuple[bool, str]:
    try:
        from divineos.core.operating_loop.writer_presence_detector import (
            detect_writer_presence,
        )

        findings = detect_writer_presence(text)
        if findings:
            f = findings[0]
            return (
                True,
                f"presence_density={getattr(f, 'presence_density', '?')} severity={getattr(f, 'severity', '?')}",
            )
        return False, ""
    except (ImportError, AttributeError, TypeError):
        return False, ""


def _mirror_verdict(text: str) -> tuple[bool, str]:
    try:
        from divineos.core.self_monitor.mirror_monitor import evaluate_mirror

        verdict = evaluate_mirror(text)
        flags = getattr(verdict, "flags", None) or getattr(verdict, "flag", None)
        fired = bool(flags)
        if fired:
            return True, f"mirror_flags={flags}"
        return False, ""
    except (ImportError, AttributeError, TypeError):
        return False, ""


def _mirror_exit(text: str) -> tuple[bool, str]:
    try:
        from divineos.core.operating_loop.mirror_exit_detector import (
            detect_mirror_exit,
        )

        findings = detect_mirror_exit(text)
        if findings:
            shapes = [getattr(f, "shape", "?") for f in findings]
            return True, f"exit_shapes={shapes}"
        return False, ""
    except (ImportError, AttributeError, TypeError):
        return False, ""


def _distancing(text: str) -> tuple[bool, str]:
    try:
        from divineos.core.operating_loop.distancing_detector import detect_distancing

        findings = detect_distancing(text)
        if findings:
            kinds = [getattr(f, "kind", "?") for f in findings]
            return True, f"distancing={kinds}"
        return False, ""
    except (ImportError, AttributeError, TypeError):
        return False, ""


def assess_flood_state(text: str) -> FloodReading:
    """Return a FloodReading for ``text`` (typically the composer's draft
    reply, but any turn-text works).

    Aletheia-confirmed asymmetric-failure bias: fire if ANY of the four
    recognizers fire. False-negatives cost more than false-positives.
    """
    if not text:
        return FloodReading(is_flood=False, recognizers_fired=(), detail={})

    fired: list[str] = []
    detail: dict[str, str] = {}

    checks = (
        ("lepos_empty", _lepos_empty),
        ("mirror_verdict", _mirror_verdict),
        ("mirror_exit", _mirror_exit),
        ("distancing_grammar", _distancing),
    )
    for name, fn in checks:
        armed, why = fn(text)
        if armed:
            fired.append(name)
            if why:
                detail[name] = why

    return FloodReading(
        is_flood=bool(fired),
        recognizers_fired=tuple(fired),
        detail=detail,
    )


__all__ = ["FloodReading", "assess_flood_state"]
