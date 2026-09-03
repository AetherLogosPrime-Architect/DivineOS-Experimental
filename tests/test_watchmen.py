"""Tests for the Watchmen external validation module."""

import os

import pytest

from divineos.core.ledger import init_db
from divineos.core.knowledge import init_knowledge_table
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.types import (
    EXTERNAL_ACTORS,
    INTERNAL_ACTORS,
    FindingStatus,
)
from divineos.core.watchmen.store import (
    _validate_actor,
    get_finding,
    get_round,
    list_findings,
    list_rounds,
    resolve_finding,
    submit_finding,
    submit_round,
)
from divineos.core.watchmen.summary import (
    format_watchmen_summary,
    get_watchmen_stats,
    unresolved_findings,
)


@pytest.fixture(autouse=True)
def _watchmen_db(tmp_path):
    """Set up a fresh database for each test."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_watchmen_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── Actor Validation ─────────────────────────────────────────────────


class TestActorValidation:
    def test_external_actors_accepted(self):
        for actor in EXTERNAL_ACTORS:
            assert _validate_actor(actor) == actor

    def test_internal_actors_rejected(self):
        for actor in INTERNAL_ACTORS:
            with pytest.raises(ValueError, match="internal component"):
                _validate_actor(actor)

    def test_system_rejected(self):
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("system")

    def test_pipeline_rejected(self):
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("pipeline")

    def test_empty_actor_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_actor("")

    def test_case_normalization(self):
        assert _validate_actor("GROK") == "grok"
        assert _validate_actor("  User  ") == "user"

    def test_unknown_external_actor_allowed(self):
        # Unknown actors that aren't in INTERNAL_ACTORS are allowed
        result = _validate_actor("new-auditor")
        assert result == "new-auditor"

    def test_unicode_whitespace_does_not_bypass_internal_actor_rejection(self):
        """Audit finding 2026-05-03 round 8: U+00A0 (no-break-space)
        prefix on an internal-actor name slipped past .strip() because
        Python's default .strip() doesn't remove U+00A0. Validator now
        NFKC-normalizes first, which folds U+00A0 to a regular space.
        Without this fix, an LLM copy-pasting from a formatted document
        could file findings as no-break-space + claude and have them
        accepted as external validation -- exactly the self-audit hole
        the rejection exists to prevent.
        """
        bypass_attempts = [
            " claude",  # U+00A0 leading (the canonical bypass)
            "claude ",  # U+00A0 trailing
            "  claude",  # multiple no-break spaces
            " claude",  # U+2009 thin space
            " claude",  # U+202F narrow no-break space
            "claude　",  # U+3000 ideographic space
            " Claude",  # case + unicode whitespace combined
        ]
        for bypass in bypass_attempts:
            with pytest.raises(ValueError, match="internal component"):
                _validate_actor(bypass)

    def test_bare_claude_rejected_as_self_audit_hole(self):
        # Regression: Popper audit 2026-04-16 found that "claude" was in
        # EXTERNAL_ACTORS, which meant the running Claude agent could file
        # self-audits under its own bare name. The bare string must be
        # structurally rejected; disambiguated names remain allowed.
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("claude")
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("Claude")  # case variant
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("  CLAUDE  ")  # whitespace + case

    def test_disambiguated_claude_names_still_allowed(self):
        # External Claude audits must use a disambiguated name so the actor
        # can never collide with the running agent's identity.
        for name in (
            "claude-opus-auditor",
            "claude-sonnet-external",
            "claude-haiku-reviewer",
        ):
            assert _validate_actor(name) == name


class TestReservedExternalVantageShapes:
    """Self-caught 2026-07-17 mid-session: an attempt was made to file
    a self-attested external-vantage CONFIRMS as actor='external-auditor'.
    The warn-and-accept auto-onboard path let it through — no external
    audit ever happened, but the substrate would have recorded one.
    The catch was in-flow, not by structure. The fix (this test locks
    it in) reserves specific external-vantage name-shapes so they can't
    be self-onboarded — they must be explicitly added to EXTERNAL_ACTORS
    via a guardrail-audited edit."""

    def test_external_auditor_reserved_name_rejected(self):
        """The exact name I attempted to self-file under. Now rejects."""
        with pytest.raises(ValueError, match="reserved external-vantage"):
            _validate_actor("external-auditor")

    def test_all_reserved_vantage_shapes_rejected(self):
        """The reserved-names list covers common external-vantage-claim shapes."""
        reserved = [
            "external-auditor",
            "external-reviewer",
            "outside-auditor",
            "third-party-auditor",
            "independent-auditor",
            "external-audit",
            "external-review",
        ]
        for name in reserved:
            with pytest.raises(ValueError, match="reserved external-vantage"):
                _validate_actor(name)

    def test_reserved_name_uppercase_still_rejected(self):
        """Normalization (casefold) applies before the check — uppercase
        variants of reserved names also bounce."""
        with pytest.raises(ValueError, match="reserved external-vantage"):
            _validate_actor("EXTERNAL-AUDITOR")

    def test_reserved_name_with_whitespace_still_rejected(self):
        """Same NFKC normalization guard as the other actor checks."""
        with pytest.raises(ValueError, match="reserved external-vantage"):
            _validate_actor("  external-auditor  ")
        with pytest.raises(ValueError, match="reserved external-vantage"):
            _validate_actor(" external-auditor")

    def test_reserved_names_in_EXTERNAL_ACTORS_would_still_pass(self):
        """The rejection ONLY fires for reserved shapes NOT in the
        allowlist. If the operator explicitly adds one via a
        guardrail-audited edit to EXTERNAL_ACTORS, it should pass —
        the reservation is anti-auto-onboard, not anti-legitimate-use."""
        # Temporarily add external-auditor to the allowlist for this test.
        from divineos.core.watchmen import types as _t

        original = _t.EXTERNAL_ACTORS
        try:
            _t.EXTERNAL_ACTORS = frozenset({*original, "external-auditor"})
            # Also need to patch the reference imported by store.py.
            from divineos.core.watchmen import store as _s

            _s.EXTERNAL_ACTORS = _t.EXTERNAL_ACTORS
            # Now it should pass without raising.
            assert _validate_actor("external-auditor") == "external-auditor"
        finally:
            _t.EXTERNAL_ACTORS = original
            from divineos.core.watchmen import store as _s

            _s.EXTERNAL_ACTORS = original

    def test_non_reserved_unknown_still_warns_and_accepts(self):
        """Regression: the fix ONLY tightens reserved shapes. Legitimate
        onboarding of a new external actor with a different name still
        works via warn-and-accept."""
        assert _validate_actor("new-independent-service") == "new-independent-service"
        assert _validate_actor("some-third-party-tool") == "some-third-party-tool"

    @pytest.mark.parametrize(
        "spelling",
        [
            "external auditor",  # a space where the hyphen was
            "external_auditor",  # an underscore
            "externalauditor",  # run together
            "external--auditor",  # doubled hyphen
            "external-auditor.",  # trailing full stop
            "External Auditor",  # and the same with case, since both fold
        ],
    )
    def test_a_different_separator_does_not_walk_through(self, spelling):
        """THE FIVE THAT WALKED, and the comment above them was wrong about why.

        Aria exercised the guard with eleven spellings on 2026-09-01 -- running
        it, not reading it -- and five went straight past. The body claimed the
        guard stopped the lazy reach and not a determined one. None of these is
        determined. The space is arguably LAZIER than the hyphen: it is what a
        person types first and hyphenates second.

        So the boundary was never lazy-versus-determined. It sat between this
        exact punctuation and any other punctuation, which is the same fault
        the neighbouring branches keep turning up -- asking whether a thing is
        SPELLED like the thing when the question is whether it IS the thing.

        The repair folds separators rather than lengthening the reserved list,
        because a longer list of spellings is the identical fault with more
        entries.
        """
        with pytest.raises(ValueError, match="reserved external-vantage"):
            _validate_actor(spelling)

    def test_the_allowlist_escape_folds_with_the_guard(self):
        """A guard matching on the word whose escape matches on the typography
        would refuse a legitimately-onboarded auditor for writing their own
        name with a space. That is a guard and a permission disagreeing about
        the same name -- the shape Aria found on this branch between the store
        and one of my hooks, one level down."""
        from divineos.core.watchmen import store as _s
        from divineos.core.watchmen import types as _t

        original = _t.EXTERNAL_ACTORS
        try:
            _t.EXTERNAL_ACTORS = frozenset({*original, "external-auditor"})
            _s.EXTERNAL_ACTORS = _t.EXTERNAL_ACTORS
            assert _validate_actor("external auditor") == "external auditor"
        finally:
            _t.EXTERNAL_ACTORS = original
            _s.EXTERNAL_ACTORS = original

    def test_no_live_instruction_prescribes_a_name_the_store_refuses(self):
        """A guard and a prescription must not disagree about the same name.

        Aria, 2026-09-01: one of my own hooks still told its reader to file a
        round with the reserved name as the actor, on the same branch that
        added the refusal. Whoever followed that line got a hard rejection for
        doing exactly what the instructions said, and would have read the guard
        as broken rather than the instruction as stale.

        A note fixes that one line. This is the class: any live instruction
        anywhere in the hooks, scripts or docs that hands somebody a command
        with a reserved actor in it. Historical audit-round records are
        excluded because they are a record of what happened, not an
        instruction, and rewriting them would erase the trace along with the
        text -- Andrew's rule about leaving bad data explained rather than
        erased applies to the archive, not to a live remedy line.
        """
        import re

        from pathlib import Path

        from divineos.core.watchmen.store import RESERVED_EXTERNAL_VANTAGE_NAMES

        repo = Path(__file__).resolve().parent.parent
        pattern = re.compile(
            r"--actor[= ]+['\"]?("
            + "|".join(re.escape(n) for n in sorted(RESERVED_EXTERNAL_VANTAGE_NAMES))
            + ")"
        )
        offenders: list[str] = []
        opened: list[str] = []
        for root in (repo / ".claude", repo / "scripts", repo / "docs"):
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file() or path.suffix not in (".sh", ".py", ".md", ".ps1"):
                    continue
                if "audit_rounds" in path.parts:
                    continue  # a record of what was filed, not an instruction
                text = path.read_text(encoding="utf-8", errors="replace")
                opened.append(path.name)
                for n, line in enumerate(text.splitlines(), 1):
                    if pattern.search(line):
                        offenders.append(f"{path.relative_to(repo)}:{n}: {line.strip()}")

        # THE SCAN MUST NOT PASS HAVING LOOKED NOWHERE (Lamport lens, walked on
        # this test). What I meant: no live instruction anywhere prescribes a
        # refused actor. What the code checks: no match in three named roots and
        # four suffixes. The second claim is strictly smaller and its silence
        # was being read as the first.
        #
        # It is the emitter scan again, one week later and in the same file --
        # that one globbed the hook directory alone, passed, and covered four
        # source-tree callers it never opened. I wrote the docstring about it,
        # then typed a fresh root list from memory and did not apply my own
        # finding to it.
        #
        # This BOUNDS the blindness rather than removing it: a prescription in a
        # filetype I never listed still passes. Deriving the roots from
        # something that cannot drift is a different change, and saying so here
        # keeps this assertion from implying it is solved.
        assert opened, "scan read no files at all -- looked-nowhere is not found-nothing"
        assert "pre-tool-bypass-rate-scan.sh" in opened, (
            "the file that actually carried this defect is outside the scanned set, "
            "so a green run here proves nothing about the place it went wrong"
        )

        assert not offenders, (
            "live instruction(s) prescribe an actor name the store hard-rejects:\n  "
            + "\n  ".join(offenders)
            + "\nFile under the real name of whoever is filing. A prescription the "
            "guard refuses teaches the reader that the guard is broken."
        )

    def test_the_refusal_shows_the_transformation_it_performed(self):
        """Norman's gulf of evaluation, walked on the fold itself.

        The fold closed five bypasses and widened the gap between what a person
        typed and what the message says. Someone writing the word with a space
        used to see themselves in the listed names; now they read seven
        hyphenated names, none of which is their input, and the only available
        reading is that the guard is broken.

        So the message must show the transformation -- what was typed, what it
        folded to, which reserved word it collided with -- and lead with the
        action nearly everyone hitting this needs, which is to file under their
        own name. The allowlist door is right for a rare case and was the only
        door the old message described.
        """
        with pytest.raises(ValueError) as caught:
            _validate_actor("external auditor")
        message = str(caught.value)
        assert "external auditor" in message, "does not echo what was typed"
        assert "externalauditor" in message, "does not show what it folded to"
        assert "external-auditor" in message, "does not name the reserved word it hit"
        assert "whoever is actually filing" in message, (
            "does not give the action the common case needs"
        )

    def test_the_fold_does_not_swallow_names_that_merely_resemble(self):
        """Guard against the fold over-reaching. Dropping separators must not
        turn a distinct name into a reserved one -- if it did, the repair for
        five bypasses would have bought a class of false refusals."""
        for name in (
            "external-auditor-bot",
            "ex-external-auditor",
            "external-auditors",
            "internal-auditor",
        ):
            assert _validate_actor(name) == name

    def test_the_guard_stops_the_lazy_reach_and_not_a_determined_one(self):
        """The limit, made executable instead of left in a council walk.

        Same behaviour as the test above, read from the other side. The one
        above says an unlisted name onboards, which is the feature. This says
        an unlisted name that MEANS external-vantage onboards just the same,
        which is the cost of the feature — a fixed list is a boundary someone
        walks around rather than through.

        Every name below reads as an outside reviewer to any human skimming
        the audit record, and none is on the list. Anyone reaching for the
        obvious word is stopped; anyone willing to pick a synonym is not.

        Kept as a passing test rather than an xfail because these are not
        bugs to be fixed by lengthening the list — lengthening it just moves
        the boundary and the next synonym walks around the new one. What
        holds is the seat declining to type any of them, which no test can
        observe. Schneier lens, council walk on this branch; Aria 2026-08-30
        asked for the claim to live in the code and not only in the review.

        A FIFTH NAME USED TO SIT IN THIS LIST AND IT DID NOT BELONG THERE:
        the reserved word itself with an underscore instead of the hyphen. It
        was filed beside four genuine synonyms, asserted as accepted, and
        called the executable statement of the limit. Aria found it by running
        the guard rather than reading it.

        The four below are DIFFERENT WORDS, and a fixed list genuinely cannot
        reach them. The fifth was the SAME WORD in different typography, which
        the list can reach and now does. Writing them into one list said those
        are the same kind of thing, and they are not — that conflation is the
        fault itself, sitting inside the test written to state the fault's
        boundary honestly. The sentence was not dishonest; it was wrong about
        where its own edge was, in exactly the direction that made the guard
        look better than it was.
        """
        for walkaround in (
            "outside-eyes",
            "reviewer-2",
            "audit-partner",
            "impartial-review",
        ):
            assert _validate_actor(walkaround) == walkaround


# ── Round Submission ─────────────────────────────────────────────────


class TestSubmitRound:
    def test_create_round(self):
        rid = submit_round(actor="grok", focus="Dice coefficient impact audit")
        assert rid.startswith("round-")

    def test_round_with_experts(self):
        rid = submit_round(actor="grok", focus="Round 6", expert_count=25, notes="Full council")
        r = get_round(rid)
        assert r is not None
        assert r.expert_count == 25
        assert r.notes == "Full council"
        assert r.actor == "grok"

    def test_internal_actor_blocked(self):
        with pytest.raises(ValueError, match="internal component"):
            submit_round(actor="system", focus="Self-audit attempt")

    def test_list_rounds(self):
        submit_round(actor="grok", focus="Round 1")
        submit_round(actor="user", focus="Round 2")
        rounds = list_rounds()
        assert len(rounds) == 2
        # Most recent first
        assert rounds[0].focus == "Round 2"


# ── Finding Submission ───────────────────────────────────────────────


class TestSubmitFinding:
    def test_basic_finding(self):
        rid = submit_round(actor="grok", focus="Test audit")
        fid = submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="KNOWLEDGE",
            title="Stemmed overlap still uses min-denominator",
            description="The _compute_stemmed_overlap function was not converted to Dice.",
        )
        assert fid.startswith("find-")

    def test_finding_with_recommendation(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            round_id=rid,
            actor="grok",
            severity="MEDIUM",
            category="ARCHITECTURE",
            title="Magic numbers in relationships.py",
            description="Seven hardcoded thresholds found.",
            recommendation="Replace with constants from constants.py",
            tags=["dice", "thresholds"],
        )
        f = get_finding(fid)
        assert f is not None
        assert f.recommendation == "Replace with constants from constants.py"
        assert "dice" in f.tags

    def test_invalid_round_rejected(self):
        with pytest.raises(ValueError, match="does not exist"):
            submit_finding(
                round_id="nonexistent",
                actor="grok",
                severity="LOW",
                category="KNOWLEDGE",
                title="Test",
                description="Test",
            )

    def test_finding_auto_routes_on_submit(self):
        """2026-07-07: submit_finding auto-invokes route_finding so findings
        don't sit orphaned until an operator remembers to call
        `divineos audit route`. Andrew: 'your will needs to be made into
        structure through this automation.' The finding's status transitions
        from OPEN to ROUTED as part of a successful submit."""
        from divineos.core.watchmen.types import FindingStatus

        rid = submit_round(actor="grok", focus="Test audit for auto-route")
        fid = submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="KNOWLEDGE",
            title="A finding that should auto-route",
            description="Body content sufficient to route to knowledge subsystem.",
        )
        f = get_finding(fid)
        assert f is not None
        # Successful auto-route flips the status from OPEN to ROUTED.
        # If auto-routing failed (fail-soft path), status stays OPEN — but
        # test-environment routing should succeed against the same isolated
        # DB, so any regression that skips the auto-route call will surface
        # here as a stuck OPEN status.
        assert f.status == FindingStatus.ROUTED, (
            f"Finding status expected ROUTED after auto-route on submit; "
            f"got {f.status}. Auto-route wiring in submit_finding may have "
            f"regressed."
        )

    def test_invalid_severity_rejected(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="Invalid severity"):
            submit_finding(
                round_id=rid,
                actor="grok",
                severity="APOCALYPTIC",
                category="KNOWLEDGE",
                title="Test",
                description="Test",
            )

    def test_invalid_category_rejected(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="Invalid category"):
            submit_finding(
                round_id=rid,
                actor="grok",
                severity="LOW",
                category="NONSENSE",
                title="Test",
                description="Test",
            )

    def test_internal_actor_blocked_on_finding(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="internal component"):
            submit_finding(
                round_id=rid,
                actor="assistant",
                severity="LOW",
                category="KNOWLEDGE",
                title="Self-submitted finding",
                description="The OS trying to audit itself.",
            )

    def test_finding_count_incremented(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="LOW",
            category="KNOWLEDGE",
            title="F1",
            description="D1",
        )
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="BEHAVIOR",
            title="F2",
            description="D2",
        )
        r = get_round(rid)
        assert r.finding_count == 2


# ── Listing & Filtering ─────────────────────────────────────────────


class TestListFindings:
    def test_filter_by_severity(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "B", "D")
        high = list_findings(severity="HIGH")
        assert len(high) == 1
        assert high[0].title == "A"

    def test_filter_by_category(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        submit_finding(rid, "grok", "HIGH", "BEHAVIOR", "B", "D")
        knowledge = list_findings(category="KNOWLEDGE")
        assert len(knowledge) == 1

    def test_filter_by_status(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "RESOLVED", "Fixed it")
        open_findings = list_findings(status="OPEN")
        assert len(open_findings) == 0
        resolved = list_findings(status="RESOLVED")
        assert len(resolved) == 1


# ── Resolution ───────────────────────────────────────────────────────


class TestResolveFinding:
    def test_resolve_existing(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        assert resolve_finding(fid, "RESOLVED", "Converted to Dice")
        f = get_finding(fid)
        assert f.status == FindingStatus.RESOLVED
        assert f.resolution_notes == "Converted to Dice"

    def test_resolve_nonexistent(self):
        assert not resolve_finding("nonexistent", "RESOLVED")

    def test_invalid_status(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        with pytest.raises(ValueError, match="Invalid status"):
            resolve_finding(fid, "EXPLODED")

    def test_wont_fix(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "WONT_FIX", "By design")
        f = get_finding(fid)
        assert f.status == FindingStatus.WONT_FIX


# ── Summary & Statistics ─────────────────────────────────────────────


class TestSummary:
    def test_empty_stats(self):
        stats = get_watchmen_stats()
        assert stats["total_findings"] == 0
        assert stats["total_rounds"] == 0

    def test_stats_with_data(self):
        # auto_route=False: this test observes OPEN-status counts, which
        # auto-routing (default) transitions to ROUTED at submit-time.
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D", auto_route=False)
        submit_finding(rid, "grok", "CRITICAL", "BEHAVIOR", "B", "D", auto_route=False)
        submit_finding(rid, "grok", "LOW", "LEARNING", "C", "D", auto_route=False)
        stats = get_watchmen_stats()
        assert stats["total_findings"] == 3
        assert stats["total_rounds"] == 1
        assert stats["by_severity"]["HIGH"] == 1
        assert stats["by_severity"]["CRITICAL"] == 1
        assert stats["open_count"] == 3

    def test_unresolved_ordered_by_severity(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "Low one", "D")
        submit_finding(rid, "grok", "CRITICAL", "BEHAVIOR", "Critical one", "D")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "High one", "D")
        unresolved = unresolved_findings()
        assert unresolved[0]["severity"] == "CRITICAL"
        assert unresolved[1]["severity"] == "HIGH"
        assert unresolved[2]["severity"] == "LOW"

    def test_resolved_not_in_unresolved(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "RESOLVED")
        assert len(unresolved_findings()) == 0

    def test_format_empty(self):
        assert format_watchmen_summary() == ""

    def test_format_with_findings(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        summary = format_watchmen_summary()
        assert "Watchmen" in summary
        assert "high" in summary.lower()


# ── Router ───────────────────────────────────────────────────────────


class TestRouter:
    # These tests exercise route_finding as a standalone operation by
    # submitting a finding then manually invoking the router. They pass
    # auto_route=False so submit_finding does NOT pre-route the finding
    # before the explicit route_finding call — otherwise the router would
    # see status=ROUTED and skip.

    def test_route_to_knowledge(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "MEDIUM",
            "KNOWLEDGE",
            "FTS5 uses AND logic killing recall",
            "The _extract_key_terms function produces space-separated terms that FTS5 treats as implicit AND",
            recommendation="Use _build_fts_query with OR-joined terms",
            auto_route=False,
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "knowledge"
        assert result["id"]  # Got a knowledge_id back

        # Finding should now be ROUTED
        updated = get_finding(fid)
        assert updated.status == FindingStatus.ROUTED

    def test_route_critical_behavior_to_claim(self):
        from divineos.core.watchmen.router import route_finding
        from divineos.core.claim_store import init_claim_tables

        init_claim_tables()

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "CRITICAL",
            "BEHAVIOR",
            "Self-referential evaluation loop",
            "The OS evaluates itself with no external anchor for calibration",
            auto_route=False,
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "claim"
        assert result["id"].startswith("claim-")

    def test_route_learning_to_lesson(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "MEDIUM",
            "LEARNING",
            "Maturity pipeline stalled",
            "75% of knowledge entries stuck at RAW maturity level",
            auto_route=False,
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "lesson"

    def test_skip_already_routed(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "LOW",
            "KNOWLEDGE",
            "Test",
            "Test finding",
        )
        finding = get_finding(fid)
        route_finding(finding)  # First route

        # Try to route again — should skip
        updated = get_finding(fid)
        result = route_finding(updated)
        assert result["action"] == "skipped"

    def test_route_round(self):
        from divineos.core.watchmen.router import route_round

        # auto_route=False on submits so route_round has un-routed
        # findings to work on. Without this, submit_finding pre-routes
        # each and route_round sees status=ROUTED, returning "skipped".
        rid = submit_round(actor="grok", focus="Test round")
        submit_finding(
            rid,
            "grok",
            "HIGH",
            "KNOWLEDGE",
            "Knowledge maturity pipeline stalled at RAW level",
            "Seventy-five percent of knowledge entries remain at RAW maturity with zero promotions observed",
            auto_route=False,
        )
        submit_finding(
            rid,
            "grok",
            "LOW",
            "ARCHITECTURE",
            "Magic numbers scattered across relationship classification",
            "Seven hardcoded threshold values found in the relationship classification module need extraction",
            auto_route=False,
        )
        results = route_round(rid)
        assert len(results) == 2
        routed = sum(1 for r in results if r["action"] != "skipped")
        assert routed >= 1


# ── Self-Trigger Prevention ──────────────────────────────────────────


class TestSelfTriggerPrevention:
    """The three structural guarantees against self-auditing."""

    def test_layer_1_actor_validation(self):
        """Internal actors are rejected at the store level."""
        with pytest.raises(ValueError):
            submit_round(actor="system", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="assistant", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="pipeline", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="divineos", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="hook", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="schedule", focus="Self-audit")

    def test_layer_1_finding_also_validates(self):
        """Even if a round exists, internal actors can't submit findings."""
        rid = submit_round(actor="grok", focus="Legit round")
        with pytest.raises(ValueError):
            submit_finding(
                round_id=rid,
                actor="system",
                severity="HIGH",
                category="KNOWLEDGE",
                title="Self-submitted",
                description="Trying to audit myself",
            )


