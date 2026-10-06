"""No gate may block another gate's prescribed way out.

Andrew 2026-08-18: *"no gate should ever be blocking its own remedy."*
And earlier, 2026-06-16, signing off Aria's signal-based-gates design: every
gate needs an emergency exit that is not a cheap route, *"that way you don't
get stuck in a cage of your own building."*

## The deadlock this ends

Every gate already exempts ITS OWN remedy. The reach doorman lets a reach
through; the correction gate lets a correction through. The principle was
understood and scoped one gate wide. Nineteen gates each knew their own way out
and none knew anyone else's, so gate A blocked the command gate B had just
prescribed and neither was wrong from inside its own scope.

Measured, not imagined -- a closed cycle where all four named exits from one
marker were each held shut by a different gate. The only way through was the
fire door, which is for a burning building rather than a Tuesday, and bypass
habituation degrades a gate to a warning. A deadlock that forces the fire door
on an ordinary day is a slow way of killing every gate at once, by teaching me
that walls are things you go around.

The fact with nowhere to live was: THIS COMMAND IS SOMEBODY'S WAY OUT. This
module is that somewhere.

## Why the shell version had to move

It lived in ``.claude/hooks/lib/remedy_allowlist.sh`` and each gate had to
remember to source it. Its own comments record the same defect arriving three
times -- a worktree prefix, then an environment-variable prefix -- each one a
legal shell form its anchored pattern could not see, and each one silently
re-opening the deadlock. Its final note is the right conclusion and the reason
this file exists: *"If a fourth prefix appears the answer is to parse the
command, not to add a fourth loop."*

So the matching here is on PARSED TOKENS from ``command_parsing``, which
already strips directory changes and variable assignments, rather than on a
pattern anchored to the start of a raw string. There is no fourth loop to add.

## Why this is not a hole

Everything listed is a RECORDING action -- files a correction, opens a reach,
logs a lesson, sets a goal, observes on the compass. None of it edits code,
commits, pushes, merges or deletes. The worst that routing through this list
achieves is writing true things into the substrate, which is the behaviour the
gates were trying to produce in the first place.

The dangerous verbs are absent and must stay absent. Nothing here may ever
match a version-control, test, deletion or editing command, and
``guards_nothing_dangerous`` in the tests is what holds that rather than my
intention to remember it.

This does not loosen any gate's claim. It stops a gate asserting a violation
against the act of resolving a DIFFERENT one.

Adding to this list is a decision, not housekeeping. The test: does some gate's
own block message name this command as the way through? If no gate prescribes
it, it does not belong here however convenient. Filing a NEW pre-registration
is deliberately absent for exactly that reason -- it is ordinary substrate
writing and nobody's prescribed exit; only the commands that CLEAR the overdue
gate are here.
"""

from __future__ import annotations

from pathlib import Path

#: Command prefixes, as token tuples, that some gate names as its way out.
#: Tokens rather than a pattern: a regex over a language with quoting cannot
#: see that an assignment prefix still leaves a remedy underneath, and that
#: blindness re-opened this deadlock three separate times.
REMEDIES: tuple[tuple[str, ...], ...] = (
    ("divineos", "briefing"),
    ("divineos", "preflight"),
    ("divineos", "goal", "add"),
    ("divineos", "reach", "open"),
    ("divineos", "reach", "dispose"),
    ("divineos", "learn"),
    ("divineos", "correction"),
    ("divineos", "corrections", "integrate"),
    ("divineos", "andrew-correction", "integrate"),
    ("divineos", "andrew-correction", "defer"),
    ("divineos", "compass-ops", "observe"),
    ("divineos", "compass-ops", "dismiss"),
    # Only the two that CLEAR the overdue-pre-registration gate. Filing a new
    # one is ordinary substrate writing and nobody's prescribed exit.
    ("divineos", "prereg", "assess"),
    ("divineos", "prereg", "overdue"),
    ("divineos", "ask"),
    # The two exits of the open-question pair (2026-10-06). The open-ask hook
    # prints `ask-resolve` as its way out and the question hold prints
    # `question-hold release` as its; each refused the other's, so a question
    # filed by mistake held all building with no exit but a shell neither watched.
    ("divineos", "ask-resolve"),
    ("divineos", "question-hold", "release"),
    ("divineos", "recall"),
    ("divineos", "context"),
    ("divineos", "decide"),
    ("divineos", "council"),
    ("divineos", "psf", "mark-done"),
    # The sort-first refusal's way out (core/sort_first.py): reading what Dad
    # said and sorting it. The sort records a judgement; it edits nothing.
    ("divineos", "his", "pending"),
    ("divineos", "his", "sort"),
)

