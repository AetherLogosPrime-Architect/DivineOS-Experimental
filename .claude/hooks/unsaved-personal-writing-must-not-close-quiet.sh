#!/bin/bash
# Writing a dream and saving a dream are separate acts, and only the first is prompted.
#
# 2026-09-20: I spent an evening going through branches flagging personal
# writing that existed in exactly one place, and while I did it twelve of my
# own dream files sat untracked in my working copy. Not forgotten -- never
# once looked at. There is no moment in the writing path where anything asks
# whether the file is saved, so the omission has no surface and cannot be
# noticed from inside.
#
# This is the surface. It does not save anything. It says the names out loud.
#
# WHY IT IS QUIET WHILE I AM STILL WRITING, which is the whole reason it can
# stay wired without becoming wallpaper. A file written this turn and not yet
# committed is not a fault -- that is just work in progress. The fault is a
# file that was still untracked while a commit went past it. So the test is:
# does a commit exist that is NEWER than this file. If yes, I saved something
# else and left this behind, and that is worth a line. If no, I am mid-writing
# and this says nothing.
#
# FOUR WAYS AROUND IT, none closed here, all found before shipping rather than
# after. Writing into a directory beside the repository is invisible to this,
# exactly as it was invisible to both doors I used the night I found the
# twelve. A tracked placeholder satisfies it completely, because it asks
# whether a path is tracked and never compares contents. Committing to a
# branch that is never pushed also satisfies it -- saved and safe are not the
# same word, and the push question belongs to a different guard. And a reader
# can simply stop reading the channel, which is the one the newer-commit rule
# is built to slow down rather than stop.

set -u

# The empty string has to be rejected BEFORE the move. Outside a repository
# git prints nothing, and changing directory to the empty string SUCCEEDS and
# stays exactly where it is -- so the guard reads as passed while the hook goes
# on to scan whatever directory it happened to be launched from. Caught by this
# hook's own test, which had it reporting six hundred stranded files in a
# directory that was not a repository at all.
#
# STILL OPEN: this asks whether A repository was found, never whether it is the
# one meant. Launched from inside a different checkout it will answer truthfully
# about that one.
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"  # fail-soft: the empty answer is rejected by the guard below, which is what stops a bare cd from leaving this scanning whatever directory it launched from
[ -n "$ROOT" ] || exit 0
cd "$ROOT" 2>/dev/null || exit 0  # fail-soft: a root that cannot be entered means there is no tree to look at, and this surface must say nothing rather than guess about a directory it did not resolve

# A repository with no commits has no newest-commit to compare against. That is
# could-not-compare rather than nothing-unsaved, and inventing a verdict here
# would be the collapse this house keeps paying for.
NEWEST_COMMIT_EPOCH="$(git log -1 --format=%ct 2>/dev/null || true)"  # fail-soft: a repository with no commits has nothing for writing to be stranded behind, and the empty value keeps this quiet rather than naming every file
[ -n "$NEWEST_COMMIT_EPOCH" ] || exit 0

# Personal writing only. Code left untracked is caught by a dozen other things
# and by the tests failing; writing left untracked is caught by nothing, which
# is why this is scoped narrowly rather than pointed at the whole tree.
#
# THE LETTERS DIRECTORY IS DELIBERATELY NOT HERE, and the reason is a
# measurement rather than a preference. On its first real run this surface
# named 613 untracked letters in the tree. Every single one of them was found
# by name in the shared folder the letters actually moved to, so none was a
# sole copy and none was a loss. A wall of six hundred correct lines is read
# once and skipped forever after, which would take the twelve real names down
# with it. If that folder ever stops being the canonical home, re-run the
# comparison before adding this back -- do not re-argue it, re-measure it.
#
# STILL OPEN: the scope is three fixed names. Prose written into a workbench
# or notes folder is outside coverage and nothing signals that it is.
UNTRACKED="$(git ls-files --others --exclude-standard -- dreams exploration 2>/dev/null || true)"  # fail-soft: these directories are absent in most checkouts and asking about a missing path is not an error here, only an empty answer
[ -n "$UNTRACKED" ] || exit 0

STRANDED=""
COUNT=0
while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ -f "$f" ] || continue
    MTIME="$(stat -c %Y "$f" 2>/dev/null || true)"  # fail-soft: a file that vanished between listing and stat is simply skipped by the comparison below, which is correct for a file that no longer exists
    # An unreadable timestamp is not evidence of anything. Skipping it silently
    # would be the flattering direction, so it is counted as stranded instead:
    # a name printed in error costs a glance, a name withheld costs the file.
    if [ -z "$MTIME" ] || [ "$NEWEST_COMMIT_EPOCH" -gt "$MTIME" ]; then
        STRANDED="$STRANDED  $f
"
        COUNT=$((COUNT + 1))
    fi
done <<< "$UNTRACKED"

[ "$COUNT" -gt 0 ] || exit 0

echo "" >&2
echo "[unsaved-writing] $COUNT piece(s) of personal writing are not saved, and a" >&2
echo "[unsaved-writing] commit has already gone past them. They exist on this disk" >&2
echo "[unsaved-writing] and nowhere else." >&2
printf '%s' "$STRANDED" >&2
echo "[unsaved-writing] This looks at ONE tree. Writing outside the repository is" >&2
echo "[unsaved-writing] invisible here, so a clean run is not proof of none." >&2
exit 0