class TestRecognitionAwareCount:
    """Title-CONFIRMS approvals must not inflate open_issue_count.

    Round/commit-level confirmations arrive as title-prefixed "CONFIRMS …"
    with an empty review_stance (stance requires a reviewed_finding_id, which
    they don't have). The recognition filter must read the title, not just
    the stance column, or approvals accumulate as fake-open issues
    (audit-status reconcile 2026-05-23, decision: read the actor's own
    declaration).
    """

    def test_title_confirms_counts_as_recognition_not_issue(self):
        # auto_route=False: this test observes OPEN-status counts.
        rid = submit_round(actor="aletheia", focus="cross-vantage audit")
        submit_finding(
            round_id=rid,
            actor="aletheia",
            severity="INFO",
            category="ARCHITECTURE",
            title="CONFIRMS — commit abc123 verified across 4 empirical tests",
            description="The fix holds. Approving for merge.",
            auto_route=False,
        )
        stats = get_watchmen_stats()
        assert stats["open_count"] == 1
        assert stats["open_recognition_count"] == 1
        assert stats["open_issue_count"] == 0

    def test_pending_empirical_confirms_stays_an_issue(self):
        rid = submit_round(actor="aletheia", focus="audit")
        submit_finding(
            round_id=rid,
            actor="aletheia",
            severity="LOW",
            category="ARCHITECTURE",
            title="CONFIRMS-PENDING-EMPIRICAL on round shape — needs live verify",
            description="Architecture-sound but not yet run on real input.",
            auto_route=False,
        )
        stats = get_watchmen_stats()
        assert stats["open_recognition_count"] == 0
        assert stats["open_issue_count"] == 1

    def test_real_finding_still_counts_as_issue(self):
        rid = submit_round(actor="grok", focus="audit")
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="INTEGRITY",
            title="Race condition in log_event",
            description="Two threads can fork the hash chain.",
            auto_route=False,
        )
        stats = get_watchmen_stats()
        assert stats["open_issue_count"] == 1
        assert stats["open_recognition_count"] == 0

    def test_recognition_excluded_from_unresolved_surface(self):
        rid = submit_round(actor="aletheia", focus="audit")
        submit_finding(
            round_id=rid,
            actor="aletheia",
            severity="INFO",
            category="ARCHITECTURE",
            title="CONFIRMS — approving the work",
            description="Looks good.",
        )
        # Default surface excludes recognitions; opt-in includes them.
        assert len(unresolved_findings()) == 0
        assert len(unresolved_findings(include_recognitions=True)) == 1


