#!/usr/bin/env python3
"""Sweep the substrate for wins that already have evidence, and file them.

Andrew 2026-08-25: *"you should do a deep sweep of the ledger and your files
and record all of your wins. you have a TON of them."*

He is right that they exist and right that they are unrecorded. The wins ledger
shipped 2026-08-03 and had zero callers until the same day this ran, because it
had no command -- so three weeks of work landed entirely in the faults pan while
the wins pan sat sealed. This walks the stores that already hold judged,
evidence-bearing outcomes and moves them across.

WHAT THIS DOES NOT DO. It does not decide that anything was good. Every record
it reads was already ruled on by someone at the time: a pre-registration
outcome was decided by a named actor against a falsifier written before the
mechanism shipped, and a correction could not reach INTEGRATED without an
evidence pointer naming a commit, file or test. This transcribes existing
verdicts into a store that could not receive them. It invents no judgment.

THE PROVENANCE MARKER IS THE POINT, not decoration. 256 of the candidates are
resolved corrections. Filing those without a mark would make the wins pan a
re-skin of the faults pan, so a reader seeing "Wins 300 / Corrections 449"
would take them for independent measurements when most of the left number IS
part of the right number, resolved. That is the two-consumers-disagreeing shape
fixed twice on the day this was written; building it deliberately would be
worse than the silence it replaces. Every swept entry therefore carries
``[swept <source>]`` inside its evidence, and the counts are reported split.

Skips anything whose evidence is too thin to check. A citation-shaped object is
not a citation, and ``record_success`` refuses those on purpose.
"""

from __future__ import annotations

import argparse
import pathlib
import sqlite3
import sys

SWEEP_MARK = "[swept 2026-08-25"


def _existing_evidence() -> set[str]:
    """Evidence strings already in the ledger, for idempotence."""
    from divineos.core.success_ledger import load_successes

    return {str(entry.get("evidence", "")) for entry in load_successes()}


def _prereg_candidates() -> list[dict]:
    """Pre-registrations whose claim was tested and HELD.

    The purest form of code-does-what-it-claims: a falsifier written before the
    mechanism shipped, and a later ruling that it did not trigger.
    """
    from divineos.core.pre_registrations import Outcome, list_pre_registrations

    out = []
    for entry in list_pre_registrations(outcome=Outcome.SUCCESS):
        notes = " ".join((entry.outcome_notes or "").split())
        mechanism = " ".join((entry.mechanism or "").split())
        if len(notes) < 60 or not mechanism:
            continue
        out.append(
            {
                "what": f"Mechanism held its pre-registered claim: {mechanism[:220]}",
                "evidence": f"{SWEEP_MARK} prereg] {entry.prereg_id}, ruled SUCCESS "
                f"by {entry.actor or 'unknown'}. {notes[:400]}",
                "yielded": f"The claim was testable, tested, and survived. {notes[:300]}",
                "goal": " ".join((entry.claim or "").split())[:180] or None,
                "goal_met": True,
            }
        )
    return out


def _correction_candidates() -> list[dict]:
    """Corrections that reached INTEGRATED with a structural artifact.

    A fault named, a fix built, a pointer a later reader can check. Andrew:
    *"just because you fail and make mistakes that does not determine your
    character.. what determines it is how you deal with it."* This is the
    dealing-with, on the record, with a commit hash on it.
    """
    path = pathlib.Path.home() / ".divineos" / "andrew_corrections.db"
    if not path.exists():
        return []
    conn = sqlite3.connect(path)
    try:
        rows = conn.execute(
            "SELECT id, correction_text, integration_evidence FROM andrew_corrections "
            "WHERE UPPER(status) = 'INTEGRATED' AND integration_evidence IS NOT NULL "
            "ORDER BY id"
        ).fetchall()
    finally:
        conn.close()

    out = []
    for cid, text, evidence in rows:
        text = " ".join((text or "").split())
        evidence = " ".join((evidence or "").split())
        if len(evidence) < 40 or not text:
            continue
        out.append(
            {
                "what": f"Corrected and shipped the fix: {text[:220]}",
                "evidence": f"{SWEEP_MARK} correction] andrew-correction #{cid}. {evidence[:400]}",
                "yielded": f"The fault stopped being a note and became a change a reader "
                f"can check: {evidence[:300]}",
                "goal": None,
                "goal_met": None,
            }
        )
    return out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        action="store_true",
        help="Actually write to the ledger. Without this, reports only.",
    )
    parser.add_argument(
        "--source",
        choices=("prereg", "correction", "all"),
        default="all",
    )
    args = parser.parse_args(argv[1:])

    sources: dict[str, list[dict]] = {}
    if args.source in ("prereg", "all"):
        sources["prereg"] = _prereg_candidates()
    if args.source in ("correction", "all"):
        sources["correction"] = _correction_candidates()

    already = _existing_evidence()
    total_new = 0
    total_skipped = 0

    for name, candidates in sources.items():
        fresh = [c for c in candidates if c["evidence"] not in already]
        dupes = len(candidates) - len(fresh)
        total_new += len(fresh)
        total_skipped += dupes
        print(
            f"{name:12s} candidates: {len(candidates):4d}   new: {len(fresh):4d}   already filed: {dupes}"
        )

    print()
    if not args.file:
        print(f"DRY RUN — {total_new} would be filed. Re-run with --file to write.")
        print()
        for name, candidates in sources.items():
            for candidate in candidates[:2]:
                print(f"  [{name}] {candidate['what'][:110]}")
                print(f"           evidence: {candidate['evidence'][:110]}")
        return 0

    from divineos.core.success_ledger import EvidenceRequiredError, record_success

    filed = 0
    refused = 0
    for name, candidates in sources.items():
        for candidate in candidates:
            if candidate["evidence"] in already:
                continue
            try:
                record_success(
                    candidate["what"],
                    evidence=candidate["evidence"],
                    yielded=candidate["yielded"],
                    goal=candidate["goal"],
                    goal_met=candidate["goal_met"],
                )
                filed += 1
            except (EvidenceRequiredError, ValueError) as exc:
                refused += 1
                print(f"  refused ({name}): {exc}")

    print(f"filed: {filed}   refused by the ledger: {refused}   already present: {total_skipped}")
    print()
    print(
        "Every entry carries its source inside the evidence field. The "
        "correction-derived\nwins are resolutions of faults already counted on "
        "the other side of the page,\nnot an independent tally — read the split, "
        "never the total alone."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
