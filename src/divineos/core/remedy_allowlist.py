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
    ("divineos", "recall"),
    ("divineos", "context"),
    ("divineos", "decide"),
    ("divineos", "council"),
    ("divineos", "psf", "mark-done"),
)

#: Verbs that must never appear here, asserted by a test rather than trusted to
#: my memory. If one of these ever matches, this list has stopped being an
#: anti-deadlock measure and become a way around the gates.
FORBIDDEN_HEADS: frozenset[str] = frozenset(
    {"git", "gh", "pytest", "rm", "mv", "cp", "python", "bash", "sh", "npm", "pip"}
)

_LOG = Path.home() / ".divineos" / "remedy_passthrough.log"


def _tokens(command: str) -> list[str]:
    """The command as tokens, with wrappers and assignments already stripped."""
    try:
        from divineos.core.command_parsing import stripped_command

        cleaned = stripped_command(command)
    except Exception:  # noqa: BLE001 — fail toward not-a-remedy, never toward a block
        cleaned = command
    return cleaned.split()


def is_remedy(command: str) -> bool:
    """True when this command is some gate's prescribed exit.

    Fails toward FALSE on any parsing trouble. That direction matters: a false
    negative leaves the calling gate exactly as it behaves today, while a false
    positive would wave something past a gate that meant to stop it.
    """
    if not command or not command.strip():
        return False
    tokens = _tokens(command)
    if not tokens:
        return False
    return any(tuple(tokens[: len(prefix)]) == prefix for prefix in REMEDIES)


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
