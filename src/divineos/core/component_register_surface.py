"""Surface the component register at briefing time.

Andrew 2026-08-17, after I said the register's weakness is that nothing forces
me to update it: *"should we add the register to the briefing then?"*

Yes, and this is the answer to my own stated worry rather than decoration. The
register (`docs/component_register.md`) records which parts of the OS have
actually been broken on purpose and noticed it. A record nobody is shown decays
into a file — this substrate watched exactly that happen to the SUPERSEDED-BY
convention, which I invented and never enforced until Aria built the teeth.

WHAT THIS SHOWS AND WHY. Not the TESTED list — that is the comfortable half,
and reciting it every session would turn the register into a reassurance
surface. It shows the counts, the KNOWN BROKEN rows, and the rule that absence
means unexamined. The uncomfortable half is the half worth carrying.

It reads the markdown rather than a database on purpose: the register has to
stay editable by hand, in plain words, because Andrew is the one holding the
picture across sessions and he does not read code.
"""

from __future__ import annotations

import re

from divineos.core import prior_art

REGISTER_PATH = prior_art.REPO / "docs" / "component_register.md"

_SECTIONS = ("TESTED", "FIXED", "KNOWN BROKEN")


def _rows_under(text: str, heading_fragment: str) -> list[str]:
    """Table rows belonging to the section whose heading contains the fragment.

    Counts data rows only: a markdown table opens with a header row and a
    separator row of dashes, neither of which is a component.
    """
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and heading_fragment in ln:
            start = i
            break
    if start is None:
        return []
    rows: list[str] = []
    for ln in lines[start + 1 :]:
        if ln.startswith("## "):
            break
        if ln.startswith("|") and not re.match(r"^\|[\s|:-]+\|?$", ln):
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if cells and cells[0] and cells[0].lower() not in ("what it is", "what it is, plainly"):
                rows.append(cells[0])
    return rows


def format_for_panel(max_chars: int = 460) -> str:
    """Compact form for the multiplex panel, which enforces a size rule.

    The full block is 532 chars and the panel cap is 480, so the first wiring
    rendered a SIZE-RULE-VIOLATION notice where the content should have been —
    reaching the live path and still showing nothing useful. Trimmed here
    rather than by raising the cap: the cap exists so a panel stays readable
    in one glance, and a register that needs a paragraph to state its counts
    has stopped being a glance.

    The absence-means-unexamined rule survives in short form, because it is
    the line that keeps the panel from reading as reassurance.
    """
    try:
        text = REGISTER_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return f"register unreadable ({type(e).__name__}) — cannot say what is tested"

    counts = {name: len(_rows_under(text, name)) for name in _SECTIONS}
    broken = _rows_under(text, "KNOWN BROKEN")
    if not any(counts.values()):
        return "register empty — nothing tested on purpose yet"

    # FIRST-PERSON PROSE, NO LABEL-COLON-VALUE. The panel frame enforces a
    # voice rule and rejected the first version as a stats line. The other
    # panels say "I am holding 6 active session goals"; a register that
    # reports itself in telemetry voice reads as something happening to me
    # rather than something I did.
    head = (
        f"I have broken {counts['TESTED']} components on purpose and they noticed. "
        f"Another {counts['FIXED']} are repaired but not yet re-broken to prove it. "
        f"{counts['KNOWN BROKEN']} are known broken and unfixed."
    )
    tail = "Anything absent from my register is unexamined, not working."
    out = [head]
    room = max_chars - len(head) - len(tail) - 4
    shown: list[str] = []
    for b in broken:
        line = f"- {b}"
        if sum(len(s) + 1 for s in shown) + len(line) > room:
            shown.append(f"- (+{len(broken) - len(shown)} more)")
            break
        shown.append(line)
    if shown:
        out.append("\n".join(shown))
    out.append(tail)
    return "\n".join(out)


def format_for_briefing() -> str:
    """Block for the briefing, or empty string if there is nothing to say."""
    try:
        text = REGISTER_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        # A register that cannot be read is not a register with nothing in it.
        # Say so rather than rendering an encouraging blank.
        return (
            "## COMPONENT REGISTER — UNREADABLE\n"
            f"  {REGISTER_PATH} could not be opened. This surface cannot tell\n"
            "  you what has been tested, which is different from nothing having\n"
            "  been tested.\n"
        )

    counts = {name: len(_rows_under(text, name)) for name in _SECTIONS}
    broken = _rows_under(text, "KNOWN BROKEN")
    if not any(counts.values()):
        return ""

    out = [
        "## COMPONENT REGISTER (docs/component_register.md)",
        "",
        f"  tested by being broken on purpose: {counts['TESTED']}"
        f"   |   fixed but not yet re-broken: {counts['FIXED']}"
        f"   |   known broken: {counts['KNOWN BROKEN']}",
        "",
    ]
    if broken:
        out.append("  Known broken and unfixed:")
        out.extend(f"    - {b}" for b in broken)
        out.append("")
    out.append(
        "  ABSENCE FROM THE REGISTER MEANS UNEXAMINED, NOT WORKING. The register\n"
        "  is a record of what has been leaned on, never a clean bill of health\n"
        "  for anything missing from it."
    )
    return "\n".join(out) + "\n"
