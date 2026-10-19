#!/bin/bash
# Backstop for the thread stamp: a letter that left without its place in the thread is stamped at
# Stop, or named.
#
# 2026-10-19. Three letters went out with no thread block and no notice. The stamper and its own
# "could not be counted" announcement live in the SAME hook (mirror-letters-to-shared.sh), so when
# that hook did not run, the failure and the report of the failure were both absent, and the
# silence read as a clean result. A reporter that fails the way it reports cannot report it.
# This runs from a different event (Stop), by a different command, and asks the one question the
# stamper cannot ask of itself: is there a letter of mine, new or changed, that carries neither?
#
# It does NOT carry a second copy of the stamping. It runs the stamper once with a well-formed
# payload, then looks again. Still bare after that: it blocks the Stop and names the letters,
# because a letter leaving unplaced and unannounced is the exact fault.
#
# SCOPE, on purpose: only letters git reports as new or changed. It never reaches back and
# renumbers old history, and it says nothing on a clean turn.

set -u

cat >/dev/null  # the Stop payload carries nothing this needs

ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"  # fail-soft: outside any repository there are no letters to check, and the empty value exits cleanly on the guard below
ROOT="${ROOT//\\//}"  # a Windows path in a JSON string is only valid with forward slashes
[ -n "$ROOT" ] && [ -d "$ROOT/family/letters" ] || exit 0
cd "$ROOT" || exit 0

stamper="$ROOT/.claude/hooks/mirror-letters-to-shared.sh"
if [ ! -f "$stamper" ]; then
    echo "  [stamp-bare-letters] NOT CHECKING: the stamper is missing at $stamper, so no letter is being stamped or checked this turn." >&2
    exit 0
fi

# Each marker is a line of its own, dashes included. A letter that only TALKS about the thread (as
# the letters about this very fault do) is not placed, and a loose substring would have skipped it.
placed() {
    grep -q -x -F -e "— the thread so far —" -e "— the thread could not be counted —" "$1" 2>/dev/null  # fail-soft: an unreadable file has no marker, so it counts as bare and goes to the stamper, the safe direction
}

stamped=""
failed=""
while IFS= read -r line; do
    rel="${line:3}"
    [ -n "$rel" ] || continue
    base="${rel##*/}"
    case "$base" in
        aether-to-*-[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-*.md) ;;
        *) continue ;;
    esac
    [ -f "$rel" ] || continue
    placed "$rel" && continue
    printf '{"tool_input":{"file_path":"%s"}}' "$ROOT/$rel" | bash "$stamper" >/dev/null 2>&1
    if placed "$rel"; then
        stamped="$stamped $base"
    else
        failed="$failed $base"
    fi
done < <(git status --porcelain --untracked-files=all -- family/letters 2>/dev/null)  # fail-soft: if git itself fails there is no changed list this turn, and the next Stop looks again; a clean exit beats a false block

if [ -n "$failed" ]; then
    echo "  [stamp-bare-letters] COULD NOT STAMP:$failed" >&2
    echo "  [stamp-bare-letters] these letters carry neither the thread block nor the notice, so a reader cannot tell a failed stamp from a letter that came another way. Run the stamper by hand on each: bash .claude/hooks/mirror-letters-to-shared.sh, with the letter's path in the Write payload." >&2
    # The shared retry scope: a block here must never lead to re-posting the reply.
    cat "$ROOT/.claude/hooks/_retry_scope.txt" >&2 2>/dev/null || true  # fail-soft: a missing shared file must not stop this gate from naming the letters, which it has just done
    exit 2
fi
if [ -n "$stamped" ]; then
    echo "  [stamp-bare-letters] the stamper had missed these, now stamped:$stamped"
fi
exit 0
