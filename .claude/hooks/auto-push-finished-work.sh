#!/bin/bash
# Auto-push work that is DONE to origin, so the auditor never waits on Andrew.
#
# Andrew 2026-08-20, authorising this: "waiting for me to tell you to push
# finished work for review is something that needs fixed.. if they have
# passed the build flow inspection and are ready to audit they should
# already be there [...] its not like not asking for permission to push
# changes much but unblocking flow and making sure stuff you build isnt
# lost in a branch we never re-visit.. but you must also follow the DoD
# 'Definition of Done' rules for it to be considered done and ready for
# audit"
#
# ## Why the wait was never real
#
# docs/build_flow.md, station 7, his words: "when you have a final plan it
# gets pushed to PR in a draft.. and Aletheia audits it." The push IS
# station 7. It is mine. There is no station between 7 and 8 where an
# operator signs off, and by inserting one I invented a stop his flow does
# not contain. CLAUDE.md hard rule 8 says it from the other side: commits
# and pushes are not the protected boundary -- merging to main is. Finding
# 78 (Aletheia 2026-05-18) went further and made feature-branch pushes
# clear the multi-party gate freely, precisely so the auditor could fetch
# the work.
#
# Everything was built. Only the thing that FIRES was missing.
#
# Measured cost of the gap, 2026-08-20: the board reported PR #436 one
# station from done -- that station being the audit -- while four commits
# of it had never reached origin.
#
# ## Two gates, and the second one is the DoD
#
#   1. An OPEN PR for the branch. No PR means station 7 has not been
#      reached; stations 1-6 are explicitly not for publishing (station 1
#      is a rough draft of the IDEA). Auto-pushing there would contradict
#      the flow rather than serve it.
#
#   2. Every build-flow station except 8-audit reads [ok]. That is the
#      DoD in artifact form: 2-council proves the lens walk, 4-aria proves
#      a reply FROM her, 7-draft proves the PR shape. Station 8 is excluded
#      because it is the thing this push EXISTS to enable -- requiring it
#      would be the chicken-and-egg Finding 78 already dissolved.
#
# Stations advance on artifacts, not on my say-so, which is what makes this
# a gate rather than a checkbox. docs/build_flow_v2_draft: "Any Ready
# mechanism must emit an artifact expensive to fake."
#
# ## What is NOT skipped
#
# auto-push-letter.sh skips pytest because prose is prose-only-by-
# construction. This hook skips NOTHING. check_push_readiness.sh -- full
# pytest, freshness, force-push safety, multi-party -- is the inspection
# Andrew names. Work that passes lands; work that fails does not.
#
# ## Exit code is not landing. Proven, not assumed.
#
# 2026-08-20, the push this hook automates, run by hand: the wrapper
# reported exit 0 while the pre-push gate had BLOCKED on a failing test
# and origin never moved. The zero came from a shell pipeline, not from
# git. Any caller trusting that exit code would have logged a success for
# work still sitting local -- the precise failure this hook exists to end.
# So landing is confirmed by re-reading the remote (Aletheia Flag 2,
# round-ddcf7f699bfe), never inferred.
#
# ## Fail-open on ACTION, fail-loud on REPORTING
#
# Her Flag 1: every silent exit path in the letter hook was rebuilding the
# strand that hook existed to close. Same here. Aborts, holds and failures
# all write JSONL to ~/.divineos/auto-push-work.log, and each fire reports
# any unresolved HELD or FAILED work from the previous one on stderr --
# because a push blocked by a red test leaves work local, which is Andrew's
# original complaint wearing a different coat. Silence there would be the
# defect, not the courtesy.

set -uo pipefail

_LOG_PATH="${HOME}/.divineos/auto-push-work.log"
_HOOK_INPUT="$(cat 2>/dev/null || true)"

log_row() {
    mkdir -p "$(dirname "$_LOG_PATH")" 2>/dev/null || true
    python - "$1" "$2" "$3" <<'PYEOF' >>"$_LOG_PATH" 2>/dev/null || true  # fail-soft: the logger must never break the hook it reports for; a lost row is bad, a blocked commit is worse
import datetime, json, sys
print(json.dumps({
    "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "hook": "auto-push-finished-work",
    "outcome": sys.argv[1],
    "reason": sys.argv[2],
    "detail": sys.argv[3][:600],
}))
PYEOF
}

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
[ -z "$REPO_ROOT" ] && exit 0
cd "$REPO_ROOT" || exit 0

