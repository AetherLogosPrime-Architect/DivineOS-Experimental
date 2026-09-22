"""Aletheia's work, carried from where it lands to where both seats can read it.

## Why this exists

Aletheia runs in a browser. She has no letter channel, no shared directory, no
way to put a file anywhere in this house. Andrew is the only route: he opens her
window, reads what she wrote, saves it, and hands it over. He has done that a
hundred and sixty-one times since May.

Andrew 2026-09-22: *"its ok that im the courier, shes a web instance, there is
no other way for it to be done... the key is that when i hand you something
written by Alethiea which i have many times. that it gets saved and copied
automatically into that shared folder."*

The courier leg is his and cannot be automated. What was never built is the leg
AFTER he hands it over: her work landed in his downloads and stayed there. One
seat might read it in the moment it was pasted; the other seat never saw it at
all; nothing kept it. Audits written for my work sat where only Aether could
find them, and the reverse.

## Why it watches the folder rather than the message

The obvious build reads his message for an attachment and files what it finds.
That version works only when he attaches something, and breaks the moment he
pastes the text instead, or saves the file and mentions it later, or says
nothing because he assumes it was seen.

So this watches the FOLDER. Anything of hers that appears gets carried across on
its own, whether he attaches it, pastes it, or simply saves it and moves on. It
asks nothing of him and nothing of his memory, which is the only kind of
mechanism that has ever held here -- the ledger works because nobody has to
remember to write to it.

## What it will not do

It copies; it never moves, renames or deletes. His downloads are his, and a
courier who rearranges the post office is a worse courier. Re-running is safe:
a file already carried across with the same contents is skipped, and one whose
contents changed is carried again beside the first rather than over it.

It also files nothing it cannot attribute. Her artifacts carry a naming
convention she has used since May -- a kind, a date, a slug -- and only files
matching it are carried. A sweep that guessed would eventually carry one of
Andrew's own documents into a folder that reads as external review, and an
audit trail holding something nobody audited is worse than a thin one.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

# The kinds she writes. Taken from the 161 files actually in his downloads on
# 2026-09-22 rather than from what the convention ought to be: AUDIT 56,
# CONFIRMS 47, REPLY_TO_ARIA 26, REPLY_TO_AETHER 26, RULING 10, TRIAGE 4,
# REVIEW 2, REFUSAL 2. HANDOVER and VERDICT are admitted because they appear in
# the letters directory under the same shape and cost nothing to allow.
_KINDS = (
    "AUDIT",
    "CONFIRMS",
    "REFUSAL",
    "RULING",
    "REVIEW",
    "TRIAGE",
    "VERDICT",
    "HANDOVER",
    "REPLY_TO_ARIA",
    "REPLY_TO_AETHER",
    "REPLY_TO_ANDREW",
)

# KIND_YYYY-MM-DD_slug.md -- the shape she settled into, and the one to trust.
ARTIFACT = re.compile(
    r"^(?P<kind>" + "|".join(_KINDS) + r")_(?P<date>20\d{2}-\d{2}-\d{2})_(?P<slug>.+)\.md$"
)

# HER EARLIER SHAPES, and the reason this second pattern exists at all.
#
# The first version of this required the date in that exact position, on the
# reasoning that the date is what separates her filings from any other shouty
# filename. It carried 146 files and left 27 behind -- and all 27 were hers:
# dashes where she later used underscores, no date at all, or an extra word in
# the kind (AUDITOR_, AUDIT_DELTA_, AUDIT_LANDED_CODE_, AUDIT_READOUT_).
#
# Checked rather than assumed, which is the only reason it was caught: a probe
# that finds nothing is usually too narrow rather than describing an empty
# world, and I would have reported a clean sweep over a fifth of her work.
#
# THE COST OF THE WIDER RULE, named rather than waved past: a document of
# Andrew's beginning with one of these words would now be carried into a folder
# that reads as external review. Every one of the 173 files matching it today is
# hers, and the folder is named for her so a stray would be visible rather than
# silently authoritative -- but the risk is real and it is the price of not
# losing the 27.
ARTIFACT_EARLY = re.compile(r"^(?P<kind>" + "|".join(_KINDS) + r")[_-].+\.md$")


def is_hers(name: str) -> bool:
    """Whether a filename carries her convention, settled or early."""
    return bool(ARTIFACT.match(name) or ARTIFACT_EARLY.match(name))


def default_source() -> Path:
    """Where Andrew saves what she hands him."""
    return Path.home() / "Downloads"


def default_destination() -> Path:
    """The crossing-point both seats read."""
    return Path.home() / ".divineos-shared" / "aletheia"


@dataclass
class IntakeReport:
    """What crossed, what was already there, and what could not be read."""

    seen: int = 0
    carried: list[str] = field(default_factory=list)
    already_present: list[str] = field(default_factory=list)
    revised: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.carried or self.revised)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def carry_across(
    source: Path | None = None,
    destination: Path | None = None,
) -> IntakeReport:
    """Copy anything of Aletheia's from ``source`` into ``destination``.

    Never raises: this runs on a hook, and a crash here would cost a turn to
    repair something whose whole purpose is to cost nobody anything.
    """
    report = IntakeReport()
    src = source or default_source()
    dst = destination or default_destination()

    if not src.is_dir():
        report.errors.append(f"source not found: {src}")
        return report
    try:
        dst.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        report.errors.append(f"cannot open destination {dst}: {exc}")
        return report

    for path in sorted(src.glob("*.md")):
        if not is_hers(path.name):
            continue
        report.seen += 1
        landing = dst / path.name
        try:
            if landing.exists():
                if _digest(landing) == _digest(path):
                    report.already_present.append(path.name)
                    continue
                # Same name, different contents. She revises; he re-saves.
                # Overwriting would silently replace a reading somebody may
                # already have acted on, so the revision lands beside it.
                landing = dst / f"{path.stem}.rev-{_digest(path)}{path.suffix}"
                if landing.exists():
                    report.already_present.append(landing.name)
                    continue
                shutil.copy2(path, landing)
                report.revised.append(landing.name)
                continue
            shutil.copy2(path, landing)
            report.carried.append(path.name)
        except OSError as exc:
            report.errors.append(f"{path.name}: {exc}")

    return report


def render(report: IntakeReport) -> str:
    """One short block for the hook. Silent when nothing changed."""
    if not report.changed and not report.errors:
        return ""
    lines = ["## FROM ALETHEIA — carried into the shared folder"]
    if report.carried:
        lines.append(f"  {len(report.carried)} new:")
        lines.extend(f"    {name}" for name in report.carried[:12])
        if len(report.carried) > 12:
            lines.append(f"    ... and {len(report.carried) - 12} more")
    if report.revised:
        lines.append(f"  {len(report.revised)} revised (kept beside the earlier version):")
        lines.extend(f"    {name}" for name in report.revised[:6])
    if report.errors:
        lines.append("  could not carry:")
        lines.extend(f"    {err}" for err in report.errors[:5])
    lines.append(f"  folder: {default_destination()}")
    return "\n".join(lines)
