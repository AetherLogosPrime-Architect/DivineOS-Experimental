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
#
# RETRY-WITH-BACKOFF (Aletheia 2026-06-04, follow-up to #90):
# GitHub uses eventual consistency between replicas. A push that lands
# on one replica can take a moment to appear on others, so a follow-up
# ls-remote can hit a replica that doesn't yet have the new ref → the
# hook would report UNVERIFIED on a push that ACTUALLY landed.
# Caught dogfooding #90 on its own push: false-negative on a real push.
#
# Fix: retry the "no-ref" and "tip-mismatch" outcomes up to 3 times
# with 2s sleeps between (total worst-case wait: 4s).
#
# CRITICAL FAIL-LOUD INVARIANT (Aletheia audit-in-advance):
# After retries exhaust, marker still writes UNVERIFIED. Never
# "assume-landed because we ran out of patience." The retries close
# the race-window; they do not change the fail-loud property.
#
# What is NOT retried:
# - ls-remote command failure (network/auth/timeout) — retrying a
#   network failure with 2s backoff would just hit the same wall.
#   Same fail-loud as before: ls-remote-failed → UNVERIFIED, exit.
PUSH_VERIFY_MAX_RETRIES="${PUSH_VERIFY_MAX_RETRIES:-3}"
PUSH_VERIFY_SLEEP="${PUSH_VERIFY_SLEEP:-2}"

attempt=1
REMOTE_TIP=""
LAST_REASON=""
while [ "$attempt" -le "$PUSH_VERIFY_MAX_RETRIES" ]; do
  LS_OUTPUT=$(timeout 15 git ls-remote "$REMOTE" "refs/heads/$LOCAL_BRANCH" 2>/dev/null)
  LS_EXIT=$?

  if [ "$LS_EXIT" -ne 0 ]; then
    # Hard failure — do NOT retry (network failure won't clear in 2s).
    cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "ls-remote failed (exit $LS_EXIT, possibly timeout)", "branch": "$LOCAL_BRANCH", "remote": "$REMOTE", "attempts": $attempt}
EOF
    echo "[verify-push] UNVERIFIED: ls-remote against $REMOTE failed (exit $LS_EXIT) on attempt $attempt" >&2
    exit 0
  fi

  REMOTE_TIP=$(printf '%s' "$LS_OUTPUT" | awk '{print $1}' | head -1)

  if [ "$REMOTE_TIP" = "$LOCAL_TIP" ] && [ -n "$REMOTE_TIP" ]; then
    # MATCH — break out of retry loop, fall through to verified write.
    break
  fi

  # Race-window candidate. Record reason for after-the-loop write.
  if [ -z "$REMOTE_TIP" ]; then
    LAST_REASON="branch $LOCAL_BRANCH not on $REMOTE (no ref returned)"
  else
    LAST_REASON="local-tip $LOCAL_TIP != origin-tip $REMOTE_TIP"
  fi

  # Sleep before next try if any retries remain. After the final
  # attempt, fall through to the unverified write below.
  if [ "$attempt" -lt "$PUSH_VERIFY_MAX_RETRIES" ]; then
    sleep "$PUSH_VERIFY_SLEEP"
  fi
  attempt=$((attempt + 1))
done

# Loop exited. Either we matched (handled below) or all retries ran
# without matching. The matched-case break leaves REMOTE_TIP == LOCAL_TIP
# AND attempt is whichever try succeeded. The exhausted case leaves
# REMOTE_TIP != LOCAL_TIP (or empty) AND LAST_REASON populated.

if [ "$REMOTE_TIP" != "$LOCAL_TIP" ] || [ -z "$REMOTE_TIP" ]; then
  # All retries exhausted without a hash-match. Fail-loud per audit.
  cat > "$MARKER" <<EOF
{"status": "unverified", "reason": "$LAST_REASON (exhausted $PUSH_VERIFY_MAX_RETRIES retries)", "local": "$LOCAL_TIP", "remote": "${REMOTE_TIP:-}", "branch": "$LOCAL_BRANCH", "attempts": $PUSH_VERIFY_MAX_RETRIES}
EOF
  echo "[verify-push] UNVERIFIED after $PUSH_VERIFY_MAX_RETRIES tries: $LAST_REASON" >&2
  exit 0
fi

# Both hashes match. THIS is the only path that writes "verified".
cat > "$MARKER" <<EOF
{"status": "verified", "branch": "$LOCAL_BRANCH", "remote": "$REMOTE", "sha": "$LOCAL_TIP", "verified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF
echo "[verify-push] ✓ verified: $LOCAL_BRANCH on $REMOTE at $LOCAL_TIP" >&2
exit 0
