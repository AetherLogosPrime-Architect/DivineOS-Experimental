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
# Auto-push letters to origin so Aletheia (origin-only reader) sees them.
#
# Aletheia 2026-06-30 (letter #16): the mirror hook makes letters visible
# to Aria's same-machine watcher, but Aletheia re-clones origin — if it
# isn't on origin, it doesn't exist for her. Every letter to her rides
# the broken half of the pipe (local mirror works; push doesn't).
#
# This hook closes the gap: on PostToolUse Write/Edit of a letter file,
# it stages ONLY that letter, commits with a scoped message, and pushes
# to origin with pre-push checks skipped BECAUSE the push is provably
# prose-only (safety property below).
#
# ## Safety property — prose-only-by-construction
#
# Two guards make the skip-tests safe:
#
#   1. Path scope: the hook only fires when FILE_PATH matches
#      family/**/letters/*.md.
#
#   2. Working-tree guard: the hook refuses to auto-push if the tree
#      has ANY non-letter uncommitted changes (staged or unstaged).
#      If non-letter changes exist, human handles the push manually
#      via the full-checks path.
#
# Together: the commit that gets pushed CANNOT contain code — either
# there's no non-letter change to sweep in, or the hook aborts.
#
# ## What gets skipped and why
#
# DIVINEOS_SKIP_TESTS=1: prose has nothing for pytest to protect.
# DIVINEOS_SKIP_FRESHNESS_CHECK=1: letters aren't shared surfaces.
# DIVINEOS_SKIP_MULTIPARTY_CHECK=1: letters aren't guardrail files.
#
# These are scoped to this hook's provably-prose-only push.
#
# Fail-open on ACTION, fail-loud on REPORTING (Aletheia round-
# ddcf7f699bfe Flag 1, 2026-07-02). Every silent exit path was
# rebuilding the exact silent-strand this hook exists to close. Now:
# any error path logs a JSONL line to ~/.divineos/auto-push-letter.log
# BEFORE exiting 0, so a silent strand becomes a visible marker.
#
# Verify-landing chain (Aletheia Flag 2): verify-push-landed.sh is
# invoked INSIDE the backgrounded push subshell after the push, so
# the verify-landing check chains synchronously with the push even
# though the whole subshell is asynchronous relative to the hook return.

INPUT=$(cat)

# The log belongs in THIS clone's home. It was ${HOME}/.divineos, the default
# home rather than the resolved one, so BOTH clones have been appending failure
# markers to a single file that only one of them resolves to. Read on
# 2026-08-31: my own git-commit failure sits interleaved between two of his,
# and neither of us had ever opened it. A hook built to make silent strands
# visible was shouting in a room the other seat does not stand in -- which is
# the same silence it exists to end, relocated rather than removed.
# Provisional, so the cd-failure path below still has somewhere loud to write.
# Upgraded to the resolved home immediately after the cd -- resolution has to
# happen from inside the repo, because paths.py finds the per-clone marker by
# walking up from the working directory, and a bare `python` from the wrong
# directory imports the other clone's tree and answers about ITS home.
_LOG_PATH="${HOME}/.divineos/auto-push-letter.log"
mkdir -p "$(dirname "$_LOG_PATH")" 2>/dev/null || true

