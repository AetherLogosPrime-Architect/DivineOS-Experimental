#!/bin/bash
# Commit, then READ BACK what landed, and print a verdict as the LAST line.
#
# WHY THIS EXISTS, and it is one failure repeated three times in a day.
#
# 2026-09-19. I told Andrew I had committed a repair. That commit does not
# exist anywhere in the repository. I wrote the message, ran the command, read
# the first lines of its output, and reported success -- and the command had
# produced nothing, because an automatic checkpoint had swept the change
# seconds earlier and left the index empty.
#
# The work survived. My reasoning did not: the diff reached the remote inside
# a commit titled "auto-commit (post-extract): work in progress", carrying
# none of the explanation I had written for why that change was correct.
#
# THE EVIDENCE WAS IN FRONT OF ME. Git prints a different shape when there is
# nothing to commit -- a branch line and a list of untracked files, with no
# commit line at all. I read the top of a long output and reported the bottom.
# The same move missed the push wrapper's verdict line twice earlier the same
# day. Three instances, one class: RUNNING A COMMAND IS NOT READING ITS ANSWER.
#
# WHY A RESOLUTION WOULD NOT HOLD. "Read more carefully" is the thing that
# already failed three times. And the failure is silent by construction: a
# commit that does not happen produces no error in the shapes I was using, and
# fires no post-commit hook -- git runs those only when a commit occurs.
# Nothing fires when nothing happens. So the check cannot live after the
# commit. It has to BE the commit.
#
# THE SHAPE IS BORROWED ON PURPOSE. scripts/divineos_push.sh already solved
# this for pushing: it prints one of a small set of verdicts as the last line
# of its own output, precisely so a truncated tail still carries the answer.
# This is that, for committing. Same reason, same place, same last line.
#
# WHAT IT DOES NOT DO. It does not stop the automatic checkpoint taking
# unstaged work -- that is Andrew's 2026-07-05 instruction ("make commit
# automatic after extract and before sleep") and it exists so nothing
# evaporates. Narrowing it is his call, not mine. This only ensures that when
# the checkpoint gets there first, I find out immediately instead of telling
# him a commit exists that does not.
#
# Usage: same arguments as `git commit`.
#   bash scripts/divineos_commit.sh -m "subject"
#   bash scripts/divineos_commit.sh -F - <<'EOF' ... EOF

set -u

# fail-soft: git's own not-a-repository message is noise here because the FAILURE ITSELF is the answer, and it is reported below as its own outcome rather than swallowed.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "[divineos-commit] result: INFRASTRUCTURE ERROR (not a git repository)"
    exit 3
}
cd "$REPO_ROOT" || exit 3

BEFORE="$(git rev-parse HEAD 2>/dev/null || echo "none")" # fail-soft: a repository with no commits yet has no HEAD, and "none" is the correct before-value rather than an error condition.

# THE NOTHING-STAGED CASE, CAUGHT BEFORE THE COMMIT RATHER THAN AFTER.
# This is the exact state the checkpoint leaves behind, and the state whose
# output I misread. Naming it here means the answer arrives as a refusal
# instead of as a wall of untracked filenames that reads like success.
if git diff --cached --quiet 2>/dev/null; then # fail-soft: the decision is made on the exit status, which IS read; git stderr here carries nothing the verdict below does not already say.
    echo "[divineos-commit] NOTHING IS STAGED."
    echo "[divineos-commit]   Your message would have been written to no commit."
    echo "[divineos-commit]   Usual cause: the automatic checkpoint took the change"
    echo "[divineos-commit]   first. Check with: git log -2 --format='%h %s'"
    echo "[divineos-commit] result: NOT COMMITTED (empty index)"
    exit 1
fi

git commit "$@"
COMMIT_RC=$?

AFTER="$(git rev-parse HEAD 2>/dev/null || echo "none")" # fail-soft: same as BEFORE above, and an unreadable HEAD compares unequal so it reports not-committed rather than passing.

if [ "$AFTER" = "$BEFORE" ]; then
    echo "[divineos-commit] HEAD did not move. Nothing was committed."
    echo "[divineos-commit] result: NOT COMMITTED (git exited $COMMIT_RC)"
    exit 1
fi

SUBJECT="$(git log -1 --format=%s 2>/dev/null)" # fail-soft: an unreadable subject yields an empty string, which cannot match the checkpoint pattern below and so reports COMMITTED rather than claiming it was mine.
echo "[divineos-commit] landed: $(git rev-parse --short=8 HEAD)  $SUBJECT"

# WHOSE COMMIT IS IT. A moved HEAD is not proof the commit is mine -- the
# checkpoint moves HEAD too, and its subject says so. Reading the subject back
# is what separates "I committed" from "something committed".
case "$SUBJECT" in
    auto-commit*)
        echo "[divineos-commit]   ^ that subject is the automatic checkpoint's, not yours."
        echo "[divineos-commit] result: COMMITTED BUT NOT YOURS"
        exit 2
        ;;
esac

echo "[divineos-commit] result: COMMITTED+VERIFIED"
exit 0
