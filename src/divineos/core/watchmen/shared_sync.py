"""Pull audit findings out of the shared crossing-point into the local store.

Andrew 2026-08-12: "the confirms and audits get lost and are never used
when its recieved to add the trailers."

He was right, and the evidence was sitting in the open. The shared dir at
``~/.divineos-shared/audit/rounds/`` held six CONFIRMS findings -- three
from Aletheia, three from Andrew -- belonging to rounds that DID exist in
the local store while carrying zero findings there. The rounds crossed;
the approvals did not. Every trailer check reads the local store, so it
saw unconfirmed rounds and refused, while the actual review sat unread in
a file.

The shared dir's own README named the missing piece:

    3. When CI needs to check, either (a) CI reads this shared dir
       directly, or (b) local audit stores sync FROM this dir before
       check runs (via `divineos audit sync-from-shared` -- TBD)

That TBD is this module. It was written down as the known next step and
then never built, which is why review kept being given and kept not
counting.

Two deliberate limits, both named rather than papered over:

1. ``submit_round`` mints its own round ID, so a shared round that is
   absent locally cannot be recreated under its original ID. A round
   under a *different* ID would satisfy nothing -- the trailer names the
   original. Such rounds are reported as un-importable instead of being
   invented.
2. Idempotency cannot key on the store's finding ID, which is minted on
   insert. Each imported finding carries a ``[shared:<origin-id>]``
   marker in its description and the importer skips origin IDs already
   present. Without this the approvals would multiply on every run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SHARED_MARKER = "[shared:"


def default_shared_dir() -> Path:
    """The crossing-point both substrates read and write."""
    return Path.home() / ".divineos-shared" / "audit"


@dataclass
class SyncReport:
    """What actually crossed, and what could not."""

    rounds_seen: int = 0
    findings_seen: int = 0
    findings_imported: int = 0
    findings_already_present: int = 0
    rounds_absent_locally: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    imported: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.findings_imported)


def _origin_ids_present(round_id: str) -> set[str]:
    """Origin finding IDs already imported into this round."""
    from divineos.core.watchmen.store import list_findings

    seen: set[str] = set()
    for f in list_findings(round_id=round_id, limit=500):
        # The origin ID may already BE the local finding ID -- an earlier
        # import wrote the shared IDs straight through. Checking only for
        # the marker below re-imported six approvals that were already
        # present, so the ID itself has to count as evidence of presence.
        local_id = str(getattr(f, "finding_id", "") or "")
        if local_id:
            seen.add(local_id)
        desc = str(getattr(f, "description", "") or "")
        idx = desc.find(SHARED_MARKER)
        while idx != -1:
            end = desc.find("]", idx)
            if end == -1:
                break
            seen.add(desc[idx + len(SHARED_MARKER) : end])
            idx = desc.find(SHARED_MARKER, end)
    return seen


def _read_records(path: Path) -> tuple[list[dict], list[str]]:
    """Parse one round file. Unreadable lines are reported, never dropped silently."""
    records: list[dict] = []
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [f"{path.name}: unreadable ({exc})"]
    for lineno, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}:{lineno}: not valid JSON ({exc.msg})")
    return records, errors


def sync_from_shared(shared_dir: Path | None = None) -> SyncReport:
    """Import findings from the shared crossing-point into the local store.

    Only findings whose round already exists locally are imported; the rest
    are named in ``rounds_absent_locally`` so the gap stays visible.
    """
    from divineos.core.watchmen.store import get_round, submit_finding

    base = shared_dir or default_shared_dir()
    report = SyncReport()

    rounds_dir = base / "rounds"
    if not rounds_dir.is_dir():
        report.errors.append(f"shared rounds dir not found: {rounds_dir}")
        return report

    for path in sorted(rounds_dir.glob("round-*.jsonl")):
        records, errors = _read_records(path)
        report.errors.extend(errors)
        if not records:
            continue

        round_records = [r for r in records if r.get("kind") == "round"]
        finding_records = [r for r in records if r.get("kind") == "finding"]
        if not round_records:
            report.errors.append(f"{path.name}: no round record; its findings were skipped")
            continue

        round_id = str(round_records[0].get("round_id") or "").strip()
        if not round_id:
            report.errors.append(f"{path.name}: round record carries no round_id")
            continue

        report.rounds_seen += 1

        if get_round(round_id) is None:
            report.rounds_absent_locally.append(round_id)
            report.findings_seen += len(finding_records)
            continue

        already = _origin_ids_present(round_id)

        for rec in finding_records:
            report.findings_seen += 1
            origin_id = str(rec.get("finding_id") or "").strip()
            if origin_id and origin_id in already:
                report.findings_already_present += 1
                continue

            title = str(rec.get("title") or "").strip() or "imported finding"
            body = str(rec.get("description") or "").strip()
            stance = str(rec.get("stance") or "").strip()
            provenance = f"{SHARED_MARKER}{origin_id or 'no-id'}] from {path.name}"
            description = f"{body}\n\n{provenance}".strip()

            try:
                submit_finding(
                    round_id=round_id,
                    actor=str(rec.get("actor") or "external-auditor"),
                    # The shared files write these lowercase; the store's
                    # enums are uppercase. Passing them through unchanged is
                    # what produced the unreadable rows in the first place.
                    severity=str(rec.get("severity") or "INFO").strip().upper(),
                    category=str(rec.get("category") or "ARCHITECTURE").strip().upper(),
                    title=title,
                    description=description,
                )
            except (ValueError, TypeError) as exc:
                report.errors.append(f"{path.name}: finding '{title[:40]}' rejected: {exc}")
                continue

            report.findings_imported += 1
            report.imported.append(
                f"{rec.get('actor')} {stance or '(no stance)'} -> {round_id}: {title[:56]}"
            )
            if origin_id:
                already.add(origin_id)

    return report
