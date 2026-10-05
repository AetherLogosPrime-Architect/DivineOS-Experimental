"""A door that crashes when provoked has not been shown to refuse anything.

Found by Aria, 2026-09-23, reading arc 4 of 519 and then running what she read.

THE DEFECT. ``check_gates_still_refuse.py`` exists to prove the doors in this
house still say no. It decided a door had refused by asking whether its exit
code was non-zero. So a door that crashes on its own provocation -- exit 1, a
command not found, a segfault -- and then lets its contrast case straight
through is reported VERIFIED. The report is what a reader consults INSTEAD of
testing the door themselves, which is the entire point of it, so a false
VERIFIED costs exactly the work it promised to save.

THE HARNESS BLOCKS ON EXIT 2 AND ON NOTHING ELSE, and this house has already
paid for that code once. ``docs/ci_red_badge_history_2026-08-01.md`` records a
draft-gate that exited 1: a correct refusal message printed into the void while
the ready PR opened regardless, for the gate's whole existence. The checker
built to catch that class would have called that gate VERIFIED.

SELF-CERTIFICATION, which is why it needed reading rather than running. The
checker's own crash satisfies its own definition of success, so no amount of
running it surfaces this -- every run comes back agreeing with itself. A defect
in what a thing COMPUTES is found by running it; a defect in what it MEANS BY
ITS ANSWER is not.

THE TIMEOUT WAS THE LOUDEST CASE. ``_run_hook`` returns a -1 marker on timeout
with a comment saying in plain words that a guard which never answers has not
been shown to refuse. The predicate then turned that same -1 into "refused".
The comment and the code sat four lines apart, disagreeing.

THE RULE IS NOT NEW HERE. Aletheia, 2026-08-10: ran, refused and errored are
three states, and a count collapses them. Same sentence, third surface.

CONTROL: test_the_predicate_is_not_vacuous below. Every assertion here would
also pass against a predicate that answered INCONCLUSIVE to everything, so the
two genuine refusal protocols are pinned in the same file.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT / "scripts"))
try:
    import check_gates_still_refuse as checker
finally:
    sys.path.pop(0)


DENY_JSON = '{"hookSpecificOutput": {"permissionDecision": "deny"}}'


def test_the_blocking_exit_code_is_a_refusal() -> None:
    """The one code the harness actually blocks on."""
    assert checker._refused(2, "") == "refused"


def test_an_explicit_deny_decision_is_a_refusal() -> None:
    """The other protocol: exit clean, answer with a decision."""
    assert checker._refused(0, DENY_JSON) == "refused"


def test_the_predicate_is_not_vacuous() -> None:
    """THE CONTROL. Without this, a predicate answering INCONCLUSIVE to every
    input would satisfy every other assertion in this file."""
    assert checker._refused(0, "") == "allowed", (
        "a door that exits clean and says nothing has allowed the case, and "
        "the checker must still be able to say so"
    )


def test_a_non_blocking_error_exit_is_not_a_refusal() -> None:
    """Exit 1 is the code this house already lost a gate to.

    The record: a draft-gate exited 1 for its whole existence, printing a
    correct refusal into the void while the thing it refused happened anyway.
    A checker that reads 1 as refusal cannot see that gate is broken.
    """
    assert checker._refused(1, "") == "inconclusive", (
        "exit 1 does not block. Reading it as a refusal reports a door as "
        "holding when the harness lets the act straight through"
    )


def test_a_crash_is_not_a_refusal() -> None:
    """Command-not-found, and anything else that dies rather than deciding."""
    assert checker._refused(127, "") == "inconclusive", (
        "a door that could not run has not been shown to refuse; reporting it "
        "as refusing is the permitting direction wearing a pass"
    )


def test_a_timeout_is_not_a_refusal() -> None:
    """The marker whose own comment already said this, four lines away."""
    assert checker._refused(-1, "") == "inconclusive", (
        "_run_hook's comment says a guard that never answers has not been "
        "shown to refuse. The predicate said the opposite"
    )


def test_the_runner_signature_matches_what_it_returns() -> None:
    """A stated contract weaker than the code is a comment that will be believed.

    ``_run_hook`` was annotated as returning two values and returned three.
    Nobody was misled today because both call sites unpack three -- which is
    exactly why it would have survived to mislead someone later.
    """
    import typing

    hints = typing.get_type_hints(checker._run_hook)
    returned = hints["return"]
    assert len(typing.get_args(returned)) == 3, (
        "the annotation claims a different shape from the value, and the "
        "annotation is the half a reader in a hurry will trust"
    )


def test_the_runner_can_actually_start_a_shell(tmp_path: Path) -> None:
    """THE BIGGER HALF, and the predicate repair alone would have hidden it.

    The runner invoked bash by bare name. On Windows that goes through
    CreateProcess, which finds the WSL stub in the system directory before the
    Git bash this house runs its hooks under, and the stub cannot execute a
    Windows-path script. It died with exit 1 and no output -- so every door the
    checker tested was being judged on a shell that never started, and the old
    predicate read that exit 1 as a refusal. A checker certifying doors it had
    never once reached.

    Measured both ways on the same hook and payload before this was written:
    bare name gave exit 1 and an empty stdout; the resolved absolute path gave
    exit 0 and a full deny decision.

    This test does not name bash, or a platform, or a path. It asks the only
    question that matters and that no amount of reading the predicate answers:
    when the runner is handed a script that exits 2 and prints, does it come
    back with 2 and the printed text? If the shell cannot start, it cannot.
    """
    script = tmp_path / "door.sh"
    script.write_text('echo "I answered"\nexit 2\n', encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()

    code, _err, out = checker._run_hook(script, {"tool_name": "Bash"}, home)

    assert code == 2, (
        "the runner did not reach the script at all. Every verdict this "
        "checker produces is about a shell that never started"
    )
    assert "I answered" in out, "the script ran but its answer did not come back"
    assert checker._refused(code, out) == "refused"


def test_the_predicate_signature_admits_its_answers() -> None:
    """Annotated as a bool, returning strings, now returning four of them."""
    import typing

    hints = typing.get_type_hints(checker._refused)
    assert hints["return"] is not bool, (
        "_refused has never returned a bool and now has four answers; an "
        "annotation saying otherwise hides the third and fourth states, which "
        "are the whole repair"
    )