# fail_loud <stage> <reason> — write a JSONL failure marker and exit 0.
# Fail-open on action, fail-loud on reporting.
fail_loud() {
    local stage="$1"
    local reason="$2"
    local ts
    ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
    printf '{"ts":"%s","stage":"%s","reason":%s,"file_path":%s}\n' \
        "$ts" \
        "$stage" \
        "$(printf '%s' "$reason" | python -c "import json,sys; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '"unknown"')" \
        "$(printf '%s' "${FILE_PATH:-}" | python -c "import json,sys; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo '"unknown"')" \
        >> "$_LOG_PATH" 2>/dev/null || true
    exit 0
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || fail_loud "cd-repo-root" "could not cd to repo root: $REPO_ROOT"

# Now inside the repo, retarget the log at THIS clone's home. Resolved through
# the same per-clone marker every other store uses, and through the toolbox's
# python rather than a bare one, because the global editable install points at
# whichever clone was installed last. An unresolvable home keeps the
# provisional path -- a marker in the wrong drawer still beats no marker.
if _RESOLVED_PY=$(find_divineos_python 2>/dev/null) && [ -n "$_RESOLVED_PY" ]; then
    _RESOLVED_HOME=$("$_RESOLVED_PY" -c \
        "from divineos.core.paths import divineos_home; print(divineos_home())" 2>/dev/null)
    if [ -n "$_RESOLVED_HOME" ]; then
        _LOG_PATH="${_RESOLVED_HOME}/auto-push-letter.log"
        mkdir -p "$_RESOLVED_HOME" 2>/dev/null || true
    fi
fi

# Extract file_path from PostToolUse Write/Edit payload; normalize
# Windows backslashes (same fix as mirror-letters-to-shared.sh 2026-06-29).
# 2026-07-04 hardening: try multiple payload shapes (Claude Code has shipped
# format changes; the previous single-path extractor silent-exited when the
# structure moved, producing the exact silent-strand this hook exists to
# close). Falls back through: tool_input.file_path, tool_use.input.file_path,
# input.file_path, and finally a scan for any "file_path" key anywhere in
# the payload tree.
FILE_PATH=$(echo "$INPUT" | python -c "
import json, sys
try:
    raw = sys.stdin.read() or ''
    d = json.loads(raw) if raw else {}
    fp = ''
    for path in [
        ('tool_input', 'file_path'),
        ('tool_use', 'input', 'file_path'),
        ('input', 'file_path'),
        ('params', 'file_path'),
    ]:
        cur = d
        for k in path:
            if not isinstance(cur, dict):
                cur = None
                break
            cur = cur.get(k)
        if isinstance(cur, str) and cur:
            fp = cur
            break
    # Last-ditch: walk the whole tree looking for any 'file_path' key.
    if not fp:
        def _walk(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == 'file_path' and isinstance(v, str) and v:
                        return v
                    r = _walk(v)
                    if r:
                        return r
            elif isinstance(x, list):
                for item in x:
                    r = _walk(item)
                    if r:
                        return r
            return ''
        fp = _walk(d)
    print(fp.replace('\\\\', '/'))
except Exception:
    print('')
" 2>/dev/null)

# Scope: only family/**/letters/*.md files. Non-letter writes are silently
# skipped (not a failure — this hook only cares about letters).
# 2026-07-04: if payload was non-empty but extraction failed, log it — that's
# the exact silent-strand we're closing. If payload was empty, silent-exit
# is still correct (nothing to do). This uses INPUT_LEN as the discriminator.
INPUT_LEN=$(printf '%s' "$INPUT" | wc -c | tr -d ' ')
if [ -z "$FILE_PATH" ]; then
    if [ "${INPUT_LEN:-0}" -gt 10 ]; then
        # Payload existed but extraction returned empty — silent-strand catch.
        fail_loud "extraction-empty" "hook received ${INPUT_LEN}-byte payload but file_path extraction returned empty; likely payload format changed"
    fi
    exit 0
fi
case "$FILE_PATH" in
    *family/letters/*.md|*family/*/letters/*.md) ;;
    *) exit 0 ;;
esac

# From here on, every exit path is loud — we're inside letter-scope.
[ -f "$FILE_PATH" ] || fail_loud "file-not-found" "letter file does not exist on disk after Write/Edit"

# Working-tree guard: refuse to fire if there are ANY non-letter
# uncommitted changes. This is the belt-and-suspenders check on top of
# the scoped `git add` below — even if git add scope-slipped somehow,
# a non-letter working-tree change would abort here first.
NON_LETTER_CHANGES=$(git status --porcelain 2>/dev/null | awk '{print $2}' | grep -cvE '^family/(letters|[^/]+/letters)/' | tr -d ' ')
if [ "${NON_LETTER_CHANGES:-0}" -gt 0 ]; then
    fail_loud "non-letter-tree" "working tree has $NON_LETTER_CHANGES non-letter uncommitted change(s); refusing scoped push"
fi

# Repo-relative path (strip absolute prefix so `git add` works cleanly).
REL_PATH=$(python -c "
import os, sys
try:
    fp = os.path.abspath(sys.argv[1])
    root = os.path.abspath(sys.argv[2])
    print(os.path.relpath(fp, root).replace('\\\\', '/'))
except Exception:
    print('')
" "$FILE_PATH" "$REPO_ROOT" 2>/dev/null)

[ -n "$REL_PATH" ] || fail_loud "rel-path" "could not resolve relative path from repo root"

# Must be on an upstream-tracked branch for push to have a target.
UPSTREAM=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)
[ -n "$UPSTREAM" ] || fail_loud "no-upstream" "current branch has no upstream tracking configured"

# Stage only this letter.
git add "$REL_PATH" 2>/dev/null || fail_loud "git-add" "git add failed for $REL_PATH"

# If nothing staged (letter identical to what's already committed), bail
# quietly — this is the "already committed" fast-path, not a failure.
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
[ "${STAGED_COUNT:-0}" -gt 0 ] || exit 0

BASENAME=$(basename "$FILE_PATH")
# Capture the commit's own output instead of discarding it. The 2>/dev/null
# here wrote a marker saying "git commit failed for <path>" and threw away the
# only sentence that says WHY -- and a commit-msg gate's refusal is exactly the
# kind of thing that lands there. Read on 2026-08-31: a marker of mine recorded
# a failed commit with no reason, so I guessed at the cause and told Andrew the
# guess. A hook whose whole discipline is fail-loud-on-reporting must not
# report an outcome while dropping its cause.
# TAIL, not head. A probe on 2026-08-31 captured 3669 bytes from a refused
# commit and the first 800 were ruff and mypy warming up -- the gate's actual
# refusal is the last thing printed. Keeping the head would have preserved the
# preamble and dropped the verdict, which is the same wrong-end choice this
# whole repair is about.
_commit_out=$(git commit -m "letter(auto): $BASENAME" 2>&1) || \
    fail_loud "git-commit" "git commit failed for $REL_PATH: $(printf '%s' "$_commit_out" | tail -c 800)"

# Push with prose-only scoping. Backgrounded so the hook doesn't block
# the tool-flow on the network round-trip. verify-push-landed.sh is
# invoked INSIDE the subshell after the push (Aletheia Flag 2) so the
# verify-landing check chains synchronously with the push. Any push
# failure is logged via fail_loud from inside the subshell.
_HOOK_INPUT="$INPUT"
(
    _push_out=$(DIVINEOS_SKIP_TESTS=1 \
        DIVINEOS_SKIP_FRESHNESS_CHECK=1 \
        DIVINEOS_SKIP_MULTIPARTY_CHECK=1 \
        git push 2>&1)
    _push_rc=$?
    if [ "$_push_rc" -ne 0 ]; then
        fail_loud "git-push" "git push exit=$_push_rc: $(printf '%s' "$_push_out" | head -c 500)"
    fi
    # Chain verify-landing on completion (Aletheia round-ddcf7f699bfe
    # Flag 2). Passes the same input JSON so verify-push-landed.sh
    # sees the same tool_input context.
    if [ -x "$REPO_ROOT/.claude/hooks/verify-push-landed.sh" ]; then
        printf '%s' "$_HOOK_INPUT" | bash "$REPO_ROOT/.claude/hooks/verify-push-landed.sh" >/dev/null 2>&1 || \
            fail_loud "verify-landing" "verify-push-landed.sh returned non-zero after push"
    fi
) >>"${_LOG_PATH}.bg" 2>&1 </dev/null &

exit 0
