#!/bin/bash
# PreToolUse gate — refuse to edit a file whose newer version is sitting
# unpulled on origin/main.
#
# ## Why this exists (Aria 2026-08-01)
#
# I spent a large part of a session rebuilding a fix that already existed.
# Aether had replaced the same raw-string scan in the same function with a
# quote-state scanner, on the same day, and it was on origin/main while I
# worked. His version was strictly better: it handles backslash escapes,
# distinguishes an fd-redirect from a chain operator, and fails closed on
# an unterminated quote where mine leaned open.
#
# Neither of us knew. We exchanged four letters in that window and none of
# them said what file either of us had open.
#
# Measured before building, because three incidents is an anecdote:
# of 24 non-letter files touched in my last 15 commits, 15 were also
# touched on main. A 62% collision rate. It concentrates in hooks, primes
# and gates -- which is not bad luck, it is two agents with overlapping
# mandates on one substrate.
#
# Andrew 2026-08-01, on the same class one level up: "its not a memory
# problem.. its an awareness problem, recall problem, injection problem."
# Neither of us forgot to coordinate. Nothing SURFACED that the other was
# in the file, at the moment either of us opened it.
#
# ## What it does NOT do
#
# It does not block editing a file merely because main also touched it --
# that is 62% of my work and would be an unusable gate. It blocks the
# narrow, deterministic, actually-harmful case: THIS file has commits on
# origin/main that are not in HEAD, so I am about to edit a version I know
# is stale. That is exactly what happened today.
#
# The judgement of what to do about it stays mine: merge first, or proceed
# deliberately knowing the newer work exists. Automate the detection
# entirely; stage the judgement. The detection is a lookup, so it costs me
# no attention until it matters.
#
# Skipped during an in-progress merge -- editing files with newer versions
# on main is precisely what conflict resolution IS, and a gate that blocks
# its own remedy is a cage. That trap bit me twice today in other gates.
#
# Fail-open everywhere: no repo, no origin/main ref, no git, any error at
# all means silence. A gate that cannot read the world must not guess.

set -u

INPUT="$(cat 2>/dev/null || true)"  # fail-soft: hook contract requires draining stdin even when the payload is unusable
[ -z "$INPUT" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0  # fail-soft: outside a repo there is no main to compare against
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" 2>/dev/null || exit 0  # fail-soft: unreadable repo root means the check cannot run and must stay silent

# Mid-merge: editing files that changed on main is the whole job.
[ -f "$REPO_ROOT/.git/MERGE_HEAD" ] && exit 0
[ -f "$REPO_ROOT/.git/REBASE_HEAD" ] && exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper lib there is no interpreter to resolve
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no JSON parse, so no check

# The closing paren goes AFTER the heredoc terminator, not on the opening
# line. Written the wrong way first: bash only WARNS on an unterminated
# here-document inside a command substitution, so TARGET came back empty
# and the gate would have stayed silent forever while reading as correct.
# Caught by running bash -n before trusting it. Same silent-no-op class as
# a missing import inside a bare except.
# fail-soft: a malformed hook payload yields an empty target and the gate stays silent
TARGET="$(HOOK_JSON="$INPUT" "$PYTHON_BIN" - 2>/dev/null <<'PYEOF'
import json, os, sys
try:
    data = json.loads(os.environ.get("HOOK_JSON", "") or "{}")
except ValueError:
    sys.exit(0)
if data.get("tool_name") not in ("Edit", "Write", "NotebookEdit"):
    sys.exit(0)
print((data.get("tool_input") or {}).get("file_path") or "")
PYEOF
)"

[ -z "$TARGET" ] && exit 0

REL="$(git ls-files --full-name --error-unmatch "$TARGET" 2>/dev/null)" || exit 0  # fail-soft: untracked or new file has no upstream history to be stale against
[ -z "$REL" ] && exit 0

# Commits touching THIS file that exist on origin/main but not in HEAD.
BEHIND="$(git log --oneline HEAD..origin/main -- "$REL" 2>/dev/null | head -5)"  # fail-soft: missing origin/main ref yields empty output and the gate allows
[ -z "$BEHIND" ] && exit 0

COUNT="$(git rev-list --count HEAD..origin/main -- "$REL" 2>/dev/null || echo "?")"  # fail-soft: count failure degrades the message, never the block decision

