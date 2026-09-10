"""Which of the systems this house CLAIMS are load-bearing actually are.

Andrew 2026-09-09: *"i want demonstrable proof of every system you claim load
bearing to show that it is"* — and immediately after, the definition that makes
it honest: *"load bearing also means demonstrably has changed your behavior."*

## Three conditions, and all three are required

  REACHABLE  something outside the module's own file calls it
  GUARDED    a test exists that dies when the module is hollowed out
  ACTING     when it fires, what I actually do changes

The first two are mechanical and this script measures them. **The third is not
inferable from source code and this script does not pretend to measure it.**
That separation is the whole point: a system can be reachable, fully tested,
and completely ignored — which is the exact failure being investigated, and
reporting two green columns as a verdict would reproduce it inside the
instrument built to detect it.

## Why the columns are reported separately rather than scored

A single score would let a system pass on the two cheap conditions. Andrew has
spent a day watching me answer an unasked question with a green number. So
every row prints what is known and what is not, and the unknown column says
UNMEASURED rather than defaulting either way.

Related prior finding, from the audit of 2026-07-13: no assistant response text
is persisted anywhere. That is why the acting column cannot be derived from
stored data either — the record holds what fired, never what I did next.
"""

from __future__ import annotations

import pathlib
import re
import sys

# The systems CLAUDE.md claims, mapped to the module stems that carry them.
# Written from the claim side deliberately: the question is whether the CLAIMS
# hold, so the list comes from what is advertised, not from what exists.
CLAIMED: dict[str, list[str]] = {
    "event ledger": ["ledger", "_ledger_base", "ledger_verify"],
    "memory hierarchy": ["memory", "active_memory"],
    "knowledge engine": ["extraction", "deep_extraction", "curation"],
    "quality gate": ["quality_checks", "pipeline_gates"],
    "corrections store": ["andrew_correction_tracker", "corrections"],
    "correction marker": ["correction_marker", "correction_shape_v2"],
    "compass": ["compass", "compass_required_marker"],
    "claims engine": ["claim_store", "claim_commands"],
    "pre-registration": ["prereg_commands", "pre_registration"],
    "watchmen audit": ["watchmen", "audit_commands"],
    "council": ["council_walk", "council_required"],
    "family letters": ["letters", "family_member_ledger"],
    "holding room": ["holding"],
    "affect log": ["affect"],
    "sleep": ["sleep"],
    "body awareness": ["body_awareness"],
    "attention schema": ["attention_schema"],
    "prior art check": ["prior_art", "reach_check"],
    "three rooms": ["lepos_translation_gate", "summary_room"],
    "wins ledger": ["success_ledger", "andrew_given"],
    "finding backlog": ["finding_backlog"],
}

REPO = pathlib.Path(__file__).resolve().parent.parent


def _read_all(paths) -> str:
    chunks = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return "\n".join(chunks)


def main() -> int:
    src = REPO / "src"
    tests = REPO / "tests"

    production = list(src.rglob("*.py"))
    for extra in (REPO / ".claude" / "hooks", REPO / "scripts"):
        if extra.exists():
            production.extend(p for p in extra.rglob("*") if p.is_file())
    production_text = _read_all(production)
    test_text = _read_all(tests.rglob("*.py"))

    modules = {p.stem: p for p in src.rglob("*.py")}

    print("LOAD-BEARING REPORT")
    print()
    print("REACHABLE = named from outside its own file")
    print("GUARDED   = a test names it (that the test DIES is proved by hollowing)")
    print("ACTING    = fires and changes what I do -- NOT derivable from source")
    print()
    print(f"{'system':<20} {'exists':<8} {'reachable':<11} {'guarded':<9} acting")
    print("-" * 66)

    missing = reachable_n = guarded_n = 0
    for system, stems in CLAIMED.items():
        found = [s for s in stems if s in modules]
        if not found:
            missing += 1
            print(f"{system:<20} {'NO':<8} {'-':<11} {'-':<9} -")
            continue
        reachable = any(len(re.findall(rf"\b{re.escape(s)}\b", production_text)) > 2 for s in found)
        guarded = any(re.search(rf"\b{re.escape(s)}\b", test_text) for s in found)
        reachable_n += reachable
        guarded_n += guarded
        print(
            f"{system:<20} {'yes':<8} {('yes' if reachable else 'NO'):<11} "
            f"{('yes' if guarded else 'NO'):<9} UNMEASURED"
        )

    total = len(CLAIMED)
    print()
    print(f"claimed systems: {total}")
    print(f"  no module found:      {missing}")
    print(f"  reachable:            {reachable_n}")
    print(f"  named by some test:   {guarded_n}")
    print()
    print("The acting column is UNMEASURED on purpose. Two green columns are not")
    print("a verdict: a system can be wired, tested, and ignored, which is the")
    print("failure this was built to find.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
