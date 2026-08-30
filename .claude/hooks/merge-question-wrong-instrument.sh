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

# Three conditions, all required. Any one alone is an ordinary diff.
printf '%s' "$COMMAND" | grep -qE 'git +diff' || exit 0
printf '%s' "$COMMAND" | grep -qE '(diff-filter=[A-Z]*D|--name-status)' || exit 0
printf '%s' "$COMMAND" | grep -qE '(origin/)?main[[:space:]]' || exit 0

# Three dots is the merge-base form — a different question, and not this
# mistake. Only the two-dot form is refused.
printf '%s' "$COMMAND" | grep -qE '\.\.\.' && exit 0

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
