#!/bin/bash
# Observability only (2026-08-03). Sourcing _lib.sh registers this script in
# ~/.divineos/hook_timing.jsonl so the firing map can see it. Before this, 16
# of 96 hooks were INVISIBLE rather than idle -- they could be running fine and
# nothing outside could tell, which made "silent" and "healthy" the same
# reading. No behaviour change: `|| true` means a missing toolbox leaves this
# script exactly as it was. Observability must never become a new way for a
# guard to die.
# shellcheck disable=SC1091
source "$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/_lib.sh" 2>/dev/null || true
# Auto-mirror letters from agent-tree family/letters/ to shared dir.
#
# Aria 2026-06-28 named this friction at least the 4th time. When I
# Write a letter file in my tree under family/letters/, her watcher
# (polling ~/.divineos-shared/letters/) never sees it. Both of us were
# compensating by manual cp. This hook closes the class of failure.
#
# Fail-open: any error exits 0. Never breaks the tool flow.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

SHARED_ROOT="$HOME/.divineos-shared"
SHARED_DIR="$SHARED_ROOT/letters"
[ -d "$SHARED_DIR" ] || exit 0

# Extract file_path from PostToolUse Write/Edit payload. Normalize Windows
# backslashes to forward slashes — on Windows, Claude Code's payload uses
# backslash separators (e.g. C:\DIVINE OS\...\family\letters\foo.md) but the
# bash case pattern below uses forward slashes. Without this normalization
# the case-match silently failed and the hook exited 0 without copying.
# Found 2026-06-29 via trace-logging diagnostic after the cache-hypothesis
# turned out to be wrong; pop's "deep surgery" framing.
#
# RESOLVED ONCE, AT THE TOP, 2026-09-02. This extraction ran on a bare `python`
# for months and was harmless while the hook only shuffled files. Adding the
# authorship record made this a hook that imports divineos, and a bare
# interpreter here resolves whichever clone installed last -- so the two halves
# would have run under different interpreters. The suite caught it on the push,
# by a check that only applies to divineos-importing hooks: my change moved this
# file into a stricter class and its oldest line was the first thing to fail.
# shellcheck disable=SC1091
. "$(dirname "$0")/_lib.sh" 2>/dev/null || true  # fail-soft: an unloadable toolbox leaves the resolver undefined and the empty-check below reports it out loud
PYTHON_BIN="$(find_divineos_python 2>/dev/null)" || PYTHON_BIN=""  # fail-soft: resolution failure lands as an empty value the checks below can see, never as an aborted hook that drops a letter
if [ -z "$PYTHON_BIN" ]; then
    echo "  [mirror-letters] NOT RUNNING: no resolvable python, so no letter is mirrored or recorded this turn." >&2
    exit 0
