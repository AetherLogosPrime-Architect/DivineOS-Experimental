"""Working the gate to the end must not return you to its opening message.

2026-08-17. `gate_status()` answers (blocked, message) and returns (False, "")
in TWO different situations:

  1. no reach check was ever opened
  2. a check was opened and every one of its artifacts was disposed

reach-check-doorman.sh treated any not-blocked as case 1 and fell through to
"REACH-CHECK -- I am about to write ... without having asked what already
exists", exit 7, block. So the sequence was:

    divineos learn ...   -> "you have not reached"
    divineos reach open  -> 3 artifacts
    divineos learn ...   -> "REACH CHECK OPEN, you have not looked"
    (open all 3, dispose all 3 with evidence)
    divineos learn ...   -> "you have not reached"        <-- back to the top

`divineos learn` had no reachable state. Not a wrong threshold and not a wrong
message: a MISSING STATE. The gate could represent "you owe a look" and "you
are looking" and had no representation for "you looked, and you are done."

The same wall the read-gate hit hours earlier, and the sentence that gate
carries in its own text -- a gate whose cure sits behind itself is a wall --
applied to the gate that quotes it.

WHY THE WINDOW EXPIRES. satisfied_recently is time-bounded rather than
permanent: one reach check in May must not authorise every write in August.
The window matches verify-before-build's 30 minutes on purpose -- two gates
asking "did you look, recently" with two different definitions of recently is
a second thing to remember, and remembering is what these exist to not rely on.
"""

from __future__ import annotations

import time

import pytest

