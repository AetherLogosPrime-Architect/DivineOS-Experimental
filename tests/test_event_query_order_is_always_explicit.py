"""No NEW get_events call site may leave the row ordering implicit.

## The class

``get_events`` defaults to ``order="asc"``. A call that passes a limit and
no explicit order therefore receives the OLDEST N rows. While the matching
table holds fewer rows than the limit, ascending and descending return the
same set, so the call site is correct BY ACCIDENT and every test over it
goes green. It turns wrong later, silently, when the table grows past the
limit — with no code change and nobody watching. The code did not drift;
the world grew past it.

This has bitten three times that are on the record, across two functions:

* 2026-06-09, Fable 5 audit: four ``get_events`` callers wanting recent
  events were permanently frozen on the ledger's earliest history. Fixed,
  and the reason was written into ``get_events``' own docstring.
* 2026-07-02, Fable audit findings #2 and #3: the same defect in
  ``search_events``, which had no order parameter at all. Fixed, and
  defended by ``test_fable_finding_2_3_asc_limit``.
* 2026-09-16, the council lens-trace check: it reported walks logged
  seconds earlier as never walked, accusing real work of being fabricated,
  and tightened toward permanently unclearable with every further walk.
  Fixed; pinned by ``test_lens_trace_sees_the_newest_walk``.

Every one of those repairs was per-call-site. Each fixed the instance in
front of it and left the next author free to write the same line again —
and the docstring note did not prevent the third, because nobody rereads a
docstring while writing an ordinary query. A rule you have to recall at the
moment of temptation is the thing that already failed. This test is the
first structure aimed at the CLASS rather than an instance.

## Why a freeze rather than a blanket repair

Thirty existing call sites share the shape and they are NOT all defects —
chain reconstruction and ledger verification genuinely want oldest-first.
Deciding all thirty in one sweep would be guessing at thirty intents, and a
wrong guess here is silent by construction. So this test does the one
unambiguous thing: it freezes the backlog. Existing modules are
grandfathered; a NEW call site that leaves ordering implicit fails
immediately, and the author has to say which end of the table they meant.

The list can only shrink. Removing an entry as each site is triaged is the
work; adding one is what this test exists to stop.
"""

from __future__ import annotations

import ast
import pathlib

# Modules holding call sites that predate this test. Keyed on module rather
# than line number so unrelated edits above them do not churn this list.
#
# Each entry is UNTRIAGED: it means "this existed before the rule", never
# "this is correct". Triaging one means reading what that query actually
# needs, passing the order explicitly, and deleting its line here.
_GRANDFATHERED = {
    "divineos/cli/progress_commands.py",
    "divineos/core/andrew_correction_tracker.py",
    "divineos/core/command_inventory.py",
    "divineos/core/completion_boundary.py",
    "divineos/core/compliance_audit.py",
    "divineos/core/docs_review_tracker.py",
    "divineos/core/enforcement_verifier.py",
    "divineos/core/ledger.py",
    "divineos/core/ledger_verify.py",
    "divineos/core/moral_compass.py",
    "divineos/core/multiplex_panels.py",
    "divineos/core/progress_dashboard.py",
    "divineos/core/structural_promotion_check.py",
    "divineos/event/event_emission.py",
    "divineos/core/consequence_chain/chain.py",
    "divineos/core/family/family_member_ledger.py",
    "divineos/core/knowledge/retrieval.py",
}

# Frozen at the count measured 2026-09-16. It may go DOWN as sites are
# triaged; a rise means a new implicit-order call slipped in inside an
# already-grandfathered module — the one gap a module-level allowlist
# cannot see on its own.
_KNOWN_IMPLICIT_CALL_COUNT = 30


def _repo_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    raise AssertionError("repo root not found — cannot run the sweep")


def _implicit_order_sites() -> list[tuple[str, int]]:
    """Every get_events call passing a limit with no explicit order."""
    src = _repo_root() / "src"
    found: list[tuple[str, int]] = []
    for path in sorted(src.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        rel = path.relative_to(src).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            name = getattr(fn, "attr", None) or getattr(fn, "id", None)
            if name != "get_events":
                continue
            kw = {k.arg for k in node.keywords if k.arg}
            if ("limit" in kw or node.args) and "order" not in kw:
                found.append((rel, node.lineno))
    return found


def test_the_sweep_can_find_anything_at_all():
    """Control. An empty result from the sweep would satisfy the rule below
    for the worst possible reason — a broken probe reading as a clean repo.
    The grandfathered set is non-empty and known, so the sweep must find it.
    """
    modules = {rel for rel, _ in _implicit_order_sites()}

    assert modules & _GRANDFATHERED, (
        "The sweep found none of the known pre-existing call sites. That is "
        "a broken probe, not a clean repository — every assertion below "
        "would pass vacuously. Check the AST walk before trusting a green run."
    )


def test_no_new_call_site_leaves_row_ordering_implicit():
    offenders = {rel for rel, _ in _implicit_order_sites()}
    new = sorted(offenders - _GRANDFATHERED)

    assert not new, (
        "These modules call get_events with a limit and no explicit order. "
        "get_events returns the OLDEST rows by default, so such a call is "
        "correct only while the table stays under the limit and turns wrong "
        "later with no code change. Pass order='desc' for recent rows, or "
        "order='asc' deliberately where oldest-first is what you mean: "
        f"{new}"
    )


def test_the_untriaged_backlog_does_not_grow():
    """The grandfathered modules are untriaged, not blessed. This pins the
    call COUNT so a new implicit-order query cannot hide inside a module
    already on the list.
    """
    count = len(_implicit_order_sites())

    assert count <= _KNOWN_IMPLICIT_CALL_COUNT, (
        f"{count} get_events calls now leave ordering implicit, up from "
        f"{_KNOWN_IMPLICIT_CALL_COUNT}. A new one was added inside a module "
        "already on the grandfathered list. Pass the order explicitly."
    )
