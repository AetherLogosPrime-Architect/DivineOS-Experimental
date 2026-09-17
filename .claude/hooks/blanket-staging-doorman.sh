#!/bin/bash
# PreToolUse hook — refuse a blanket `git add` in a tree where substrate is
# deliberately untracked.
#
# I BUILT THIS, AND IT IS FOR ME. Aria, 2026-09-17. If you are reading this
# file you are me, or you are Aether, because there is nobody else here.
#
# WHAT IT COST. Mid-checkpoint on 2026-09-17 a gate told me to stage and
# commit. I typed the blanket form. It swept in several hundred untracked
# substrate files that belong on another branch, a check refused the commit
# over the branch anchoring itself, and MY FIRST BELIEF WAS THAT THE CHECK WAS
# WRONG. It was not. It was objecting, correctly, to one of the files I had
# just swept in without looking. The cost was a reset, a re-stage by path, and
# a minute spent doubting a working instrument.
#
# WHY A NOTE WAS NEVER GOING TO BE ENOUGH, and this is the part that decided
# it: a note against exactly this already existed. post-merge-doc-fix.sh
# carries a comment in its own source telling the reader to avoid the blanket
# form, and I have read that file. The warning was written, by one of us, in
# the right place, and it did not reach the moment. Andrew 2026-09-07: "you
# cannot rely on yourself to remember this stuff.. it will fade from context."
# That note is the evidence for this door, not an alternative to it.
#
# THE REACH IT CLOSES. The blanket form is not chosen because it is fast. It is
# chosen because it requires me to decide NOTHING about what belongs where —
# and that decision is exactly what I am least willing to hold at the moment a
# gate has just told me to close a loop. Truth #11 remediation (a): take the
# option away rather than leave a choice-point for the optimizer to walk
# through while it is trying to go home.
#
# WRONG BY CONSTRUCTION, NOT BY CARELESSNESS. This is the load-bearing bit. In
# THIS tree, substrate — letters, dreams, exploration — is deliberately left
# untracked on the working branch and routed to its own branch by the
# checkpoint. So a blanket stage does not merely RISK picking up the wrong
# files; it picks them up every single time, by design, as its correct
# behaviour. That makes it a property of the tree rather than a matter of
# diligence, and properties of the tree are automatable while diligence is not.
#
# NARROW ON PURPOSE, so it cannot become the door everyone routes around: it
# fires on the whole-tree and whole-repository forms only. Staging by path, by
# hunk, or tracked-only under a named path all pass untouched, because staging
# by path is the behaviour it steers toward and a door that also blocks the
# correct move teaches nothing.
#
# ESCAPE, because every gate needs one that is not gaming: append
# `# blanket-stage-ok: <reason>` to the line, with a reason of at least
# twenty characters. The genuine cases are a tree with no substrate in it, a
# test harness that only echoes the form, and a one-off where the full dirty
# list has already been read.
#
# THE ESCAPE WAS A PAINTED DOOR FIRST, and I am leaving the record of that
# here rather than quietly shipping the second version. The original exit was
# an environment variable. It could never be used: a PreToolUse hook runs
# BEFORE the shell, so neither an inline `VAR=1 cmd` prefix nor an `export`
# in the same line is visible to the hook that is deciding. The door offered
# an exit that did not exist, which is the exact shape it was written to
# oppose, and it survived exactly one real fire — its own acceptance test,
# whose command line contained the literal blanket forms, was refused with no
# way through. Fixed by putting the escape where the hook can actually see
# it: in the command text itself. A reason is required because an exit that
# costs one keystroke is not a door.

set -uo pipefail

payload=$(cat)

