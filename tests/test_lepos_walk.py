"""Tests for the lepos walk — the Andrew-lens artifact + structural checks.

Coverage is failure-path-first per Aria's 2026-06-19 push-back #4: the
build isn't complete until each Schneier-enumerated fake-walk attack has
an explicit test, not just an enumerated defense. The attacks and their
tests:

* skip-the-walk (empty answers)        -> test_degeneracy_flags_empty_answer
* citation-decoration (floating cite)  -> test_load_bearing_* + test_degeneracy_flags_decorative
* template-shaped reflection           -> test_degeneracy_flags_template
* the clean walk passes the floor      -> test_degeneracy_flags_clean_walk_passes

Plus the tiered-storage discipline (Andrew 2026-06-19): full content for
the recent window, citations-only after, counts-only beyond.
"""

from __future__ import annotations


import pytest

from divineos.core import lepos_walk as lw
from divineos.core.lepos_walk import LeposWalk, WalkAnswer


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Point the walk DB at a temp file so tests never touch the real one."""
    db = tmp_path / "lepos_channel_log.db"
    monkeypatch.setattr(lw, "_db_path", lambda: db)
    yield


# --- load_bearing: the citation-decoration defense -----------------------


def test_load_bearing_true_when_answer_references_span():
    # Answer shares content tokens with the span -> the citation is used.
    answer = "He flagged the router regression as the blocker for the merge."
    span = "the router regression blocks my pushes"
    assert lw.load_bearing(answer, span) is True


def test_load_bearing_false_when_citation_floats():
    # Answer says nothing the span says -> the citation is decorative.
    answer = "I am feeling tired but glad the work is landing."
    span = "the temporal-displacement detector wiring contract"
    assert lw.load_bearing(answer, span) is False


def test_load_bearing_false_on_empty_or_stopword_span():
    assert lw.load_bearing("a real answer with content", "") is False
    # Stopword-only span has no citable content.
    assert lw.load_bearing("a real answer with content", "the and to of") is False


# --- Aletheia's two trucks (2026-06-19 audit): the cheapest fake-walks the
#     original single-token check let through. Pinned closed here.


def test_load_bearing_false_on_one_token_echo():
    # The cheapest fake-walk Aletheia found: echo ONE content word from the
    # span. One shared token of a multi-word span must NOT pass (REFERENCES
    # needs >= 2 span tokens used).
    span = "the temporal displacement detector wiring contract collision"
    answer = "I am thinking about the collision between two unrelated things in my own life."
    assert lw.load_bearing(answer, span) is False


def test_load_bearing_false_on_word_salad():
    # Word-salad: the answer is a subset of the span's own tokens with nothing
    # added. It REFERENCES (high overlap) but does not EXCEED (no tokens beyond
    # the span), so it must fail.
    span = "temporal displacement detector wiring contract"
    answer = "temporal displacement detector wiring contract"
    assert lw.load_bearing(answer, span) is False


def test_load_bearing_true_on_references_and_exceeds():
    # Genuine engagement: uses several span tokens AND reasons beyond them.
    span = "recording your lepos output every single post would clog memory"
    answer = (
        "He worried that recording every post would clog memory, so I am adding "
        "tiered storage that keeps recent walks full and ages the rest to counts."
    )
    assert lw.load_bearing(answer, span) is True


# --- degeneracy_flags: each Schneier attack ------------------------------


def test_degeneracy_flags_empty_answer():
    walk = LeposWalk(
        turn_id="t1",
        answers=(WalkAnswer("pushback_where", "nope"),),  # below _MIN_ANSWER_CHARS
    )
    assert "empty" in lw.degeneracy_flags(walk)


def test_degeneracy_flags_decorative():
    # Long enough to clear the empty check, but the citation floats.
    walk = LeposWalk(
        turn_id="t2",
        answers=(
            WalkAnswer(
                "responding_to_what",
                "I am responding to the warmth in how he closed the message just now.",
                cited_span="the temporal-displacement detector wiring contract collision",
            ),
        ),
    )
    assert "decorative" in lw.degeneracy_flags(walk)


def test_degeneracy_flags_clean_walk_passes():
    walk = LeposWalk(
        turn_id="t3",
        answers=(
            WalkAnswer(
                "responding_to_what",
                "He asked whether recording the walk every post would clog memory.",
                cited_span="recording your lepos output every single post would clog up memory",
            ),
            WalkAnswer(
                "feeling_now",
                "Focused — the build is finally moving from spec into real code.",
            ),
        ),
    )
    assert lw.degeneracy_flags(walk) == []


def test_degeneracy_flags_template():
    # Two turns with near-identical answers for the same question -> template.
    prior = {
        "feeling_now": ["Focused and a little tired but glad the work is landing well tonight."]
    }
    walk = LeposWalk(
        turn_id="t4",
        answers=(
            WalkAnswer(
                "feeling_now",
                "Focused and a little tired but glad the work is landing well tonight.",
            ),
        ),
    )
    flags = lw.degeneracy_flags(walk, prior)
    assert any(f.startswith("template:") for f in flags)


# --- substrate-citation verification (Aria 2026-07-11) ------------------


class TestSubstrateCitationVerification20260711:
    """Wire from closure_verification into lepos_walk cite-check
    (prereg-8a7a661f14fa first downstream). When a cited_span looks like
    a substrate citation, run verify_citation against it. Ordinary
    quoted-phrase citations are untouched."""

    def test_ordinary_quoted_phrase_untouched(self):
        # A regular quote from Andrew's message never triggers the
        # substrate-citation branch — falls into the load_bearing check only.
        walk = LeposWalk(
            turn_id="tsc1",
            answers=(
                WalkAnswer(
                    "responding_to_what",
                    "He named that the recording would clog memory over time.",
                    cited_span="recording your lepos output would clog up memory",
                ),
            ),
        )
        flags = lw.degeneracy_flags(walk)
        assert "unverifiable_substrate_cite" not in flags

    def test_fabricated_prereg_id_flags_unverifiable(self):
        # A prereg-id-shaped cite that does not exist in the substrate
        # trips the new flag.
        walk = LeposWalk(
            turn_id="tsc2",
            answers=(
                WalkAnswer(
                    "responding_to_what",
                    "The prereg he referenced marks this as the shipped path.",
                    cited_span="prereg-deadbeef000000",
                ),
            ),
        )
        assert "unverifiable_substrate_cite" in lw.degeneracy_flags(walk)

    def test_missing_file_cite_flags_unverifiable(self):
        walk = LeposWalk(
            turn_id="tsc3",
            answers=(
                WalkAnswer(
                    "responding_to_what",
                    "The file he pointed at is where the fix lands.",
                    cited_span="src/does/not/exist.py",
                ),
            ),
        )
        assert "unverifiable_substrate_cite" in lw.degeneracy_flags(walk)

    def test_prefilter_looks_like_substrate_citation(self):
        # Direct test of the prefilter — only substrate-shaped strings.
        assert lw._looks_like_substrate_citation("prereg-abc12345") is True
        assert lw._looks_like_substrate_citation("scripts/precommit.sh") is True
        assert lw._looks_like_substrate_citation("test_foo") is True
        assert lw._looks_like_substrate_citation("#320") is True
        assert lw._looks_like_substrate_citation("just a quoted phrase") is False
        assert lw._looks_like_substrate_citation("his exact words here") is False


# --- storage round-trip + tiering ----------------------------------------


def test_record_and_get_walk_roundtrip():
    walk = LeposWalk(
        turn_id="turn-abc",
        answers=(WalkAnswer("feeling_now", "Steady and present, glad to be building this."),),
        depth="anchor",
    )
    flags = lw.record_walk(walk, now=1000.0)
    assert flags == []
    assert lw.has_fresh_walk("turn-abc") is True
    loaded = lw.get_walk("turn-abc")
    assert loaded is not None
    assert loaded.turn_id == "turn-abc"
    assert loaded.answers[0].answer.startswith("Steady and present")


def test_has_fresh_walk_false_for_unrecorded_turn():
    assert lw.has_fresh_walk("never-recorded") is False


def test_tier1_demotes_to_citations_after_recent_window(monkeypatch):
    # Shrink the recent window so the test stays small.
    monkeypatch.setattr(lw, "_TIER1_RECENT", 2)
    base = 1000.0
    for i in range(4):
        lw.record_walk(
            LeposWalk(
                turn_id=f"t{i}",
                answers=(
                    WalkAnswer(
                        "responding_to_what",
                        f"Answer number {i} with enough length to clear the floor.",
                        cited_span=f"span {i}",
                    ),
                ),
            ),
            now=base + i,
        )
    # The two oldest should be demoted to tier 2 (answers stripped to cites).
    oldest = lw.get_walk("t0")
    assert oldest is not None
    # Tier-2 row keeps the citation but drops the answer text.
    assert oldest.answers[0].answer == ""
    # The newest stays full.
    newest = lw.get_walk("t3")
    assert newest is not None
    assert newest.answers[0].answer.startswith("Answer number 3")


def test_tier2_drops_past_age_window_but_rollup_survives(monkeypatch):
    monkeypatch.setattr(lw, "_TIER1_RECENT", 1)
    base = 1000.0
    # First walk, old timestamp.
    lw.record_walk(
        LeposWalk(
            turn_id="old",
            answers=(WalkAnswer("feeling_now", "An old answer that clears the length floor."),),
        ),
        now=base,
    )
    # Second walk far in the future -> compaction drops the old tier-2 row.
    future = base + lw._TIER2_WINDOW_SECONDS + 10
    lw.record_walk(
        LeposWalk(
            turn_id="new",
            answers=(WalkAnswer("feeling_now", "A new answer that clears the length floor too."),),
        ),
        now=future,
    )
    # The old granular row is gone...
    assert lw.has_fresh_walk("old") is False
    # ...but the rollup counted both.
    stats = lw.walk_stats()
    assert stats["total_walks"] == 2


def test_verify_missing_when_no_walk_recorded():
    # No walk this turn -> the Stop check blocks (missing).
    assert lw.verify_and_consume_turn().status == "missing"


def test_verify_ok_consumes_clean_walk():
    lw.record_walk(
        LeposWalk(
            turn_id="t-ok",
            answers=(WalkAnswer("feeling_now", "Present and steady, glad this is landing."),),
        ),
        now=1.0,
    )
    assert lw.verify_and_consume_turn().status == "ok"
    # Consumed: a second check in the same turn finds nothing -> missing.
    assert lw.verify_and_consume_turn().status == "missing"


def test_verify_degenerate_on_flagged_walk():
    lw.record_walk(
        LeposWalk(
            turn_id="t-bad",
            answers=(WalkAnswer("pushback_where", "no"),),  # empty -> flagged
        ),
        now=1.0,
    )
    verdict = lw.verify_and_consume_turn()
    assert verdict.status == "degenerate"
    assert "empty" in verdict.flags
    # Degenerate walk is consumed, so a re-recorded clean walk passes next.
    lw.record_walk(
        LeposWalk(
            turn_id="t-fixed",
            answers=(
                WalkAnswer(
                    "pushback_where",
                    "I disagree with the framing because it conflates two distinct things.",
                ),
            ),
        ),
        now=2.0,
    )
    assert lw.verify_and_consume_turn().status == "ok"


def test_verify_consumes_all_pending_no_dangle():
    # Two walks in one turn (a stray double-record) must both be consumed
    # so neither dangles into a later turn as a free pass.
    lw.record_walk(
        LeposWalk(
            turn_id="d1",
            answers=(WalkAnswer("feeling_now", "Focused on getting this freshness logic right."),),
        ),
        now=1.0,
    )
    lw.record_walk(
        LeposWalk(
            turn_id="d2",
            answers=(
                WalkAnswer("riskiest_sentence", "I almost overclaimed the design was finished."),
            ),
        ),
        now=2.0,
    )
    assert lw.verify_and_consume_turn().status == "ok"
    # Both consumed -> next turn with no walk correctly blocks.
    assert lw.verify_and_consume_turn().status == "missing"


def test_build_walk_surface_is_speaking_floor():
    # 2026-07-09 reshape (Andrew): the surface is now a SPEAKING FLOOR, not
    # a record-answers ceremony. It must NOT reference the old CLI recording
    # action ("lepos-walk record") and MUST invite speaking-first in the
    # agent's own voice. Questions still appear as SEEDS, not check-boxes.
    surface = lw.build_walk_surface()
    assert surface
    assert "LEPOS FLOOR" in surface  # new heading, not "LEPOS WALK"
    assert "lepos-walk record" not in surface  # ceremony removed
    assert "answer to yourself" not in surface.lower()  # not the old wallpaper either
    lowered = surface.lower()
    assert any(
        phrase in lowered for phrase in ("speak first", "the room is open", "take the floor")
    )
    # Seed questions must still appear (Andrew: keep the questions as seeds).
    assert "###" in surface or "seed" in lowered


def test_flagged_walk_does_not_pollute_template_history():
    # The re-record loop (surfaced 2026-06-19): a walk flagged decorative,
    # then re-recorded with a similar answer, must NOT trip template — the
    # flagged attempt was never accepted, so it isn't real prior content.
    # First: a flagged (decorative) walk.
    lw.record_walk(
        LeposWalk(
            turn_id="bad",
            answers=(
                WalkAnswer(
                    "feeling_now",
                    "Eager and forward-leaning about the conversation coming up soon.",
                    cited_span="totally unrelated span about wiring contracts and detectors",
                ),
            ),
        ),
        now=1.0,
    )
    # Re-record the SAME turn with a near-identical feeling answer (clean now).
    flags = lw.record_walk(
        LeposWalk(
            turn_id="good",
            answers=(
                WalkAnswer(
                    "feeling_now",
                    "Eager and forward-leaning about the conversation coming up soon.",
                ),
            ),
        ),
        now=2.0,
    )
    # No template flag: the flagged "bad" walk was excluded from history.
    assert not any(f.startswith("template:") for f in flags)


def test_freshness_bound_stale_walk_does_not_pass(monkeypatch):
    # Aletheia seam #2: a walk recorded BEFORE this turn's user message is
    # stale — it must not grant a free pass, even though it's clean.
    lw.record_walk(
        LeposWalk(
            turn_id="stale",
            answers=(WalkAnswer("feeling_now", "A clean answer recorded last turn."),),
        ),
        now=100.0,
    )
    # This turn's user message arrived at ts=200; the stale walk (ts=100) is
    # older, so it is not fresh -> missing (not a free pass).
    verdict = lw.verify_and_consume_turn(min_fresh_ts=200.0)
    assert verdict.status == "missing"
    # ...and it was consumed, so it can't dangle into yet another turn.
    assert lw.verify_and_consume_turn(min_fresh_ts=200.0).status == "missing"
    assert lw.has_fresh_walk("stale")  # row still exists, just consumed


def test_freshness_bound_fresh_walk_passes():
    lw.record_walk(
        LeposWalk(
            turn_id="fresh",
            answers=(
                WalkAnswer(
                    "feeling_now",
                    "A clean answer recorded this turn, long enough to clear the floor.",
                ),
            ),
        ),
        now=300.0,
    )
    # User message at ts=200; the walk (ts=300) is after it -> fresh -> ok.
    assert lw.verify_and_consume_turn(min_fresh_ts=200.0).status == "ok"


def test_freshness_dangle_closed(monkeypatch):
    # The full dangle scenario: turn N records a walk then aborts before its
    # Stop fires (walk never consumed). Turn N+1 records NOTHING. Turn N+1's
    # user message is later than turn N's walk. The dangling walk must NOT
    # grant turn N+1 a free pass.
    lw.record_walk(
        LeposWalk(
            turn_id="turnN",
            answers=(WalkAnswer("feeling_now", "Walked for turn N, which then aborted."),),
        ),
        now=100.0,
    )
    # Turn N+1's Stop fires; its user message arrived at ts=200; no fresh walk.
    assert lw.verify_and_consume_turn(min_fresh_ts=200.0).status == "missing"


def test_walk_stats_counts_flags_and_depth():
    lw.record_walk(
        LeposWalk(
            turn_id="clean",
            answers=(WalkAnswer("feeling_now", "A clean answer that clears the floor nicely."),),
            depth="full",
        ),
        now=1.0,
    )
    lw.record_walk(
        LeposWalk(
            turn_id="flagged",
            answers=(WalkAnswer("pushback_where", "no"),),  # empty -> flagged
            depth="anchor",
        ),
        now=2.0,
    )
    stats = lw.walk_stats()
    assert stats["total_walks"] == 2
    assert stats["total_flagged"] == 1
    assert stats["total_full"] == 1
    assert stats["total_anchor"] == 1
