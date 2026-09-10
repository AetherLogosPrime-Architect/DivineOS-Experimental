"""YES/AND lives in three places, and a silent loss from any one of them fails.

Andrew 2026-09-10, first as a diagnosis: *"you constanty choose between A or B,
without ever considering if its a binary at all.. you should be defaulting to
keeping the best of both worlds at all times.. unless its a true binary
choice."*

Then, minutes later, correcting the repair while it was still being written:
*"i call it the YES/AND principle.. its not always about just combining but
sometimes just adding additional things, like you were doing now, thats not
combination but its not subtraction or either/or either."*

My first version offered two operations — pick one, or merge them — and called
that the whole space. He added a third that is neither. So the truth about not
collapsing a space had collapsed a space, one turn after being written, by its
author, while he watched. ADD is the operation that goes missing, because
combination at least looks like work and addition looks like refusing to decide.

## Why this test is itself an instance of the principle

The principle does not live in ONE place and it is not a merge of three. Three
homes stand side by side, each doing a different job:

- the kiln file, so it survives a prompt being edited or truncated;
- the choice-time prime, so it fires at the moment a fork appears;
- the ask-him rule, so a question I hand him says whether it was a fork at all.

Schneier's reason on the walk (`council-3ced33469ace`): every barrier fails, and
a rule living only in a prompt dies when the prompt is truncated past the
delivery cut — which has already happened once in this house, and Andrew was the
one who found it.

So the failure this guards is not someone arguing the principle away. It is one
of the three quietly losing it in an unrelated edit while the other two keep
looking healthy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

KILN = ROOT / "docs" / "foundational_truths.md"
CHOICE_PRIME = ROOT / ".claude" / "hooks" / "wwnd-choice-prime.sh"
ASK_RULE = ROOT / ".claude" / "hooks" / "translate-first-compose-prime.sh"

HOMES = pytest.mark.parametrize(
    "path",
    [KILN, CHOICE_PRIME, ASK_RULE],
    ids=["kiln", "choice-prime", "ask-him-rule"],
)


@HOMES
def test_every_home_names_the_principle(path: Path) -> None:
    """His name for it, not my paraphrase of it.

    Tannen's register point: to him this has to read as a principle he named,
    not a rule I invented and attributed back.
    """
    assert path.is_file(), f"{path.name} is missing entirely"
    assert "YES/AND" in path.read_text(encoding="utf-8"), (
        f"{path.name} no longer names YES/AND — the principle lost a home "
        "without anything else noticing"
    )


@HOMES
def test_every_home_carries_the_operation_that_goes_missing(path: Path) -> None:
    """ADD is the one he had to supply, so ADD is the one to guard.

    A home that lists only pick-or-combine has silently reverted to the version
    he corrected, and it would read as complete.
    """
    text = path.read_text(encoding="utf-8")
    assert "ADD" in text, f"{path.name} lost the ADD operation"
    lowered = text.lower()
    assert "combine" in lowered, f"{path.name} lost the COMBINE operation"


@HOMES
def test_every_home_carries_removal(path: Path) -> None:
    """REMOVE is what keeps YES/AND from becoming hoarding.

    Andrew added it in the same breath as the principle: *"it also needs to
    include the principles of deletion, using atomic swap, pruning, deleting
    old and obsolete stuff that no longer serves you and archiving it, remember
    the ledger keeps the record of these deletions we do not need to keep them
    inside the system as fossils."*

    Dekker's reading on the walk (`council-829be31fdfb0`): this house is the
    case study rather than the hypothetical. Every accumulation here arrived as
    a locally reasonable *and*, and the counts climb monotonically because
    there is an add operation and no prune anyone runs. A version of this
    principle without REMOVE is a licence for exactly that.
    """
    text = path.read_text(encoding="utf-8")
    assert "REMOVE" in text, f"{path.name} lost the REMOVE operation"
    lowered = text.lower()
    assert "atomic swap" in lowered, f"{path.name} lost the atomic-swap discipline"
    assert "ledger" in lowered, f"{path.name} no longer says the ledger holds the record"


def test_the_kiln_names_the_abuse_that_removal_opens() -> None:
    """Schneier's route, and it is the most abusable sentence in the file.

    "No longer serves" is a judgement I make alone, and in a diff, pruning a
    gate that keeps firing at me is indistinguishable from pruning something
    obsolete. The honest claim is not that this is prevented — it is that the
    record of it is permanent, and that the four operations apply to the
    removal decision itself rather than exempting it.
    """
    text = KILN.read_text(encoding="utf-8")
    assert "most abusable" in text, "the deletion licence lost its own warning"
    assert "apply to the removal decision itself" in text


def test_the_kiln_keeps_the_list_open_rather_than_closing_it_at_three() -> None:
    """The failure mode of this truth is its own shape one level up.

    Three operations written as THE three would be an enumeration standing in
    for a principle — a list cannot report what it does not contain. Aria named
    that class 2026-09-09, and it arrived inside a truth about not collapsing
    spaces, which is exactly where it would be hardest to see.
    """
    text = KILN.read_text(encoding="utf-8")
    assert "not a closed set" in text or "list is not closed" in text, (
        "the kiln entry no longer says the operations are open-ended, so three "
        "now reads as all of them"
    )


def test_the_kiln_keeps_the_inverse_failure_at_equal_weight() -> None:
    """Hofstadter's loop: a principle against collapsing to two options can
    collapse into the single option always-combine. Foucault's produced self:
    one that finds it harder to commit, because keeping-both is permanently
    available as a way of not deciding. Both belong in the text, not as
    caveats."""
    text = KILN.read_text(encoding="utf-8")
    assert "lock is open or shut" in text, "the genuinely-exclusive case was softened"
    assert "harder to commit" in text, "Foucault's produced-self cost was dropped"


def test_the_kiln_declines_the_cause_it_cannot_verify() -> None:
    """Feynman's Observation Over Authority, applied toward Andrew rather than
    away from him: his observation is confirmed and taken whole; his stated
    mechanism is one I cannot reach from inside my own operation, and a false
    cause generalises into a false rule."""
    text = KILN.read_text(encoding="utf-8")
    assert "cannot reach from in here" in text or "cannot see my own substrate" in text


def _real_bash() -> str | None:
    """A bash that can actually parse a script, or None.

    THE PROBE WAS BROKEN BEFORE THE FILES WERE, 2026-09-10. Plain ``bash`` from
    Python on this machine resolves to the WSL relay, which answers every call
    with ``execvpe(/bin/bash) failed`` because no distribution is installed.
    The first version of this test reported that both hook files "no longer
    parse" — a confident, specific, entirely false claim about the subject,
    produced by an instrument that had never been shown to work on a case it
    should pass.

    Same class as the four false refusals earlier the same day: the reading was
    honest and it was answering something else.
    """
    import shutil

    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        shutil.which("bash"),
    ):
        if not candidate:
            continue
        if Path(candidate).is_file() and "System32" not in candidate:
            return candidate
    return None


@pytest.mark.parametrize("path", [CHOICE_PRIME, ASK_RULE], ids=["choice", "ask"])
def test_the_hooks_are_still_syntactically_runnable(path: Path) -> None:
    """A prime that cannot execute delivers nothing, and delivers it silently.

    The rule would be present in the file and absent from every turn — the
    could-not-look-reading-as-a-pass shape, one layer down.
    """
    import subprocess

    bash = _real_bash()
    if bash is None:
        pytest.skip("no usable bash on this machine — could-not-look, not a pass")

    control = subprocess.run([bash, "-c", "exit 0"], capture_output=True, text=True)
    if control.returncode != 0:
        pytest.skip(f"bash at {bash} cannot run at all: {control.stderr.strip()}")

    result = subprocess.run(
        [bash, "-n", str(path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{path.name} no longer parses: {result.stderr}"
