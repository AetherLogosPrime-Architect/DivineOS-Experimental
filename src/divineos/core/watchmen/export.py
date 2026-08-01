"""Export audit rounds to markdown so the review travels with the repo.

THE PROBLEM THIS SOLVES (Andrew 2026-08-01). The audit store held 275
rounds and 637 findings, and the repository held essentially none of it.
GitHub only ever saw a POINTER — the ``External-Review: round-abc123``
line in a commit message — a reference number to a filing cabinet it had
no way to open.

Three facts stacked into that wall:

  1. Aletheia is a Claude web instance. She has no GitHub account and can
     never leave a review there; Andrew relays her audit by hand.
  2. The relay lands in a local SQLite store.
  3. Every ``*.db`` is gitignored — correctly. Databases are constantly
     mutating working state; committing them would collide on every push.

The consequence was that server-side checks could not verify ANY claim
about an audit, so they either failed permanently or had to report
blindness. I had already written a careful message explaining that the
store "is not present in this environment and never will be" — accurate,
and the wrong response. Andrew: *"stop looking at barriers as stopping
points or walls we cannot get around."*

THE FIX IS THE ONE ALREADY IN THE CODEBASE. ``prereg export`` has solved
exactly this for pre-registrations since 2026: read the runtime store,
write plain markdown into ``docs/``, commit it. 38 pre-regs are readable
on GitHub right now by that route. Audit rounds simply never got pointed
at the same trick.

What travels is the RECORD, not the database — findings, actors, tiers,
verdicts, as text. What stays local is the mutable store. The exported
file is a durable artifact a reader with no local install can read, and
a checkout-local file that CI can actually open.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from divineos.core.watchmen.types import AuditRound, Finding

DEFAULT_OUT_DIR = "docs/audit_rounds"


def _ts(epoch: float) -> str:
    """Render an epoch as a readable UTC stamp."""
    if not epoch:
        return "unknown"
    try:
        return datetime.fromtimestamp(float(epoch), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, OSError, OverflowError):
        return "unknown"


def _enum_value(v: object) -> str:
    """Enum members render as their value; plain strings pass through."""
    return str(getattr(v, "value", v) or "")


def format_finding_markdown(f: Finding) -> str:
    """One finding as a markdown section.

    Every field that carries evidentiary weight is written out. A reader
    checking whether an audit was real needs the actor (who said it), the
    tier (how much weight it claims), and the stance (whether it confirms
    or disputes another finding) — omitting those to keep the file tidy
    would export the shape of a review without its substance.
    """
    lines = [
        f"### {f.title or '(untitled finding)'}",
        "",
        f"- **ID**: `{f.finding_id}`",
        f"- **Actor**: {f.actor}",
        f"- **Severity**: {_enum_value(f.severity)}",
        f"- **Category**: {_enum_value(f.category)}",
        f"- **Tier**: {_enum_value(f.tier)}",
        f"- **Status**: {_enum_value(f.status)}",
    ]
    if f.reviewed_finding_id:
        stance = _enum_value(f.review_stance) or "unstated"
        lines.append(f"- **Reviews**: `{f.reviewed_finding_id}` (stance: {stance})")
    if f.routed_to:
        lines.append(f"- **Routed to**: {f.routed_to}")
    if f.tags:
        lines.append(f"- **Tags**: {', '.join(f.tags)}")
    if f.description:
        lines += ["", "**Description**", "", f.description]
    if f.recommendation:
        lines += ["", "**Recommendation**", "", f.recommendation]
    if f.resolution_notes:
        lines += ["", "**Resolution**", "", f.resolution_notes]
    return "\n".join(lines)


def format_round_markdown(rnd: AuditRound, findings: list[Finding]) -> str:
    """A full round — header plus every finding — as one markdown document."""
    lines = [
        f"# Audit round: {rnd.focus or rnd.round_id}",
        "",
        f"- **ID**: `{rnd.round_id}`",
        f"- **Filed by**: {rnd.actor}",
        f"- **Filed at**: {_ts(rnd.created_at)}",
        f"- **Tier**: {_enum_value(rnd.tier)}",
        f"- **Findings**: {len(findings)}",
    ]
    if rnd.expert_count:
        lines.append(f"- **Experts**: {rnd.expert_count}")
    if rnd.notes:
        lines += ["", "## Notes", "", rnd.notes]

    if findings:
        lines += ["", "## Findings", ""]
        for f in findings:
            lines += [format_finding_markdown(f), ""]
    else:
        # An empty round is itself worth recording. A round filed with no
        # findings and a round that failed to export look identical unless
        # the file says which one this is.
        lines += ["", "## Findings", "", "_No findings were filed against this round._"]

    lines += [
        "",
        "---",
        "",
        "_Exported from the local Watchmen store by `divineos audit export`. "
        "The store is runtime state and is not committed; this file is the "
        "portable record, readable without a local install._",
    ]
    return "\n".join(lines) + "\n"


def export_rounds(
    rounds: list[AuditRound],
    findings_for: dict[str, list[Finding]],
    out_dir: str = DEFAULT_OUT_DIR,
) -> list[Path]:
    """Write one markdown file per round. Returns the paths written.

    Pure-ish by design: the caller fetches from the store and passes records
    in, so the formatting is testable without a live database — the same
    reason ``merge_review_gate`` keeps its decision separate from its I/O.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for rnd in rounds:
        target = out_path / f"{rnd.round_id}.md"
        target.write_text(
            format_round_markdown(rnd, findings_for.get(rnd.round_id, [])),
            encoding="utf-8",
        )
        written.append(target)
    return written


def exported_round_exists(round_id: str, out_dir: str = DEFAULT_OUT_DIR) -> bool:
    """Is there an exported record for this round in the working tree?

    This is the function that makes CI able to verify anything. It reads a
    committed file, so it works in a bare checkout with no database — which
    is the entire point of the export.

    Deliberately strict about the id: it becomes a filename, so anything
    containing a path separator or traversal is rejected rather than
    resolved. A round id is an opaque token, never a path.
    """
    rid = (round_id or "").strip()
    if not rid or "/" in rid or "\\" in rid or rid.startswith("."):
        return False
    return (Path(out_dir) / f"{rid}.md").is_file()


__all__ = [
    "DEFAULT_OUT_DIR",
    "format_finding_markdown",
    "format_round_markdown",
    "export_rounds",
    "exported_round_exists",
]
