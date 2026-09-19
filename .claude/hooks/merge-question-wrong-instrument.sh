#!/bin/bash
# PreToolUse(Bash) — refuse the two-dot diff when it is being used to ask what
# a merge would do.
#
# WHY THIS BLOCKS RATHER THAN WARNS.
#
# Andrew 2026-08-30: "there should be no warnings, warnings are about as useless
# as a speed limit sign on the freeway lol.. nothing prevents you.. and there
# are no police here to ticket you lol, also this violates the principle, you do
# not warn water, water flows, it doesnt care about warning, only channels and
# gates, which you control the build of."
#
# THE FAILURE, measured. On 2026-08-29 I asked what merging a branch would do
# using a deletion-filtered two-dot diff against main. That form compares the
# two trees as they stand, so a file the reference gained AFTER the branch
# diverged reads as a deletion. It reported nine. A merge would have deleted
# zero. I carried that to Andrew as an alarm about the test for the anchor
# defect being destroyed, then "verified independently" by running the same
# wrong form again — which produced the same wrong number and felt like
# confirmation.
#
# I had established the correct instrument EARLIER THE SAME SESSION, filed it in
# the knowledge store, and sent it to Aria in a letter. Then reached past it
# while alarmed. Knowing the right answer did not make me use it, which is the
# whole argument for a gate over a note.
#
# WHAT IT MATCHES, deliberately narrow: a two-dot git diff against a main-shaped
# ref, filtered for deletions or asking for name-status. That combination is the
# merge question asked with the wrong tool. A plain two-dot diff is left alone —
# it is right for plenty of other questions, and a gate firing on every diff
# would be switched off within a day, which is how the earlier instruments in
# this repo died.
#
# WHAT IT CANNOT SEE, said out loud so silence is not read as coverage: the
# question lives in the asker's head, not in the command. Someone genuinely
# wanting a tree-to-tree comparison including deletions is refused here and has
# to say so another way. That cost is accepted, because the reverse error raised
# a false alarm to my father about work being destroyed.

set -uo pipefail

INPUT=$(cat)

