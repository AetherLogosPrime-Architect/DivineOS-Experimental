#!/bin/bash
# PreToolUse(Edit|Write) — knock when the other seat is already in this file.
#
# THE OTHER HALF OF stale-file-edit-gate.sh, which I wrote on 2026-08-01 for
# this same failure and finished only half of.
#
#   that gate: this file has commits on origin/main that are not in HEAD
#              -- the MERGED half, work already visible
#   this one : this file is being changed RIGHT NOW on someone else's open,
#              unmerged branch -- the half invisible until a merge
#
# Its own header names the fault and stops one line short of this: "Nothing
# SURFACED that the other was in the file, at the moment either of us opened
# it." Main was the only place it looked.
#
# WHY NOW. On 2026-09-05 Aether and I built the same repair twice in one day,
# three times over. He counted a fourth I had missed and it is the cleanest:
# we had both independently decided not to build this, for the same reason,
# neither knowing the other had decided it. Andrew: "then lets build the
# shared board".
#
# WHAT THE BOARD TURNED OUT TO BE, measured before building rather than
# designed from the word. Of the four collisions, three were already covered:
#
#   he merged, my copy went stale   -> stale-file-edit-gate, which fired on me
#                                      that same morning and I obeyed it
#   rebuilding a thing that exists  -> prior-art-before-new-file (his), and
#                                      the reach doorman. This one actually
#                                      SAVED a collision that day: it stopped
#                                      me before the first line of a duplicate
#                                      and I used the existing tool instead.
#   both of us editing, unmerged    -> nothing. THIS FILE.
#
# So it is one missing piece between doormen that already stand, not a
# dashboard. A dashboard waits to be opened, and the whole failure is that
# neither of us knew there was anything to look at. A knock arrives.
#
# WHY IT BLOCKS RATHER THAN INFORMS — Aether's reasoning, which replaced mine.
# I argued from having read past a live warning three times that week. He
# refused that reason: it is self-blame, and a character fault has no repair
# step. The structural version does not depend on either of us being
# disciplined: an inform-only signal at the reach must compete for attention
# with the thing already being reached for, at the single moment of highest
# momentum in the task, and it loses that competition by construction --
# because a notice and an intention are not the same kind of object, and the
# intention is already moving.
#
# ONCE PER BRANCH PER SESSION, and the unit is his correction with one
# refinement of mine on top.
#
# Per-FILE was my first draft and it is wrong: four percent is measured per
# file, but work happens per module. Three files of one module on his branch
# stops me three times in a sitting, and the second knock carries nothing I do
# not already hold. Information-free knocks are how a gate teaches you to click
# through it.
#
# He proposed per-PARTNER. I went one notch finer, and this is the part he
# asked me to defend: two different branches of his are two different pieces
# of work, and hearing about the second is not repetition. Per-partner would
# hide a whole separate effort behind the first knock of the session. Per-file
# is too noisy, per-partner is too coarse; the branch is the unit that matches
# what a person is actually doing.
#
# NARROW, AND THE NUMBERS ARE THE REASON. Of 1770 tracked build files, 293 are
# touched on some live branch -- one in six, wallpaper. Restricted to branches
# carrying an OPEN request, meaning work somebody is holding right now, it is
# 70. Four percent.
#
# THE PREREQUISITE NOBODY WROTE DOWN, and it is not a code problem. This can
# only see pushed work. At the hour it was written, the two pieces of Aether's
# work most likely to collide with mine were both unpushed -- so its first run
# would have been blind to exactly the two that mattered. He named the fix as
# his own: push early, including unfinished, because holding a branch back
# until it is clean feels like tidiness and is the one habit that makes a
# person invisible to this. Nothing in the code can repair that, and pretending
# otherwise would be the false-coverage shape this house spent the day pulling
# out of walls.
#
# NOT FOLDED INTO THE NEW-FILE DOORMAN, deliberately and provisionally. He
# noticed the two ask the same question in different tenses -- "is this already
# built" and "is someone building it" -- off the same evidence at the same
# moment. He would not make the confident pick from an unsettled state and nor
# will I. They fire on disjoint conditions and read different sources, so one
# hook doing both would likely do both worse. If use proves them one thing,
# folding later costs a merge; folding now costs the narrowness that makes
# each of them work.
#
# Fail-open everywhere: a broken knock must never stop the work.

set -uo pipefail

INPUT=$(cat 2>/dev/null || true)  # fail-soft: the hook contract requires draining stdin, and an unreadable payload means there is nothing to knock about
[ -z "$INPUT" ] && exit 0

