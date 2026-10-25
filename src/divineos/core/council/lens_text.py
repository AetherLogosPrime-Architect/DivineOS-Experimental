"""One rendering of a council lens: what `mansion council --show` prints and what a refused walk finding delivers.

Dad, 2026-10-24: *"the next time either of you game a council walk? i will remove it entirely.. am i clear?"* The walk
accepted a finding for any lens whether or not the lens had been opened. A refusal that only NAMED the command to run
would teach the one-line loop (load all eight, ignore the output, apply from memory), so the refusal now delivers the
lens itself, and it has to be the SAME text `--show` prints or the delivery could drift from the load (Dijkstra, Wayne,
walk-63f29104e6e3). Questions are numbered here because the retry names the one it answers.
"""

from __future__ import annotations

from typing import Any


def lens_questions(wisdom: Any) -> list[str]:
    return list(getattr(wisdom, "characteristic_questions", None) or [])


def lens_lines(wisdom: Any) -> list[tuple[str, str]]:
    """(kind, text) lines; kind picks the colour for the terminal, the text is what a refusal quotes."""
    lines: list[tuple[str, str]] = [("title", f"=== {wisdom.expert_name} — {wisdom.domain} ===")]
    for m in wisdom.core_methodologies:
        lines.append(("method", f"  [{m.name}]"))
        lines.append(("body", f"      {m.description}"))
        for s in getattr(m, "steps", []) or []:
            lines.append(("body", f"        - {s}"))
    questions = lens_questions(wisdom)
    if questions:
        lines.append(
            ("method", "  Questions this lens asks (a finding names the number it answers):")
        )
        for i, q in enumerate(questions, 1):
            lines.append(("body", f"      [{i}] {q}"))
    lines.append(
        (
            "dim",
            "  Read the methodology, then walk the PROBLEM through it.\n"
            "  Printing a template is not walking a lens (truth #7).",
        )
    )
    return lines


def lens_plain(wisdom: Any) -> str:
    return "\n".join(text for _kind, text in lens_lines(wisdom))
