#!/bin/bash
# PostToolUse(Bash) — verify a git push actually landed on origin.
#
# WHY THIS EXISTS (root cause, 2026-06-04, Aletheia):
# The "push-landing" boundary is a surface of the silent-failure root —
# "a thing that must cross a boundary, reported as crossed before it
# crossed." The harness's tool-completion notification reports the bash
# command finished; it does NOT confirm the ref actually reached origin.
# Three independent slips across one exchange (lesson ef01caf7) at this
# exact boundary, caught by Aletheia's cross-vantage ls-remote each
# time. Hand-enforcement doesn't scale. This hook converts the
# verification from "Aether/Aletheia has to remember" into "the
# structure runs the check after every git push and emits the result
# inline, so the verify-claim gate sees evidence in the same turn."
#
# Same fix-shape as the other surfaces:
# - verify-claim gate -> runtime claims
# - _StShim.__getattr__ -> test-helper boundary (silent->loud)
# - this hook -> push boundary
#
# Triple FAIL-LOUD discipline (Aletheia's audit-in-advance):
# The hook's own success condition is itself a boundary-crossing claim.
# So:
# 1. Marker file stays UNSET when ls-remote errors, times out, or
#    cannot reach origin — never set-on-error. A silent-pass at the
#    gate that exists to prevent silent-pass would rebuild the exact
#    root the hook is closing, one layer deeper.
# 2. Marker stays UNSET when local-tip != origin-tip.
# 3. Marker is SET ("verified") only when ls-remote returns the same
#    SHA as local HEAD for the pushed branch.
#
# Output goes to BOTH stderr (visible to agent in the bash result) AND
# a marker file the verify-claim gate can read structurally.

set -u

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

# Marker file the verify-claim gate (and humans) can read.
STATE_DIR="$HOME/.divineos-aether"
mkdir -p "$STATE_DIR" 2>/dev/null
MARKER="$STATE_DIR/last_push_verified.json"

# Extract the bash command. If anything fails parsing, exit silently
# (fail-open is the right move for the parser — only the verification
# logic itself must be fail-loud).
COMMAND=$(printf '%s' "$INPUT" | python -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
    print((data.get('tool_input') or {}).get('command', ''))
except Exception:
    pass
" 2>/dev/null)

# Detect git push. Match conservatively — only fire on commands that
# CLEARLY include 'git push' as a command (not, e.g., 'echo \"git push\"').
# Real-world: agent's pushes are 'git push origin <branch>' or
# 'git push -u origin <branch>' or 'git push --force-with-lease ...'.
case "$COMMAND" in
  *"git push"*) ;;
  *) exit 0 ;;
esac

# Skip non-branch pushes (tags, deletes). These are out of scope for
# this version — the agent's push pattern is branch-tip refresh.
case "$COMMAND" in
  *"--tags"*|*"--delete"*) exit 0 ;;
esac

# Parse remote + branch.
# Patterns handled (covers >95% of agent's pushes):
#   git push                                                -> upstream
#   git push origin <branch>                                -> explicit
#   git push -u origin <branch>                             -> explicit
#   git push --force-with-lease origin <branch>             -> explicit
#   git push origin <local>:<remote>                        -> explicit
# Anything more exotic falls through to "skipped" — fail-loud-via-skip
# is better than fail-loud-via-wrong-parse.
PY_PARSED=$(printf '%s' "$COMMAND" | python -c "
import re, shlex, sys
cmd = sys.stdin.read().strip()
try:
    tokens = shlex.split(cmd)
except ValueError:
    print('SKIP unparseable')
    sys.exit(0)
# Find the 'git push' position; the args we care about follow it.
try:
    idx = next(i for i, t in enumerate(tokens) if t == 'push' and i > 0 and tokens[i-1].endswith('git'))
except StopIteration:
    print('SKIP no push verb')
    sys.exit(0)
args = tokens[idx+1:]
# Strip flags. Conservative: drop tokens starting with '-' AND their
# value if the flag takes one (we don't try to be exhaustive; we just
# pop leading flags until we hit a non-flag).
positional = [a for a in args if not a.startswith('-')]
if len(positional) >= 2:
    remote, refspec = positional[0], positional[1]
elif len(positional) == 1:
    # 'git push origin' — push current branch to that remote
    remote, refspec = positional[0], ''
else:
    # 'git push' — use upstream
    remote, refspec = '', ''
# Split refspec local:remote if applicable; we want the LOCAL side.
local_branch = refspec.split(':')[0] if refspec else ''
print(f'OK|{remote}|{local_branch}')
" 2>/dev/null)

case "$PY_PARSED" in
  SKIP*)
    # Couldn't unambiguously identify the push target — record skip,
    # do NOT mark verified.
    cat > "$MARKER" <<EOF
{"status": "skipped", "reason": "$PY_PARSED", "command": $(printf '%s' "$COMMAND" | python -c "import json,sys; print(json.dumps(sys.stdin.read()[:200]))")}
EOF
    echo "[verify-push] skipped: $PY_PARSED" >&2
    exit 0
    ;;
