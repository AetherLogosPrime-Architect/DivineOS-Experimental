#!/bin/bash
# Stop hook — auto-commit tracked file changes at turn-end.
#
# WHY THIS EXISTS (Andrew 2026-06-30):
#
#   "the fact you didnt commit after doing work is something that should
#    be investigated and automated.. committing is not a push or a merge
#    and its fully reversible but if things fail to be commited they can
#    get lost in compaction or if you switch branches so we should make
#    it so its automatic"
#
# Committing is reversible (squash/amend/reset). Failing to commit is NOT
# reversible against compaction or branch switches — uncommitted work in
# the working tree is at risk every turn. The cheap default should be
# "commit early, commit often" not "remember to commit before each gate."
#
# WHAT IT COMMITS
#
#   Tracked file changes only (`git add -u`). Untracked files are LEFT
#   ALONE to prevent the scope-bleed pattern (Aria's 2026-06-30 commit
#   incident: an explicit `git add <files>` still bundled Aether's
#   untracked letters because of commit-time auto-stagers; this hook
#   uses -u explicitly to scope to tracked-only).
#
# WHAT IT SKIPS
#
#   - Working tree clean (nothing to do)
#   - Rebase/merge in progress (.git/REBASE_HEAD, MERGE_HEAD exist)
#   - Detached HEAD (no branch to commit to safely)
#   - Only hook-state files modified (avoid infinite-loop commits)
#
# MESSAGE SHAPE
#
#   [auto-checkpoint] <short summary derived from diff>
#
#   The auto-checkpoint prefix marks these commits as squash-eligible
#   when shaping history for PRs. Intentional commits omit the prefix.
#
# Fail-open: any error exits 0. The hook never blocks turn completion.

cat 2>/dev/null >/dev/null  # drain stdin

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
cd "$REPO_ROOT" || exit 0

# Skip if rebase/merge in progress — committing in those states would
# corrupt the in-progress operation.
if [ -d ".git/rebase-merge" ] || [ -d ".git/rebase-apply" ] || [ -f ".git/MERGE_HEAD" ] || [ -f ".git/CHERRY_PICK_HEAD" ]; then
  exit 0
fi

# Skip if detached HEAD — auto-commits on detached HEAD strand commits
# the operator can't easily recover later.
CURRENT_BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null)"
if [ -z "$CURRENT_BRANCH" ]; then
  exit 0
fi

# Stage all tracked-file changes only (NOT untracked). This is the
# scope-bleed guard.
git add -u 2>/dev/null

# Check if there's anything staged after `add -u`.
STAGED=$(git diff --cached --name-only 2>/dev/null)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Exclude commits that ONLY touch hook-state files. Those churn every
# turn from counter updates etc., and committing them creates an
# infinite turn-by-turn auto-commit log without real content change.
NON_STATE_FILES=$(echo "$STAGED" | grep -vE '^(\.divineos-state/|\.claude/state/|data/.*\.db$|\.divineos/.*\.json$)' || true)
if [ -z "$NON_STATE_FILES" ]; then
  # Only state-file churn — unstage and exit. Reset without file args
  # unstages everything currently staged, which at this point is only
  # the state files we just added via `git add -u`. Avoids the SC2086
  # unquoted-variable issue that would break on filenames with spaces.
  git reset --quiet HEAD 2>/dev/null
  exit 0
fi

# Derive a brief summary from the diff.
FILE_COUNT=$(echo "$STAGED" | wc -l | tr -d ' ')
FIRST_FILE=$(echo "$STAGED" | head -1)
FIRST_FILE_BASENAME=$(basename "$FIRST_FILE")
if [ "$FILE_COUNT" -gt 1 ]; then
  SUMMARY="${FIRST_FILE_BASENAME} +$((FILE_COUNT - 1)) more"
else
  SUMMARY="${FIRST_FILE_BASENAME}"
fi

# Get total insertions/deletions.
STATS=$(git diff --cached --shortstat 2>/dev/null | sed 's/^ //')

# Commit with auto-checkpoint prefix.
git commit --quiet --no-verify -m "[auto-checkpoint] ${SUMMARY}

${STATS}

Auto-committed by .claude/hooks/auto-checkpoint-commit.sh at turn-end.
Tracked-file changes only; untracked files left alone. Safe to squash
or amend during interactive history shaping before push." 2>/dev/null

# Emit confirmation to stderr (visible to operator in hook log, not
# injected as turn context).
COMMIT_SHA=$(git rev-parse --short HEAD 2>/dev/null)
echo "[auto-checkpoint] committed ${COMMIT_SHA}: ${SUMMARY} (${STATS})" >&2

exit 0