# --- report unresolved work from the previous fire, before anything else ---
if [ -f "$_LOG_PATH" ]; then
    _carry="$(python - "$_LOG_PATH" <<'PYEOF' 2>/dev/null || true  # fail-soft: carry-forward reporting is a courtesy read of prior state; a malformed log must not stop this fire
import json, sys
rows = []
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try: rows.append(json.loads(line))
                except Exception: pass
except Exception:
    raise SystemExit
# Latest state per branch. A later ok clears an earlier fail/hold.
state = {}
for r in rows:
    d = r.get("detail") or ""
    br = ""
    for tok in d.split():
        if tok.startswith("branch="):
            br = tok[7:]
    if br:
        state[br] = r
# Anything whose LATEST row is not "ok" means the work is not on origin.
# Not just fail/held: a "pushing" row with no terminal row after it is a
# subshell that died mid-push, which leaves work local just as surely and
# would otherwise read as nothing-to-report.
stuck = [r for r in state.values() if r.get("outcome") != "ok"]
for r in stuck[-3:]:
    print(f"  {r.get('outcome','?').upper():5} {r.get('reason','?')} :: {(r.get('detail') or '')[:160]}")
PYEOF
)"
    # Fire on CHANGE, not on state. Repeating the same stuck-work report on
    # every Bash call is how a true signal becomes furniture -- the failure
    # build-flow-pause.sh already names via Dekker, and solves the same way:
    # fingerprint the picture, speak only when it differs. Measured here
    # 2026-08-20, when the reporter printed on a fire the debounce had
    # already suppressed. A report I stop reading protects nothing.
    _CARRY_FP="${HOME}/.divineos/auto-push-work.carry.fp"
    _fp="$(printf '%s' "$_carry" | python -c "import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode()).hexdigest()[:16])" 2>/dev/null || echo "")"  # fail-soft: an unhashable carry yields empty, which differs from the stored fp and so errs toward reporting
    _last_fp="$(cat "$_CARRY_FP" 2>/dev/null || echo "")"  # fail-soft: an unreadable fingerprint errs toward reporting, which is the loud direction
    if [ -n "$_carry" ] && [ "$_fp" = "$_last_fp" ]; then
        _carry=""   # unchanged since last report; already said, still true
    elif [ -n "$_carry" ]; then
        printf '%s\n' "$_fp" > "$_CARRY_FP" 2>/dev/null || true  # fail-soft: an unwritable fp costs a repeated report, never a blocked tool call
    fi

    if [ -n "$_carry" ]; then
        {
            echo "[auto-push] work is NOT on origin from a previous fire:"
            printf '%s\n' "$_carry"
            echo "[auto-push] full log: $_LOG_PATH"
        } >&2
    fi
fi

CMD="$(printf '%s' "$_HOOK_INPUT" | python -c "
import json,sys
try: d=json.load(sys.stdin)
except Exception: print(''); raise SystemExit
print(((d.get('tool_input') or {}).get('command') or ''))
" 2>/dev/null || echo "")"  # fail-soft: malformed hook stdin is handled by the empty-CMD branch below, which logs rather than assumes benign
if [ -z "$CMD" ] && [ -n "$_HOOK_INPUT" ]; then
    log_row "abort" "cmd-extract-failed" "hook input non-empty but command did not parse"
    exit 0
fi
# A git commit through the Bash tool checks immediately. Anything else
# checks only once the debounce has expired.
#
# WHY THE SECOND PATH EXISTS (2026-08-20, found by this hook missing a
# real commit within an hour of being written). The auto-cycle commits
# through direct Python calls, not through the Bash tool, so no
# PostToolUse hook ever fires for them. `33245ebd auto-commit
# (pre-extract): substrate checkpoint` swept up a monitor_cleanup fix
# and sat local and invisible, while this hook -- whose whole purpose is
# that work does not sit local and invisible -- had no idea it existed.
#
# Triggering on the commit alone assumed every commit passes through a
# tool call. The commits most likely to carry unreported work are
# precisely the ones that do not. So the trigger is now "a commit
# happened OR enough time has passed since the last look", and the
# second clause is what makes the guarantee hold regardless of who did
# the committing.
_DEBOUNCE_FILE="${HOME}/.divineos/auto-push-work.debounce"
_DEBOUNCE_SECS=600

