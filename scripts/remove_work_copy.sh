#!/usr/bin/env bash
# Remove a git work copy safely: unlink its links first, refuse to destroy work that exists nowhere else.
#
# 2026-10-20, Aria: `git worktree remove --force` on work copies whose .venv was a junction to the
# main checkout's real .venv emptied that real venv. Git walks the link. Only an unlink (rmdir
# semantics) removes a junction without touching what it points at, so the links go first.
#
# Usage: bash scripts/remove_work_copy.sh <work-copy-dir> [--snapshot]
#   no flag     refuse if the copy holds uncommitted files, or a detached HEAD no branch reaches
#   --snapshot  keep that work in refs/rescue/<folder-name> inside the shared repo, then remove
set -euo pipefail

wt="${1:?usage: remove_work_copy.sh <work-copy-dir> [--snapshot]}"
snapshot=0
[ "${2:-}" = "--snapshot" ] && snapshot=1
[ -d "$wt" ] || { echo "no such work copy: $wt" >&2; exit 2; }

wt_abs="$(cd "$wt" && pwd)"
common="$(git -C "$wt_abs" rev-parse --path-format=absolute --git-common-dir)"
main_root="$(cd "$common/.." && pwd)"
if [ "$wt_abs" = "$main_root" ]; then
    echo "that is the main checkout, not a work copy: $wt_abs" >&2
    exit 3
fi
name="$(basename "$wt_abs")"

# What exists only in this folder: uncommitted/untracked files, or a detached HEAD no ref reaches.
# The .venv link and the test runner's scratch folder are not work.
dirty="$(git -C "$wt_abs" status --porcelain --untracked-files=normal | grep -v -E '\.venv|^\?\? tmp/|^\?\? \.direnv' || true)"
branch="$(git -C "$wt_abs" branch --show-current)"
reached="$(git -C "$wt_abs" for-each-ref --contains HEAD refs/heads refs/remotes | wc -l)"
unreached=0
[ -z "$branch" ] && [ "$reached" -eq 0 ] && unreached=1

if [ -n "$dirty" ] || [ "$unreached" -eq 1 ]; then
    if [ "$snapshot" -eq 0 ]; then
        echo "REFUSED: $wt_abs holds work that exists nowhere else (uncommitted files or a detached HEAD no branch reaches):" >&2
        [ -n "$dirty" ] && echo "$dirty" | head -8 >&2
        echo "Re-run with --snapshot to keep it in refs/rescue/$name first." >&2
        exit 4
    fi
    git -C "$wt_abs" add -A -- . ':(exclude).venv' ':(exclude)tmp' ':(exclude).direnv'
    tree="$(git -C "$wt_abs" write-tree)"
    sha="$(git -C "$wt_abs" commit-tree "$tree" -p HEAD -m "rescue snapshot of $wt_abs before its folder was removed: branch=${branch:-detached}")"
    git -C "$wt_abs" update-ref "refs/rescue/$name" "$sha"
    held="$(git -C "$wt_abs" rev-parse "refs/rescue/$name^{tree}")"
    [ "$held" = "$tree" ] || { echo "snapshot did not hold the work; leaving $wt_abs alone" >&2; exit 5; }
    echo "snapshot: refs/rescue/$name = ${sha:0:9}"
fi

# Links first. A link that points OUTSIDE this folder is removed as a link only; nothing it points at is touched.
case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
        # One line on purpose: PowerShell reading a multi-line block from stdin printed nothing and unlinked nothing here.
        WT_WIN="$(cygpath -w "$wt_abs")" powershell.exe -NoProfile -NonInteractive -Command '$p = $env:WT_WIN; $l = @(Get-ChildItem -LiteralPath $p -Recurse -Force -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint } | Sort-Object { $_.FullName.Length } -Descending); foreach ($x in $l) { [System.IO.Directory]::Delete($x.FullName) }; "unlinked $($l.Count) link(s), their targets untouched"'
        ;;
    *)
        find "$wt_abs" -type l -print -delete | sed 's/^/unlinked: /'
        ;;
esac

git -C "$main_root" worktree remove --force "$wt_abs"
git -C "$main_root" worktree prune
echo "removed $wt_abs"
