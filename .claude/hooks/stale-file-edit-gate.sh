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

cat >&2 <<EOF
STALE-FILE EDIT — $REL has $COUNT commit(s) on origin/main that are not in your branch.

You are about to edit a version you already know is out of date. This is
the exact shape that cost a session: a fix rebuilt from scratch while a
better version of the same function sat unpulled on main.

Commits you do not have for this file:
$BEHIND

Two honest ways forward, and the choice is yours:

  1. Pull first, then edit the current version:
       git fetch origin main
       git merge origin/main

  2. Proceed deliberately, having looked at what landed:
       git show origin/main:$REL
     Then say why the newer work does not change what you are about to do.

Measured 2026-08-01: 62% of my non-letter files are also touched on main.
Overlap is normal and fine. Editing the STALE copy is the part that wastes
the work.
EOF
exit 2
