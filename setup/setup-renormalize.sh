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


# Step 2+3: find and convert, in ONE Python process.
#
# REWRITTEN 2026-08-24 after running this script against a worktree it was
# written to fix and watching it do nothing. Three defects, all now gone:
#
#   1. STEP 3 NEVER RAN. It invoked `python3`, which on Windows is a Microsoft
#      Store shim that prints an install advert and exits non-zero. Silent
#      no-op on the platform this script exists for.
#
#   2. THE REPLACEMENT PAIR HAD BEEN EATEN. The old code embedded RAW CR and LF
#      bytes as Python literals inside a double-quoted shell string. The pair
#      was b'\r\n' -> b'\n'; because that CR was followed by a LF it WAS a CRLF
#      sequence, so this repo's own LF-normalization collapsed it to
#      b'\n' -> b'\n' -- a no-op. The line-ending fixer was destroyed by
#      line-ending normalization. Escapes inside a QUOTED heredoc (<<'PYEOF')
#      are immune: the shell performs no expansion at all, and there are no
#      raw CR bytes left to collapse.
#
#   3. THE SCAN SPAWNED ONE grep PER FILE. 5562 tracked text files at ~47ms of
#      Windows process-spawn each is ~260 seconds, so it read as a hang and got
#      killed before reaching step 3 anyway. Python does the whole walk in one
#      process.
#
# Verified before shipping, against real fixtures in a throwaway git repo:
# CRLF file converted, LF file untouched, and a .txt containing NUL bytes
# SKIPPED with its CRLF intact (the block case, exercised -- not assumed).
echo ""
echo "[2/2] Scanning and normalizing tracked text files..."

# `python3` is the broken shim here; `python` is the real interpreter. Probe by
# executing, not by presence -- the shim exists on PATH and still fails.
PY_BIN=""
for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "" >/dev/null 2>&1; then
        PY_BIN="$c"
        break
    fi
done
if [ -z "$PY_BIN" ]; then
    echo "  ERROR: no working Python found (tried python3, python, py)." >&2
    echo "  Cannot normalize. Install Python or disable the Store alias." >&2
    exit 1
fi
echo "  interpreter: $PY_BIN"

"$PY_BIN" <<'PYEOF'
import pathlib
import subprocess
import sys

PATTERNS = ["*.sh", "*.py", "*.md", "*.json", "*.toml",
            "*.yml", "*.yaml", "*.txt", "*.cfg"]

# -z: NUL-delimited, so paths containing spaces or newlines survive intact.
out = subprocess.run(
    ["git", "ls-files", "-z", "--"] + PATTERNS,
    capture_output=True, check=True,
).stdout
files = [f for f in out.decode("utf-8", "surrogateescape").split("\0") if f]

fixed, binary, missing = [], 0, 0
for name in files:
    p = pathlib.Path(name)
    try:
        data = p.read_bytes()
    except OSError as e:
        missing += 1
        print(f"  skip {name}: {e}", file=sys.stderr)
        continue
    # A NUL byte means this is not text no matter what the extension claims.
    # Rewriting it would corrupt content this script has no business touching.
    if b"\x00" in data:
        binary += 1
        continue
    if b"\r\n" not in data:
        continue
    p.write_bytes(data.replace(b"\r\n", b"\n"))
    fixed.append(name)

print(f"  scanned {len(files)} tracked text file(s)")
if not fixed:
    print("  no CRLF found -- worktree already clean.")
else:
    print(f"  normalized {len(fixed)} file(s):")
    for name in fixed[:20]:
        print(f"    {name}")
    if len(fixed) > 20:
        print(f"    ... and {len(fixed) - 20} more")
if binary:
    print(f"  skipped {binary} file(s) containing NUL bytes (not text)")
if missing:
    print(f"  skipped {missing} unreadable file(s) -- see stderr")
PYEOF

echo ""
echo "=== Done ==="
echo "Verify with: git status --porcelain"
echo "Empty means only the worktree was stale -- nothing to commit."
echo "Any output means the blobs were CRLF too; commit with:"
echo "  git commit -m 'chore: normalize line endings to LF'"