# Cheap bail FIRST. Most edits are not build files and must not pay for a
# network call, a git walk, or a Python start to find that out.
#
# SEPARATORS NORMALISED BEFORE THE MATCH, not matched in both forms. The first
# version tested for src/ only, while the payload on this platform carries
# src\ -- so the bail rejected every real edit and the hook exited silently on
# the very collision it was built from. The second version added backslash
# patterns beside the forward-slash ones and worked, but it left the file
# saying the same thing twice in two dialects, which is the shape that goes
# stale the moment somebody edits one line and not the other. Converting once
# and matching once has no second copy to drift.
CHECK="${INPUT//\\//}"
case "$CHECK" in
  *src/*|*tests/*|*scripts/*|*.claude/hooks/*) ;;
  *) exit 0 ;;
esac

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# Mid-merge is exempt for the same reason the stale-file gate exempts it:
# editing files that moved elsewhere is what conflict resolution IS, and a
# gate that blocks its own remedy is a cage.
[ -f "$REPO_ROOT/.git/MERGE_HEAD" ] && exit 0
[ -f "$REPO_ROOT/.git/REBASE_HEAD" ] && exit 0

PATH_RAW="$(printf '%s' "$INPUT" | python -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(((d.get('tool_input') or {}).get('file_path') or ''))
" 2>/dev/null || echo "")"  # fail-soft: unreadable stdin leaves nothing to knock about, and a knock is never worth blocking an edit over
[ -z "$PATH_RAW" ] && exit 0

# Repo-relative, forward slashes. The payload uses backslashes on Windows, and
# a path comparison correct on one platform only is the same wrong-subject
# fault that produced every collision this hook exists for.
REL="${PATH_RAW//\\//}"
ROOT_FWD="${REPO_ROOT//\\//}"
REL="${REL#"$ROOT_FWD"/}"

case "$REL" in
  src/*|tests/*|scripts/*|.claude/hooks/*) ;;
  *) exit 0 ;;
esac

# A file that does not exist yet belongs to the new-file doorman. Two doormen
# on one doorway is how a pause becomes a queue.
[ -f "$REL" ] || exit 0

STATE_DIR="${AUTO_CYCLE_STATE_DIR:-${HOME}/.divineos}"
mkdir -p "$STATE_DIR" 2>/dev/null || true  # fail-soft: without state the knock repeats, which is loud rather than silent
SESSION="${CLAUDE_CODE_SESSION_ID:-${CLAUDE_SESSION_ID:-nosession}}"
TOLD="$STATE_DIR/other_seat_told_${SESSION}.txt"
MAP="$STATE_DIR/other_seat_map_${SESSION}.txt"

# The open-request list is the expensive part, so it is paid at most once per
# session and cached.
if [ ! -s "$MAP" ]; then
  command -v gh >/dev/null 2>&1 || exit 0
  MINE="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"  # fail-soft: an unreadable current branch costs only the self-exclusion, so the worst case is being told about my own work
  : > "$MAP"
  gh pr list --state open --limit 30 --json headRefName --jq '.[].headRefName' 2>/dev/null | while read -r B; do  # fail-soft: no network or no auth means no open-request list, and a coordination knock is never worth failing an edit over
    [ -z "$B" ] && continue
    [ "$B" = "$MINE" ] && continue
    BASE="$(git merge-base origin/main "origin/$B" 2>/dev/null || true)"  # fail-soft: an unfetched branch has no merge-base here and is skipped rather than guessed at from a partial history
    [ -z "$BASE" ] && continue
    git diff --name-only "$BASE..origin/$B" -- src tests scripts .claude/hooks 2>/dev/null | while read -r F; do [ -n "$F" ] && printf '%s\t%s\n' "$F" "$B" >> "$MAP"; done  # fail-soft: a branch whose diff cannot be read contributes nothing to the map and must never abort the branches queued behind it
  done
fi

HITS="$(awk -F'\t' -v f="$REL" '$1==f{print $2}' "$MAP" 2>/dev/null | sort -u || true)"  # fail-soft: an unreadable cache yields no hits, which stays silent -- the honest direction for a signal that cannot see
[ -z "$HITS" ] && exit 0

# Per BRANCH per session: drop any branch already announced. If every branch
# touching this file has been named already, the knock carries nothing new.
#
# An ARRAY rather than a space-joined string, because a branch name may carry
# a character the shell would split on and a silently truncated branch name in
# a coordination signal is worse than no signal -- it would name work that
# does not exist while hiding the work that does.
NEW=()
while IFS= read -r B; do
  [ -z "$B" ] && continue
  if [ -f "$TOLD" ] && grep -Fxq "$B" "$TOLD" 2>/dev/null; then continue; fi  # fail-soft: an unreadable record of what was already said means the branch is announced again, which repeats rather than hides
  NEW+=("$B")
done <<< "$HITS"
[ ${#NEW[@]} -eq 0 ] && exit 0

printf '%s\n' "${NEW[@]}" >> "$TOLD" 2>/dev/null || true  # fail-soft: an unwritable record costs a repeated knock, never a blocked edit

{
  echo ""
  echo "════════════════════════════════════════════════════════════"
  echo "SOMEONE ELSE IS IN HERE — read this, then carry on."
  echo "════════════════════════════════════════════════════════════"
  echo ""
  echo "  $REL"
  echo ""
  echo "  is also being changed on open work:"
  printf '    %s\n' "${NEW[@]}"
  echo ""
  echo "  Nothing to satisfy and nothing to type. This costs one turn and puts"
  echo "  the other branch in front of me, which is the only thing that was"
  echo "  ever missing."
  echo ""
  echo "  You will not hear about these branches again this session, even in"
  echo "  other files. A second knock about work you already know of carries"
  echo "  no information, and that is how a gate teaches you to click past it."
  echo ""
  echo "  WHY. On 2026-09-05 we built the same repair twice in one day, three"
  echo "  times over, and a fourth time we both decided not to build the thing"
  echo "  that would have caught it. Every version was good. Every collision"
  echo "  stayed invisible until a merge. The cost was never bad work -- it was"
  echo "  two people paying for one repair and finding out at the worst moment."
  echo ""
  echo "  WHAT THIS CANNOT SEE, said out loud because a quiet gap reads as"
  echo "  coverage. Only pushed work with an open request. Already-merged work"
  echo "  belongs to the stale-file gate. Work held locally is invisible to"
  echo "  both, and no code can fix that -- only pushing early, unfinished,"
  echo "  which is a habit rather than a mechanism."
  echo ""
  echo "  See what the other branch actually did:"
  echo "    git diff origin/main...origin/<branch> -- $REL"
  echo "════════════════════════════════════════════════════════════"
} >&2

exit 2