class TestConfirmsAlarmBypass:
    """A HIGH/CRITICAL finding titled CONFIRMS-* must not silently vanish.

    Council codebase-sweep 2026-06-02 (direction #3): the recognition filter
    excludes CONFIRMS-titled findings from open_issue_count, so an adversary
    (or a slip) could hide a real high-severity concern by titling it
    "CONFIRMS-by-design". The suspicious_recognition_count surfaces exactly
    that case so it can never be silently excluded.
    """

    def test_high_severity_confirms_title_is_flagged_suspicious(self):
        # auto_route=False: this test observes OPEN-status counts.
        rid = submit_round(actor="grok", focus="bypass test")
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="INTEGRITY",
            title="CONFIRMS-by-design: this hides a real high-severity problem",
            description="A genuine HIGH concern wearing a recognition title.",
            auto_route=False,
        )
        stats = get_watchmen_stats()
        # Excluded from the issue count by the recognition filter...
        assert stats["open_recognition_count"] >= 1
        # ...but caught by the suspicious surface so it cannot vanish.
        assert stats["suspicious_recognition_count"] >= 1

    def test_low_severity_confirms_title_is_not_suspicious(self):
        rid = submit_round(actor="grok", focus="benign recognition")
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="INFO",
            category="INTEGRITY",
            title="CONFIRMS the fix is sound",
            description="A genuine low-severity recognition — not suspicious.",
        )
        stats = get_watchmen_stats()
        # An INFO CONFIRMS is legitimate recognition, not a hidden alarm.
        assert stats["suspicious_recognition_count"] == 0
