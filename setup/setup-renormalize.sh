#!/usr/bin/env bash
# setup/setup-renormalize.sh — fix CRLF line endings on a Windows checkout.
#
# Background: this repo declares .sh and .py files as LF-only via .gitattributes
# (eol=lf). On Windows, however, a clone done before that .gitattributes rule
# was added — or a clone done with core.autocrlf=true — leaves the worktree
# files with CRLF endings even though git's blobs are LF. shellcheck and
# similar tools that read the worktree (not the index) then fire SC1017
# "Literal carriage return" errors on every line of every .sh file.
#
# git add --renormalize . only produces diffs when the BLOBS need updating.
# When blobs are already LF and the worktree is CRLF, renormalize is a no-op.
# This script explicitly rewrites worktree files to match the blob line endings.
#
# Run after a fresh Windows clone. Safe to re-run; idempotent.
#
# Filed 2026-05-16 after CRLF false-alarms blocked an unrelated commit
# during the multiplex MVP arc. Discipline: Windows devs run this once
# at clone time, OR set git config --global core.autocrlf input so future
# clones never hit the problem.

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "=== DivineOS CRLF renormalization ==="
echo "Repo: $REPO_ROOT"

# Step 1: set core.autocrlf to input for this repo (commit LF, checkout LF)
echo ""
echo "[1/3] Setting core.autocrlf=input for this repo..."
git config core.autocrlf input
echo "  done."

# Step 2: scan tracked text files for CRLF and build a tmp list
echo ""
echo "[2/3] Scanning tracked text files for CRLF..."
TMP_LIST="$(mktemp)"
trap 'rm -f "$TMP_LIST"' EXIT

git ls-files "*.sh" "*.py" "*.md" "*.json" "*.toml" "*.yml" "*.yaml" "*.txt" "*.cfg" | while IFS= read -r f; do
    if [ -f "$f" ] && grep -qlU $'' "$f" 2>/dev/null; then
        printf '%s
' "$f" >> "$TMP_LIST"
    fi
done

COUNT="$(wc -l < "$TMP_LIST" | tr -d ' ')"

if [ "$COUNT" -eq 0 ]; then
    echo "  no CRLF found. Worktree is already clean."
    exit 0
fi

echo "  found $COUNT files with CRLF line endings (first 20):"
head -20 "$TMP_LIST" | sed 's/^/    /'
if [ "$COUNT" -gt 20 ]; then
    echo "    ... and $((COUNT - 20)) more"
fi

# Step 3: strip CRLF in-place via stdin (bypasses ARG_MAX for large repos)
echo ""
echo "[3/3] Stripping CRLF in-place..."
python3 -c "
import sys, pathlib
fixed = 0
for line in sys.stdin:
    f = line.rstrip(chr(10))
    if not f:
        continue
    p = pathlib.Path(f)
    try:
        data = p.read_bytes()
        if b'
' in data:
            p.write_bytes(data.replace(b'
', b'
'))
            fixed += 1
    except OSError as e:
        print('  skip ' + f + ': ' + str(e), file=sys.stderr)
print('  normalized ' + str(fixed) + ' files')
" < "$TMP_LIST"

echo ""
echo "=== Done ==="
echo "Verify with: git diff --stat"
echo "If git diff shows changes, the repo blobs were also CRLF; commit with:"
echo "  git commit -m 'chore: normalize line endings to LF'"
echo "If git diff is empty, only the worktree was stale — no commit needed."