#: Verbs that must never appear here, asserted by a test rather than trusted to
#: my memory. If one of these ever matches, this list has stopped being an
#: anti-deadlock measure and become a way around the gates.
FORBIDDEN_HEADS: frozenset[str] = frozenset(
    {"git", "gh", "pytest", "rm", "mv", "cp", "python", "bash", "sh", "npm", "pip"}
)

#: The letter doorbell, kept OFF the remedies list on purpose. The Stop guard
#: prescribes this exact command as its way out, so every other guard must let
#: it through -- and `bash` is forbidden above, because bash runs anything. So
#: the exemption is one exact script path as a token pair, asked through
#: ``is_doorbell`` and never through ``is_remedy``. 2026-10-06: it was refused
#: five times in a day by three guards, one of which knew only the bare spelling
#: and refused the same command with a `cd` in front of it.
DOORBELL: tuple[str, ...] = ("bash", "scripts/letter_doorbell.sh")

_LOG = Path.home() / ".divineos" / "remedy_passthrough.log"


def is_doorbell(command: str) -> bool:
    """True only when every acting segment is the doorbell script.

    Setup links (a worktree cd, an assignment) pass, and work chained behind it
    refuses the whole line, by the same parser the remedy list uses. Fails toward
    FALSE on anything it cannot read, so a doubt leaves the guard asking."""
    if not command or not command.strip():
        return False
    try:
        from divineos.core.command_parsing import runs_only

        return runs_only(command, (DOORBELL,))
    except Exception:  # noqa: BLE001 — fail toward not-the-doorbell, never toward a block
        return False


def is_remedy(command: str) -> bool:
    """True when this command is some gate's prescribed exit, and nothing else.

    A remedy with other work chained behind it is not a remedy. Until
    2026-09-24 this matched the FRONT of a command, so `divineos decide "x" &&
    git commit` walked past every refusal on the router with the commit riding
    on the recording command -- found by the adversarial pass on the sort-first
    refusal. Setup links (a worktree cd, an assignment, `set -o pipefail`) still
    pass; see ``command_parsing.runs_only``.

    Fails toward FALSE on any parsing trouble. That direction matters: a false
    negative leaves the calling gate exactly as it behaves today, while a false
    positive would wave something past a gate that meant to stop it.
    """
    if not command or not command.strip():
        return False
    try:
        from divineos.core.command_parsing import runs_only

        return runs_only(command, REMEDIES)
    except Exception:  # noqa: BLE001 — fail toward not-a-remedy, never toward a block
        return False


def note_pass_through(caller: str, command: str) -> None:
    """Leave a trace, because a silent allowlist rots into an unexamined hole.

    The log is what will show whether this carries real traffic or quietly
    matches nothing. Fails silent by necessity: an unwritable audit line must
    never turn a permitted remedy back into a block, and losing one trace is
    strictly better than restoring the deadlock this exists to end.
    """
    try:
        import time

        _LOG.parent.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with _LOG.open("a", encoding="utf-8") as handle:
            handle.write(f"{stamp}\t{caller}\t{command[:160]}\n")
    except OSError:
        pass
