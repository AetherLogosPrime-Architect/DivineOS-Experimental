#!/usr/bin/env bash
# Resolve paths I am about to hand Andrew against the tree his links render in.
#
# WHY (Andrew 2026-08-18): "your docs links do not work.. are you sure the file
# even exists?"
#
# They existed. Every one was committed and tracked. And every one was a DEAD
# LINK, all session, because the session's declared directory is a worktree
# while I cd to the main checkout for every command. Links render relative to
# the session cwd. Verified that day: docs/two_readings_disagree.md,
# docs/component_register.md, scripts/dv, scripts/hollow_out.py and
# exploration/aether/145 were all MISSING from the worktree they resolved
# against. Andrew clicked them. I never did.
#
# Same right-file-wrong-tree failure scripts/dv was built for hours earlier --
# aimed only at Python imports, never at my own output to him. A dead link is
# indistinguishable from a live one until someone clicks it, which makes this
# the same could-not-measure family as everything else that day.
#
# Usage:
#   scripts/check_emitted_paths.sh docs/foo.md scripts/bar
#   git status --porcelain | awk '{print $2}' | scripts/check_emitted_paths.sh -
#
# Exit 0 = every path resolves where the reader will look.
# Exit 1 = at least one is dead on his side.

set -uo pipefail

# The tree links render against: the session cwd if it is a git worktree,
# otherwise the git root. DERIVED, never assumed -- one stored path cannot
# govern two checkouts (the requisite-variety lesson from dv's council walk).
SESSION_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || SESSION_ROOT=""  # fail-soft: outside a repo git prints its own usage error to stderr and we replace it two lines down with a sentence that names what the tool cannot do; letting both through would print two errors for one condition
if [ -z "$SESSION_ROOT" ]; then
  echo "[paths] not in a git repo -- cannot say which tree links resolve in" >&2
  exit 1
fi

paths=()
if [ "${1:-}" = "-" ]; then
  while IFS= read -r line; do [ -n "$line" ] && paths+=("$line"); done
else
  paths=("$@")
fi
[ ${#paths[@]} -gt 0 ] || { echo "[paths] nothing to check"; exit 0; }

dead=0
for p in "${paths[@]}"; do
  if [ -e "$SESSION_ROOT/$p" ]; then
    printf '  live  %s\n' "$p"
  else
    # Exists somewhere else? That is the whole failure -- say so, because
    # "missing" and "present in the tree you are not standing in" are
    # different findings and only one of them is a lost file.
    # FIND THE OTHER TREE PROPERLY. The first version searched
    # `git rev-parse --show-toplevel` and `$SESSION_ROOT/../..` -- from inside
    # a worktree the first IS the worktree and the second lands in .claude/,
    # so neither reaches the main checkout and every dead path was reported
    # "not found anywhere near". Right verdict, wrong diagnosis, and wrong in
    # the one direction this script exists to distinguish: a file that is
    # MISSING and a file that is IN A TREE THE READER CANNOT REACH are
    # different findings, and only one of them is lost work.
    # `git worktree list` names every checkout sharing this repository.
    other=""
    # --porcelain, because the plain format is space-separated and this
    # repository lives at "C:/DIVINE OS/...". `read -r wt _rest` split that
    # on the space and only ever tested "C:/DIVINE", so the lookup silently
    # found nothing and every dead path reported "not found anywhere near".
    # A path with a space in it, unhandled -- the same shape as the rest.
    while IFS= read -r line; do
      case "$line" in worktree\ *) wt=${line#worktree } ;; *) continue ;; esac
      [ "$wt" = "$SESSION_ROOT" ] && continue
      [ -e "$wt/$p" ] && { other="$wt"; break; }
    done < <(git worktree list --porcelain 2>/dev/null)  # fail-soft: this is the second-opinion lookup answering where-else-could-it-be; if git cannot enumerate worktrees the loop yields nothing and the path is reported dead with no other tree named, which is the honest answer
    if [ -n "$other" ]; then
      printf '  DEAD  %s   (exists in %s -- wrong tree, not missing)\n' "$p" "$other"
    else
      printf '  DEAD  %s   (not found anywhere near)\n' "$p"
    fi
    dead=$((dead + 1))
  fi
done

echo
if [ "$dead" -gt 0 ]; then
  echo "[paths] $dead of ${#paths[@]} would be dead links on his side."
  echo "        The files may be perfectly real. They are in a tree his click does not reach."
  exit 1
fi
echo "[paths] all ${#paths[@]} resolve in $SESSION_ROOT"