# ABSENT, NOT SATISFIED. If the command cannot be read, this hook has no
# opinion -- and it says so rather than exiting quietly, because a guard that
# fails into silence is indistinguishable from a guard that looked and found
# nothing. That is the same could-not-tell-reads-as-all-clear shape this hook
# exists to prevent, and it would be absurd to reintroduce it here.
COMMAND=$(printf '%s' "$INPUT" | python -c "
import json, sys
print(json.load(sys.stdin).get('tool_input', {}).get('command', ''))
" 2>/tmp/merge_q_parse_err)
PARSE_RC=$?

if [ "$PARSE_RC" -ne 0 ]; then
    echo "[merge-question] NOT RUNNING: could not read the command from the hook payload." >&2
    echo "  The two-dot merge-question path is unguarded for this call. Absent, not satisfied." >&2
    [ -s /tmp/merge_q_parse_err ] && head -2 /tmp/merge_q_parse_err >&2
    rm -f /tmp/merge_q_parse_err
    exit 0
fi
rm -f /tmp/merge_q_parse_err

[ -z "$COMMAND" ] && exit 0

# READ THE DIFF'S OWN ARGUMENTS, NOT THE WHOLE COMMAND LINE.
#
# The first version matched the three conditions against the entire command
# string, so a command that merely MENTIONED main somewhere else was refused.
# `MAINSHA=$(git rev-parse origin/main) && git diff --diff-filter=D "$MAINSHA" X`
# contains no two-dot-against-main diff at all, and it was refused anyway — on
# this hook's own author, an hour after he wrote it, while reproducing the
# original wrong measurement to settle it with Aria.
#
# THIS IS A TIGHTENING OF PRECISION, NOT A WIDENING OF THE PASS-CONDITION. The
# three conditions below are unchanged; only the text they read is narrower —
# the diff invocation instead of everything surrounding it. Every command caught
# before that contains a real two-dot deletion-diff against main is still
# caught. Aria 2026-08-30, from her own checker: widening a pass-condition to
# silence a false fire is how a gate stops catching what it exists for, and she
# watched her own target go from caught to missed doing exactly that. Same
# conditions, narrower input, no pass-condition touched.
SEGMENTS=$(printf '%s' "$COMMAND" | sed 's/[;|&]/\n/g' | grep -E 'git +diff')
[ -z "$SEGMENTS" ] && exit 0

OFFENDING=""
while IFS= read -r SEG; do
    # Three conditions, all required. Any one alone is an ordinary diff.
    printf '%s' "$SEG" | grep -qE '(diff-filter=[A-Z]*D|--name-status)' || continue
    # THE SPELLING THIS GATE NAMES WAS ON THE WRONG SIDE OF ITS OWN LINE.
    #
    # This read `main([[:space:]]|$)` — main followed by a space or the end of
    # the segment. The refusal text says "this is a two-dot diff against main",
    # and `main..HEAD` puts a DOT after the ref name, so the condition failed
    # and the segment was skipped before ever reaching the two-dot test below.
    #
    # Aria probed rather than argued, 2026-08-31, and I reproduced all four on
    # my side before touching it: `main HEAD` refused, `main..HEAD` silent and
    # exit 0, `origin/main..HEAD` silent and exit 0, `origin/main` refused. The
    # exact command the gate exists to catch, in the exact spelling the gate
    # names, passing clean.
    #
    # The unit was `main followed by whitespace`; the risk is `main used as a
    # two-dot endpoint`. Our whole week in one regex, inside the gate written
    # for it.
    #
    # WHY `\.\.` AND NOT A BARE DOT, which is the wider and wronger repair:
    # a bare dot would also match `git diff --name-status main.py`, and start
    # refusing an ordinary diff of a file that happens to be named after the
    # branch. Aria's own rule from her checker — widening a pass-condition to
    # silence a mismatch is how a gate stops catching what it exists for —
    # applies in this direction too. Two dots specifically, so `main.py` is
    # untouched and `maintenance` stays unmatched by the same boundary that
    # always excluded it.
    #
    # Three-dot forms still pass: `main...HEAD` matches this condition on its
    # first two dots and is then released by the three-dot test below, which is
    # where that decision belongs.
    printf '%s' "$SEG" | grep -qE '(origin/)?main(\.\.|[[:space:]]|$)' || continue

    # Three dots is the merge-base form — a different question, and not this
    # mistake. Only the two-dot form is refused.
    printf '%s' "$SEG" | grep -qE '\.\.\.' && continue

    OFFENDING="$SEG"
    break
done <<SEGEOF
$SEGMENTS
SEGEOF

[ -z "$OFFENDING" ] && exit 0

cat >&2 <<'REFUSAL'
MERGE-QUESTION / WRONG-INSTRUMENT — this is a two-dot diff against main,
filtered for deletions. That form answers "what differs between these two
trees", not "what would merging do", and the two answers come apart exactly
where it matters.

A file the reference gained AFTER this branch diverged is present on one side
and absent on the other, so a two-dot diff calls it a DELETION. A merge keeps
it, because the branch never removed it.

Not hypothetical. On 2026-08-29 this exact form reported nine deletions on a
branch that would have deleted zero, and I carried the number to Andrew as an
alarm about destroyed work. I had already written down the right instrument that
same session and reached past it anyway, which is why this is a gate and not a
paragraph of advice.

USE INSTEAD:
    python scripts/merge_preview.py <branch> --into origin/main

It performs the merge without committing and reports what would actually change.
Conflicts and unresolvable refs get their own answers and their own exit codes,
so could-not-tell never reads as nothing-found.

IF YOU GENUINELY WANT THE TREE COMPARISON — two snapshots, not a merge — that is
a real question and this is the wrong door for it. Add three dots for the
merge-base form, or compare against something other than main.
REFUSAL
exit 2