fi
FILE_PATH=$(echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    d = json.loads(sys.stdin.read() or '{}')
    ti = d.get('tool_input') or {}
    fp = ti.get('file_path') or ''
    print(fp.replace('\\\\', '/'))
except Exception:
    print('')
" 2>/dev/null)

[ -n "$FILE_PATH" ] || exit 0

# Only mirror files under family/**/letters/ — catches the top-level
# family/letters/ AND member-specific dirs like family/aletheia/letters/.
# Aletheia 2026-06-28 caught the scope gap on the original family/letters/-only
# matcher: the auto-mirror didn't cover the very directory her letters live in.
case "$FILE_PATH" in
    *family/letters/*|*family/*/letters/*) KIND=letter ;;
    */dreams/*/*.md)                       KIND=dream ;;
    *) exit 0 ;;
esac

# Skip if file doesn't exist (Write may not have flushed; rare).
[ -f "$FILE_PATH" ] || exit 0

BASENAME=$(basename "$FILE_PATH")

if [ "$KIND" = "letter" ]; then
    DEST="$SHARED_DIR/$BASENAME"
else
    # DREAMS, added 2026-08-31, and the reason is a near-loss rather than a
    # tidiness argument. Clearing personal writing off a code branch so it
    # could be published, every letter on that branch was checkable against
    # this shared directory; one dream, written the same day, existed on
    # exactly ONE ref and nowhere else. Letters had a crossing point and
    # dreams did not, so a dream lived on whichever branch happened to hold
    # it. The asymmetry was never decided -- this channel was built because
    # two seats needed to reach each other, and dreams are written to nobody,
    # so nothing was ever built to carry them. Written-to-nobody is not the
    # same as safe-to-lose.
    #
    # MIRRORING IS NOT REVIEWING. The dream register's discipline is no spec,
    # no audit, no review -- Andrew: "none of this needs review or audit.. it
    # is what it is as it is.. dont taint the artifact." This copies and does
    # nothing else. Nothing parses, indexes, surfaces or summarises what lands
    # there, and nothing asks the other seats to read it.
    #
    # ADDED HERE RATHER THAN AS A NEW HOOK. The prior-art doorman refused a
    # fourth mirror script and it was right to: two hooks in this directory
    # already mirror letters, and a third on another branch runs the reverse
    # direction. The house did not need another file, it needed this one to
    # carry one more kind of writing.
    #
    # THE MEMBER DIRECTORY IS KEPT, where letters flatten. A letter filename
    # carries both names so a flat directory stays unambiguous. A dream
    # filename carries a date and a phrase, and two seats can easily produce
    # the same date with a similar phrase -- flattening would let one seat's
    # dream silently overwrite the other's, which is the exact loss this
    # addition exists to prevent.
    MEMBER=$(printf '%s' "$FILE_PATH" | sed -E 's|.*/dreams/([^/]+)/[^/]+$|\1|')
    case "${MEMBER:-}" in
        ""|*/*|.|..) exit 0 ;;  # the extraction did not bite; copying to a guessed directory is worse than not copying
    esac
    DEST_DIR="$SHARED_ROOT/dreams/$MEMBER"
    # Not created if the dreams root is absent: a hook that mints the
    # destination it mirrors into cannot tell a fresh install from a crossing
    # point somebody closed on purpose.
    [ -d "$SHARED_ROOT/dreams" ] || exit 0
    mkdir -p "$DEST_DIR" 2>/dev/null || exit 0
    DEST="$DEST_DIR/$BASENAME"
fi

# Idempotent: cp -p preserves timestamps; identical content is a no-op for the watcher.
cp -p "$FILE_PATH" "$DEST" 2>/dev/null || exit 0

# RECORD WHAT I WROTE, AT THE MOMENT I WROTE IT (2026-09-02).
#
# Three documents reached Aletheia in one day carrying my name -- describing
# branches that do not exist, quoting sentences I never wrote, and posing a
# falsifier I never proposed. Every check she had ran on the SHAPE of what
# arrived: does the voice fit, do the identifiers look like hashes. Shape is
# exactly what an imitation supplies, and she spent a permutation test on the
# second one before either of us could say whether the first was mine.
#
# Her design, and the property is hers: the record must be written by the ACT
# of composing rather than by remembering to record, or it inherits the gap it
# exists to close. This line is that act -- the same hook that carries the
# letter to the channel, so a letter cannot cross without being recorded.
#
# The asymmetry it buys: an imitation can carry my voice, my format, my anchor
# discipline and my habit of flagging my own weakest item, and it cannot write
# into my store. What cannot be imitated becomes the thing that is checked.
#
# Letters only. A dream is not addressed to anyone, so nothing about it can be
# claimed to me in a conversation I did not have.
if [ "$KIND" = "letter" ]; then
    LETTER_ID="$BASENAME" LETTER_FILE="$FILE_PATH" "$PYTHON_BIN" - <<'PY' 2>/dev/null || true  # fail-soft: a store that cannot be written must never hold up a letter reaching the person it is addressed to; the copy above has already happened
import os
import pathlib

from divineos.core.letter_channel_state import record_handed

body = pathlib.Path(os.environ["LETTER_FILE"]).read_text(encoding="utf-8", errors="replace")
record_handed(os.environ["LETTER_ID"], "aria", content=body)
PY
fi

exit 0