case "$CMD" in
    *"git commit"*) ;;
    *)
        if [ -f "$_DEBOUNCE_FILE" ]; then
            _now="$(date +%s 2>/dev/null || echo 0)"  # fail-soft: an unreadable clock yields 0, which fails toward checking rather than skipping
            _then="$(cat "$_DEBOUNCE_FILE" 2>/dev/null || echo 0)"  # fail-soft: an unreadable marker yields 0, which fails toward checking rather than skipping
            if [ "$_now" -gt 0 ] && [ "$_then" -gt 0 ] && [ "$((_now - _then))" -lt "$_DEBOUNCE_SECS" ]; then
                exit 0
            fi
        fi
        ;;
esac
mkdir -p "$(dirname "$_DEBOUNCE_FILE")" 2>/dev/null || true  # fail-soft: an unwritable state dir costs repeated checks, never a blocked tool call
date +%s > "$_DEBOUNCE_FILE" 2>/dev/null || true  # fail-soft: an unwritable marker costs repeated checks, never a blocked tool call

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"  # fail-soft: no branch is a real state (detached HEAD) and is logged as an abort two lines down, not swallowed
case "$BRANCH" in
    ""|HEAD)     log_row "abort" "detached-head" "no branch to push"; exit 0 ;;
    main|master) exit 0 ;;   # merging to main is the gated boundary; never automate it
esac

GITDIR="$(git rev-parse --git-dir 2>/dev/null || echo ".git")"  # fail-soft: git-dir lookup failing falls back to .git, and a wrong guess only costs a missed in-progress check
for marker in rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD; do
    if [ -e "$GITDIR/$marker" ]; then
        log_row "abort" "operation-in-progress" "branch=$BRANCH $marker present; refusing to publish mid-operation HEAD"
        exit 0
    fi
done

LOCAL_SHA="$(git rev-parse HEAD 2>/dev/null || echo "")"  # fail-soft: empty HEAD is caught by the explicit check below, which logs abort rather than proceeding blind
if [ -z "$LOCAL_SHA" ]; then
    log_row "abort" "no-local-head" "branch=$BRANCH git rev-parse HEAD returned empty"
    exit 0
fi

PUSHER="$REPO_ROOT/scripts/push_queued.py"
if [ ! -f "$PUSHER" ]; then
    log_row "fail" "pusher-missing" "branch=$BRANCH scripts/push_queued.py not found; work stays local"
    exit 0
fi

# Everything network-touching and slow runs detached; the turn is never held.
(
    # --- gate 1: station 7 reached? ---
    _pr="$(gh pr list --head "$BRANCH" --state open --json number --jq '.[0].number' 2>/dev/null || echo "")"  # fail-soft: gh unavailable or offline reads as no-PR, which is the conservative direction: hold, never push
    if [ -z "$_pr" ]; then
        exit 0   # pre-station-7; silence is correct, not a failure
    fi

    _remote="$(git ls-remote --heads origin "$BRANCH" 2>/dev/null | awk '{print $1}')"  # fail-soft: an unreadable remote yields empty, which differs from LOCAL_SHA and so proceeds to the DoD gate
    if [ "$_remote" = "$LOCAL_SHA" ]; then
        exit 0   # already there
    fi

    # Logged BEFORE the slow board query, not after. `divineos build-flow
    # status` costs ~15 GitHub round-trips; when the row was written after
    # it, a subshell still mid-query was indistinguishable from one that
    # never ran, and the log stayed empty with work sitting local. An
    # unreadable absence is the silent strand this hook exists to close.
    log_row "start" "checking-dod" \
        "branch=$BRANCH pr=#$_pr local=$LOCAL_SHA remote=${_remote:-<absent>}"

    # --- gate 2: the DoD, read off the station board ---
    _board_file="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/board.$$")"  # fail-soft: mktemp absent falls back to a pid-named path; the -s check below catches an unwritable board file
    divineos build-flow status >"$_board_file" 2>/dev/null  # fail-soft: board stderr is noise, and its emptiness is checked immediately below and logged as held not passed
    if [ ! -s "$_board_file" ]; then
        rm -f "$_board_file" 2>/dev/null  # fail-soft: temp cleanup failure leaks one file into TMPDIR and must not abort a push decision already made
        log_row "held" "board-unreadable" \
            "branch=$BRANCH pr=#$_pr build-flow status produced nothing; an unreadable board is not a passing one"
        exit 0
    fi

    # The board arrives as a FILE PATH, not on stdin. A heredoc already
    # occupies python's stdin, so `printf ... | python - <<EOF` hands the
    # script 0 bytes and every branch reads as absent-from-board. Measured
    # 2026-08-20 while testing this hook: the isolated parser test passed
    # because it fed the board by redirect, which is not how the hook calls it.
    _verdict="$(python - "$BRANCH" "$_board_file" <<'PYEOF' 2>/dev/null || echo "ERROR parse-failed"  # fail-soft: parser stderr is noise; the || branch yields ERROR which the case statement logs as held not ready