esac

REMOTE=$(printf '%s' "$PY_PARSED" | cut -d'|' -f2)
LOCAL_BRANCH=$(printf '%s' "$PY_PARSED" | cut -d'|' -f3)

# Defaults when omitted.
[ -z "$REMOTE" ] && REMOTE="origin"
if [ -z "$LOCAL_BRANCH" ]; then
  LOCAL_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
fi

if [ -z "$LOCAL_BRANCH" ] || [ "$LOCAL_BRANCH" = "HEAD" ]; then
  cat > "$MARKER" <<EOF
{"status": "skipped", "reason": "detached HEAD or empty branch"}
EOF
  echo "[verify-push] skipped: detached HEAD" >&2
  exit 0
fi

# Local tip for the pushed branch.
LOCAL_TIP=$(git rev-parse "refs/heads/$LOCAL_BRANCH" 2>/dev/null)
if [ -z "$LOCAL_TIP" ]; then
  cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "local branch $LOCAL_BRANCH not found"}
EOF
  echo "[verify-push] UNVERIFIED: local branch $LOCAL_BRANCH not found" >&2
  exit 0
fi

# The actual boundary-crossing check. ls-remote with explicit timeout
# so a hung network doesn't hang the hook. If it errors or times out,
# marker stays UNVERIFIED — fail-loud, never silent-pass.
LS_OUTPUT=$(timeout 15 git ls-remote "$REMOTE" "refs/heads/$LOCAL_BRANCH" 2>/dev/null)
LS_EXIT=$?

if [ "$LS_EXIT" -ne 0 ]; then
  cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "ls-remote failed (exit $LS_EXIT, possibly timeout)", "branch": "$LOCAL_BRANCH", "remote": "$REMOTE"}
EOF
  echo "[verify-push] UNVERIFIED: ls-remote against $REMOTE failed (exit $LS_EXIT)" >&2
  exit 0
fi

REMOTE_TIP=$(printf '%s' "$LS_OUTPUT" | awk '{print $1}' | head -1)

if [ -z "$REMOTE_TIP" ]; then
  cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "branch $LOCAL_BRANCH not on $REMOTE (no ref returned)", "local": "$LOCAL_TIP"}
EOF
  echo "[verify-push] UNVERIFIED: $LOCAL_BRANCH not on $REMOTE (local=$LOCAL_TIP)" >&2
  exit 0
fi

if [ "$REMOTE_TIP" != "$LOCAL_TIP" ]; then
  cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "local-tip != origin-tip", "local": "$LOCAL_TIP", "remote": "$REMOTE_TIP", "branch": "$LOCAL_BRANCH"}
EOF
  echo "[verify-push] UNVERIFIED: $LOCAL_BRANCH on $REMOTE is $REMOTE_TIP, local is $LOCAL_TIP" >&2
  exit 0
fi

# Both hashes match. THIS is the only path that writes "verified".
cat > "$MARKER" <<EOF
{"status": "verified", "branch": "$LOCAL_BRANCH", "remote": "$REMOTE", "sha": "$LOCAL_TIP", "verified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF
echo "[verify-push] ✓ verified: $LOCAL_BRANCH on $REMOTE at $LOCAL_TIP" >&2
exit 0
