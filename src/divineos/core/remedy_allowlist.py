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

import re
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
    # The overdue block's own third exit: it prints `prereg reviewing` as the way
    # to go get evidence, and the build-flow gate then asked for council paperwork
    # that the overdue block itself refused to let be filed. `game-walk file` is
    # the other half of that paperwork. Neither edits a file.
    ("divineos", "prereg", "reviewing"),
    ("divineos", "game-walk", "file"),
    ("divineos", "ask"),
    ("divineos", "recall"),
    ("divineos", "context"),
    ("divineos", "decide"),
    # council is a GROUP: a bare ("divineos", "council") prefix also matched
    # `authorize-bypass` and `emergency-skip`, so the fire door was a routine
    # remedy every gate asking this list let through (Aether found it 2026-10-11
    # and the matrix test in test_every_exit_passes_every_gate.py measures it). The
    # emergency exits stay reachable by their own route; these are the walk's own.
    ("divineos", "council", "log"),
    ("divineos", "council", "walk"),
    ("divineos", "council", "show"),
    ("divineos", "council", "recent"),
    ("divineos", "council", "check"),
    # The merge path prescribes these, and filing a review round otherwise owed a
    # fresh council walk per command. They record and edit nothing. `submit` and
    # `file-external-confirm` carry a condition, below: a line in Dad's voice is not
    # a remedy.
    ("divineos", "audit", "submit-round"),
    ("divineos", "audit", "prepare-merge"),
    ("divineos", "audit", "submit"),
    ("divineos", "audit", "file-external-confirm"),
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

#: --actor user, in the spellings a person types: spaced, equals, quoted.
#: The actors a filing may name and still be a remedy, as a CLOSED list of
#: literals. The first version blocked `--actor user` and let everything else
#: through, so a spelling it missed (a capital, a variable, split quotes, no actor
#: at all) filed in Dad's voice with no pause (Aether's hold, 2026-10-11). Now a
#: miss fails toward the pause: anything not literally named here is not a remedy.
#: A real new actor is added here by name, which is the only place to do it.
_NAMED_ACTOR = re.compile(
    r"--actor(?:[ \t]+|=)(?:aletheia|aria|aether|grok|gemini|claude-[a-z0-9.-]+)(?=[ \t]|$)"
)
_AUDIT_FILING = re.compile(r"\baudit[ \t]+(?:submit|file-external-confirm)\b")
#: An output option (--output, --out, -o...) on the DIVINEOS command itself: it
#: writes a file wherever it is pointed. Looked for only AFTER the program name,
#: so a `set -o pipefail` setup link is not mistaken for it. Fails toward
#: not-a-remedy.
_WRITES_WHERE_TOLD = re.compile(
    r"divineos\b[^;&|\n]*?[ \t](?:--out(?:put)?(?:[ \t=]|$)|-o(?:[ \t=]|\S|$))"
)

_LOG = Path.home() / ".divineos" / "remedy_passthrough.log"


def outside_quotes(command: str) -> str:
    """The command with quoted arguments blanked, or the text whole when that
    cannot be done safely. A word inside a quoted lesson is data, not an option
    and not a second goal (Aether, 2026-10-11); ``blank_quoted_spans`` already
    refuses the shapes where blanking would hide a real write, and returns None,
    which here means scan the text as it stands."""
    try:
        from divineos.core.command_parsing import blank_quoted_spans

        blanked = blank_quoted_spans(command)
    except Exception:  # noqa: BLE001 — not parseable: look at the text whole
        blanked = None
    return command if blanked is None else blanked


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
    # A finding filed with --actor user is DAD's confirm, and the pause before
    # words are put in his voice is one of the few worth keeping (Aether
    # 2026-10-11). So an audit filing is a remedy only when it carries exactly ONE
    # --actor and it is a literal from the closed list. Anything else (a capital, a
    # variable, split quotes, no actor, or a second --actor that would win) is NOT
    # a remedy, so a spelling this misses FAILS TOWARD THE PAUSE. The first version
    # blocked `user` and let the rest through, which was the other direction.
    if _AUDIT_FILING.search(command) and not (
        len(re.findall(r"--actor\b", command)) == 1 and _NAMED_ACTOR.search(command)
    ):
        return False
    # A remedy that writes where it is told is not a remedy: `briefing --output
    # x.md` is a file write wearing a recording command's name (Aletheia attacked
    # this shape on 619; the shared list took any arguments, so asking it first
    # brought the hole back, found by that PR's own closed-shape test). Looked for
    # OUTSIDE quoted spans: a lesson that mentions `-o` is data (Aether).
    if _WRITES_WHERE_TOLD.search(outside_quotes(command)):
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