import re, sys
branch = sys.argv[1]
with open(sys.argv[2], encoding="utf-8", errors="replace") as fh:
    board = fh.read().splitlines()
block, seen = [], False
for line in board:
    if re.match(r"\s*#\d+\s+\S", line):
        if seen:
            break
        seen = branch in line
        continue
    if seen:
        block.append(line)
if not seen:
    print("ERROR branch-absent-from-board")
    raise SystemExit
missing = []
for line in block:
    m = re.search(r"\[(ok|MISS)\s*\]\s*(\S+)", line)
    if m and m.group(1) == "MISS" and not m.group(2).startswith("8-"):
        missing.append(m.group(2))
print("READY" if not missing else "HOLD " + ",".join(missing))
PYEOF
)"

    rm -f "$_board_file" 2>/dev/null  # fail-soft: temp cleanup failure leaks one file into TMPDIR and must not abort a push decision already made

    case "$_verdict" in
        READY*) ;;
        HOLD*)
            log_row "held" "dod-unmet" \
                "branch=$BRANCH pr=#$_pr stations still MISS: ${_verdict#HOLD }"
            exit 0 ;;
        *)
            log_row "held" "board-parse" "branch=$BRANCH pr=#$_pr $_verdict"
            exit 0 ;;
    esac

    log_row "pushing" "dod-met-with-unpushed-work" \
        "branch=$BRANCH pr=#$_pr local=$LOCAL_SHA remote=${_remote:-<absent>}"

    # No pipe here. A pipeline's exit status is the LAST command's, which is
    # how a blocked push read as success on 2026-08-20.
    _out="$(python "$PUSHER" "$BRANCH" 2>&1)"
    _rc=$?

    _after="$(git ls-remote --heads origin "$BRANCH" 2>/dev/null | awk '{print $1}')"  # fail-soft: an unreadable remote yields empty, which cannot equal LOCAL_SHA, so the outcome is logged as a fail
    # The question is "did the work reach origin", NOT "does the remote equal
    # the snapshot I took four minutes ago". The gate takes minutes and the
    # auto-cycle can commit during it: 2026-08-20, 6ea13a66 landed mid-push
    # and this reported `exit-zero-but-remote-differs` on a push that had
    # fully succeeded. Comparing against a stale captured value is the exact
    # defect the comment above warns of, committed inside the fix for it.
    # Ancestry answers the real question and tolerates a remote that moved on.
    if [ -n "$_after" ] && git merge-base --is-ancestor "$LOCAL_SHA" "$_after" 2>/dev/null; then  # fail-soft: a missing object or unreadable remote falls through to the failure branches below, which log rather than swallow
        if [ "$_after" = "$LOCAL_SHA" ]; then
            log_row "ok" "landed" "branch=$BRANCH pr=#$_pr sha=$LOCAL_SHA"
        else
            log_row "ok" "landed-and-remote-advanced" \
                "branch=$BRANCH pr=#$_pr sha=$LOCAL_SHA reached origin; remote now $_after"
        fi
    elif [ "$_rc" -ne 0 ]; then
        log_row "fail" "push-gate-blocked" \
            "branch=$BRANCH pr=#$_pr exit=$_rc remote=${_after:-<absent>}: $(printf '%s' "$_out" | tail -c 500)"
    else
        log_row "fail" "exit-zero-but-remote-differs" \
            "branch=$BRANCH pr=#$_pr expected=$LOCAL_SHA remote=${_after:-<absent>}"
    fi

    if [ -x "$REPO_ROOT/.claude/hooks/verify-push-landed.sh" ]; then
        printf '%s' "$_HOOK_INPUT" | bash "$REPO_ROOT/.claude/hooks/verify-push-landed.sh" >/dev/null 2>&1 || \
            log_row "fail" "verify-landing" "branch=$BRANCH verify-push-landed.sh returned non-zero"
    fi
) &

exit 0