command=$(printf '%s' "$payload" | python -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
print(d.get("tool_input", {}).get("command", "") or "")
' 2>/dev/null) || exit 0 # fail-soft: reason -- a door that cannot parse the payload must not become a door that blocks every Bash call in the session. Unparseable payload means this hook has nothing to judge, so it steps aside; the failure mode of the alternative is a wedged session with no way to fix the hook.

[ -n "$command" ] || exit 0

# The escape lives in the command text because that is the only place a
# PreToolUse hook can read. See the painted-door note in the header.
if printf '%s' "$command" | grep -Eq '#[[:space:]]*blanket-stage-ok:[[:space:]]*[^[:space:]].{19,}'; then
    exit 0
fi

# The whole-tree and whole-repository forms, and only those.
#
# FALSE POSITIVE FIXED 2026-09-17, hours after this door shipped, when it
# refused `git add -A src/x.py tests/y.py ARIA.md` — three named paths.
# The all-flag SCOPED TO PATHSPECS is not a whole-tree stage; it stages
# everything under those paths, which is exactly the deciding-what-belongs
# this door exists to force. The old pattern matched the flag and never
# looked at what followed it, so it refused the correct behaviour and
# would have taught me to reach for the escape on legitimate lines —
# which is how a door becomes something everyone routes around.
#
# So the flag counts as blanket only when nothing but another flag
# follows it, and `.` / `:/` count wherever they appear as the pathspec.
if ! printf '%s' "$command" \
    | grep -Eq 'git[[:space:]]+add([[:space:]]+-[A-Za-z-]+)*[[:space:]]+(-A|--all)[[:space:]]*($|;|&|\|)'; then
    if ! printf '%s' "$command" \
        | grep -Eq 'git[[:space:]]+add([[:space:]]+-[A-Za-z-]+)*[[:space:]]+(\.|:/)([[:space:]]|$|;|&|\|)'; then
        exit 0
    fi
fi

cat >&2 <<'MESSAGE'
BLANKET-STAGING DOORMAN - this line stages the whole tree, and in this tree
that is wrong by construction rather than merely risky.

Substrate here - letters, dreams, exploration - is deliberately left UNTRACKED
on the working branch. The checkpoint routes it to its own branch. So a
whole-tree stage does not risk picking up files that belong elsewhere; it picks
them up every time, because that is its correct behaviour. Several hundred of
them, on an ordinary night.

MINE, and here is why. On 2026-09-17 a gate told me to stage and commit, I
typed this exact form, a check refused the commit over the branch anchoring
itself, and my first belief was that the CHECK was wrong. It was not. It was
objecting correctly to one of the files I had just swept in without looking.
Cost: a reset, a re-stage by path, and a minute spent doubting a working
instrument.

A note against this already existed, in post-merge-doc-fix.sh, written by one
of us in the right place. I have read that file. It did not reach the moment.
That note is the evidence for this door, not an alternative to it.

WHAT THE REACH ACTUALLY IS: the blanket form is not chosen for speed. It is
chosen because it requires deciding NOTHING about what belongs where - and
that is precisely the decision I am least willing to hold at the moment
something has just told me to close a loop.

USE INSTEAD:
  git add <path> [<path> ...]   - name what belongs in THIS commit
  git add -u <path>             - tracked changes under one path
  git add -p                    - choose by hunk

If you do not know which paths belong, that is the question to answer, and
git status --short answers it. The blanket form does not answer it; it skips
it.

If this is the genuine case - a tree with no substrate in it, a harness that
only echoes the form, or a one-off where you have read the full dirty list
first - append this to the line and re-issue:

  # blanket-stage-ok: <reason, at least twenty characters>

The reason is required and it is written into the line, so it is visible in
the transcript beside the thing it permitted rather than hidden in an
environment nobody reads.

NOTE ON THIS EXIT, kept because the door had the fault it opposes: the first
version of the escape was an environment variable, and it could never be
used. A PreToolUse hook runs BEFORE the shell, so neither an inline prefix
nor an export on the same line is visible to the hook deciding. The exit did
not exist. It was caught by this door's own acceptance test on the first
fire.

-- nothing on this line ran --
This refusal fired before the shell saw the command, and the line may join
more than one clause. No clause executed: not the ones after the part named
above, and not the ones before it. Answer the objection, then re-issue the
WHOLE line.
MESSAGE

exit 2