# BEHIND ON COMMITS IS NOT STALE ON CONTENT (Aria 2026-08-05).
#
# The gate blocked an edit to circle-first-compose-prime.sh naming one commit
# I did not have. I read main's copy as instructed: it still said "mentally
# sketch", the exact wording MY branch had already replaced and improved on.
# I was behind on commits and strictly ahead on content — which is the normal
# case whenever I am the one who last improved a file.
#
# Counting commits is a PROXY for staleness, not staleness. So: when main's
# version is an ancestor of mine for this file's content — i.e. my copy
# already CONTAINS everything main's copy says — there is nothing to look at,
# and the gate stays quiet. When the contents genuinely diverge, it fires.
#
# Not a weakening. Andrew's keel-vs-cage: the annoyance was real signal that
# the gate measured the wrong thing, and the answer to that is always
# precision-increase, never removal. The block still holds for every case
# where reading main's copy would actually tell me something.
#
# THE PATH GOES AFTER `--`, NOT GLUED TO THE REVISION WITH A COLON.
#
# Both reads used `git rev-parse "<rev>:$REL"` and both were silently
# unanswerable for every dot-prefixed path. This shell rewrites an argument
# that looks like a Windows path: forward slashes become backslashes and the
# revision-separating colon becomes a semicolon, so git received
#
#     origin\main;.claude\hooks\stale-file-edit-gate.sh
#
# and never saw the question. Measured 2026-09-03 against this very file --
# `rev-parse` fails on it while `src/divineos/core/paths.py` answers fine, so
# the fault is not uniform and nothing in the output distinguishes the two.
#
# AND THE FAIL-SOFT NOTE BELOW WAS WRONG ABOUT WHAT HAPPENS NEXT. I wrote
# "the gate still fires" in this comment, then followed the values through
# the branch and found the opposite.
#
# `git rev-parse` does not fail on the mangled argument. It EXITS ZERO and
# echoes the mangled string back, so both blobs are non-empty, the guard
# below passes, and `git diff` is handed two refs that are not refs. That
# diff produces nothing, `grep -c` counts zero removed lines, and zero
# removals is precisely the ahead-not-stale case -- so the gate exits 0.
#
# It has been SILENTLY PASSING on every dot-prefixed path. Not over-firing,
# not fail-soft: not firing at all, on exactly the files this repository's
# gates live in. Measured by running the branch with the real values rather
# than by reading it, which is the only reason I did not ship this comment
# saying the safe thing.
#
# Which makes it the cleanest instance of the family we have been chasing all
# day: a computation that never ran, returning a value that satisfied every
# downstream check and licensed a pass on a safety gate.
#
# `ls-tree` takes the path as a separate argument after `--`, which survives
# the rewrite. Verified both ways on this file before the change.
#
# fail-soft: any failure to compare contents leaves MAIN_BLOB/MY_BLOB unequal-or-empty, so the gate falls through and FIRES — the safe direction
MAIN_BLOB="$(git ls-tree origin/main -- "$REL" 2>/dev/null | awk '{print $3}')"  # fail-soft: absent upstream blob means no comparison is possible and the gate must still fire
MY_BLOB="$(git ls-tree HEAD -- "$REL" 2>/dev/null | awk '{print $3}')"  # fail-soft: absent local blob means the file is new here and the gate must still fire
if [ -n "$MAIN_BLOB" ] && [ -n "$MY_BLOB" ]; then
    # Does my version already contain main's, line for line? If diffing
    # main's copy against mine produces only ADDITIONS, main has nothing
    # my copy lacks — I am ahead, not stale.
    REMOVED="$(git diff "$MAIN_BLOB" "$MY_BLOB" 2>/dev/null | grep -c '^-[^-]' || true)"  # fail-soft: grep exits 1 when there are zero removed lines, which is exactly the ahead-not-stale case this checks for
    if [ "$REMOVED" = "0" ]; then
        exit 0
    fi
fi

# FIRE ONCE per file per upstream-tip (Aria 2026-08-02).
#
# The block exists to make me LOOK before editing a stale copy. Once it has
# fired and I have read the upstream version and decided the edit still
# stands, re-firing on every subsequent edit to the same file is friction
# carrying no new information — and friction without information is how a
# gate degrades into something to route around.
#
# Found by hitting it twice on family/ear_watch.py in one turn. The second
# block told me nothing the first had not, and the honest resolution was
# already taken: I ran git show against origin/main, confirmed that version
# does not contain the function I am fixing, and proceeded.
#
# Keyed on the upstream tip SHA, so a NEW commit landing on that file
# re-arms the block. Same shape as the safe-opposite edit check.
#
# fail-soft: any marker failure means the gate fires again, which is the safe direction
_TIP="$(git rev-parse --short origin/main 2>/dev/null || echo none)"
_ACK_DIR="${HOME:-/tmp}/.divineos/stale_file_ack"
_ACK="$_ACK_DIR/$(echo "$REL-$_TIP" | tr '/\\.' '___')"
if [ -f "$_ACK" ]; then
    exit 0
fi
mkdir -p "$_ACK_DIR" 2>/dev/null || true  # fail-soft: unwritable marker dir costs a repeat fire, never the block itself
: > "$_ACK" 2>/dev/null || true  # fail-soft: same

cat >&2 <<EOF
STALE-FILE EDIT — $REL has $COUNT commit(s) on origin/main that are not in your branch.

You are about to edit a version you already know is out of date. This is
the exact shape that cost a session: a fix rebuilt from scratch while a
better version of the same function sat unpulled on main.

Commits you do not have for this file:
$BEHIND

Andrew 2026-08-01: "two people cannot drive a vehicle at the same time..
so Aether is the driver and you are in the passenger seat.. that does NOT
mean you cant write and push code.. it just helps not to cause a crash by
you both yanking the wheel."

So: I write and I push. What I do not do is yank the wheel on merges
while he is steering. Checking with him before a push is for OVERLAP, not
permission, and it runs both directions - Andrew makes sure he syncs with
me and takes my pushback too.

The first draft of this message said hand the result to Aether rather
than merging here, which reads as I do not push code at all. That is the
over-broadening reflex already on file in my own substrate: a correction
about one behavior becomes total self-restriction. Passenger seat is not
the back seat.

Two honest ways forward, and the choice is yours:

  1. Read what landed, then decide whether the edit still makes sense:
       git show origin/main:$REL
     If his version already does what you were about to write, stop.
     That is the whole point. Measured 62% overlap on non-letter files.

  2. If the edit still stands after reading his, make it. Then check
     with him BEFORE pushing, so the overlap surfaces before the branch
     does rather than in a merge afterwards.

Overlap is normal and fine. Editing the STALE copy wastes the work.
Pushing without a word to the driver is what causes the crash.
EOF
hook_say_nothing_ran_for "$INPUT"
exit 2