from divineos.core import reach_check as R


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Point the reach tables at a scratch DB so real history is untouched."""
    import divineos.core.reach_check as mod

    db = tmp_path / "reach.db"
    monkeypatch.setattr(mod, "_get_connection", lambda: __import__("sqlite3").connect(db))
    R.init_reach_tables()
    return db


def _check_with(store, dispositions, disposed_ages_s):
    """Insert one check whose items carry the given dispositions/ages."""
    import sqlite3

    now = time.time()
    conn = sqlite3.connect(store)
    conn.execute(
        "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?,?,?)",
        ("chk-1", "a symptom", now - 3600),
    )
    for i, (d, age) in enumerate(zip(dispositions, disposed_ages_s, strict=True)):
        conn.execute(
            "INSERT INTO reach_items "
            "(item_id, check_id, artifact, origin, disposition, reason, evidence, disposed_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                f"ri-{i}",
                "chk-1",
                f"cli:thing{i}",
                "cli-registry",
                d,
                "because" if d else None,
                "cmd:x" if d else None,
                (now - age) if d else None,
            ),
        )
    conn.commit()
    conn.close()


class TestTheStateThatWasMissing:
    def test_a_fully_disposed_check_satisfies_the_gate(self, store):
        """The exact case that walled me: everything disposed, moments ago."""
        _check_with(store, ["applied", "not_relevant"], [60, 30])
        ok, why = R.satisfied_recently()
        assert ok is True
        assert "chk-1" in why, "and it must NAME what satisfied it"
        assert "2 artifact" in why

    def test_gate_status_still_reports_not_blocked_there(self, store):
        """Both halves must agree, or the doorman gets contradictory answers."""
        _check_with(store, ["applied"], [60])
        assert R.gate_status()[0] is False
        assert R.satisfied_recently()[0] is True


class TestItDoesNotBecomeABlankCheque:
    def test_a_partially_disposed_check_does_not_satisfy(self, store):
        """One undisposed item means the look is not finished."""
        _check_with(store, ["applied", None], [60, 0])
        assert R.satisfied_recently()[0] is False
        assert R.gate_status()[0] is True, "and the open-items path still blocks"

    def test_an_old_check_goes_stale(self, store):
        """A reach in May must not authorise a write in August."""
        _check_with(store, ["applied"], [R.SATISFIED_WINDOW_SECONDS + 60])
        assert R.satisfied_recently()[0] is False

    def test_the_boundary_is_inside_the_window(self, store):
        _check_with(store, ["applied"], [R.SATISFIED_WINDOW_SECONDS - 5])
        assert R.satisfied_recently()[0] is True

    def test_no_checks_at_all_is_not_satisfied(self, store):
        """The genuine case-1: nothing was ever asked."""
        assert R.satisfied_recently()[0] is False

    def test_a_check_with_no_items_DOES_satisfy(self, store):
        """REVERSED. This test previously asserted the opposite, and was wrong.

        The original reasoning: "zero artifacts disposed is not all artifacts
        disposed." It sounds careful. It rebuilt, inside the repair, the exact
        wall the repair was for -- `reach open` returning NOT FOUND is the gate
        WORKING (prior_art was asked; nothing exists to look at), and the
        doorman answered "you have not reached." I hit it about an hour after
        fixing the original, and it deadlocked every remedy the
        correction-marker gate offers, including the marker-clear itself.

        The test passed the whole time. It was asserting the defect.

        A test written from the same understanding that produced the code is
        the SECOND reading, not the third -- it agrees because it shares the
        assumption. See docs/two_readings_disagree.md, which this instance is
        in. Left as a reversal rather than a deletion so the trace survives.

        Nothing is waved through: a zero-item check means the search ran and
        came back empty. Recency is the only guard it needs, and the staleness
        test below still applies to it.
        """
        # Inserted directly rather than via _check_with, which back-dates
        # opened_at an hour -- fine for disposal-time cases, outside the window
        # for a check judged on when it was OPENED.
        import sqlite3

        conn = sqlite3.connect(store)
        conn.execute(
            "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?,?,?)",
            ("chk-empty", "asked just now", time.time()),
        )
        conn.commit()
        conn.close()

        ok, why = R.satisfied_recently()
        assert ok is True
        assert "nothing existed to open" in why, "and it must say WHY it opened"

    def test_an_old_empty_check_still_goes_stale(self, store):
        """The recency guard has to survive the reversal above.

        Otherwise one NOT-FOUND reach would authorise writes indefinitely,
        which is the blank cheque the original test was reaching for -- it had
        the right worry and put it on the wrong condition.
        """
        import sqlite3

        conn = sqlite3.connect(store)
        conn.execute(
            "INSERT INTO reach_checks (check_id, symptom, opened_at) VALUES (?,?,?)",
            ("chk-old", "asked long ago", time.time() - R.SATISFIED_WINDOW_SECONDS - 60),
        )
        conn.commit()
        conn.close()
        assert R.satisfied_recently()[0] is False


def test_the_doorman_consults_the_satisfied_state():
    """Pin the wiring: the module-level fix is inert if the hook ignores it.

    The defect lived in the hook, not the library, and a library function
    nobody calls would leave the wall standing while the tests went green.
    """
    from divineos.core.prior_art import REPO

    hook = (REPO / ".claude" / "hooks" / "reach-check-doorman.sh").read_text(
        encoding="utf-8", errors="replace"
    )
    assert "satisfied_recently()" in hook, "the doorman must ask"
    # ...and ask BEFORE printing the you-have-not-reached message, otherwise
    # the answer arrives after the block.
    assert hook.index("satisfied_recently()") < hook.index("REACH-CHECK -- I am about")


def test_the_python_body_carries_no_apostrophes():
    """The hook body is a single-quoted shell argument.

    Writing "gate's" into a comment ended the string and bash tried to parse
    python -- and because the broken hook fires on Edit, it then blocked its
    own repair. Cost a detour through PowerShell to unstick. Pinned so the
    next comment does not do it again.
    """
    from divineos.core.prior_art import REPO

    path = REPO / ".claude" / "hooks" / "reach-check-doorman.sh"
    text = path.read_text(encoding="utf-8", errors="replace")
    start = text.index("python3 -c '") if "python3 -c '" in text else text.index("-c '")
    body = text[start:]
    end = body.index("\n' )") if "\n' )" in body else len(body)
    body = body[body.index("'") + 1 : end]
    assert "'" not in body, (
        "an apostrophe inside the python body terminates the shell string; "
        "rephrase (its/that gate) rather than escaping"
    )
