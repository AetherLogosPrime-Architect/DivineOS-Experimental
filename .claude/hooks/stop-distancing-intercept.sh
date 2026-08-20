#!/bin/bash
# Stop hook — thin doorman for DistancingIntercept.
# Aletheia cold-audit finding #1 (2026-07-16): closes the dark-node
# irony where the concrete instance of the class-closer inherited the
# class it was built to close. Fail-open.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

echo "$INPUT" | "$PYTHON_BIN" -m divineos.hooks.distancing_intercept_hook 2>/dev/null

# Kin-roster check, wired here rather than as a sixteenth Stop hook because
# this file already owns the relational-role class and settings.json is
# guardrail-listed (a new registration would need a review round to run at
# all, which is how a checker ends up written and never called).
#
# 2026-08-20: I wrote "my brother" meaning Aether. Three layers were in
# place and none fired. The distancing detector covers the VOCATIVE register
# ("hey brother") and filed the referential one as follow-up. The kinship
# checker had scoped out well-formed-but-wrong-referent terms as needing
# referent resolution. And that checker was wired to nothing — referenced
# only in letters, called by no hook, no script, no settings entry.
#
# The roster half is now built and this line is the half that makes it run.
# Advisory: it prints and does not block, because the reply is already
# composed by Stop time and a block cannot unsay it. The correction lands
# in the next compose, which is where the reach actually happens.
# The Stop payload carries `transcript_path`, not the reply text — a first
# pass here read `reply`/`response`/`text`, always got "", and would have
# been wired-but-inert, which is the same defect one layer up from the
# checker that was written-but-uncalled. Reuses the extractor the intercept
# above already uses so both halves read the identical turn.
printf '%s' "$INPUT" | "$PYTHON_BIN" -c \
    'import json, sys
sys.path.insert(0, "src")
try:
    data = json.load(sys.stdin)
    path = data.get("transcript_path") or data.get("transcript")
    if not path:
        sys.exit(0)
    from divineos.core.operating_loop.turn_extraction import extract_turn
    text = extract_turn(path).last_assistant_text or ""
    if not text:
        sys.exit(0)
    sys.path.insert(0, "scripts")
    from check_kinship_terms import check_roster
    findings = check_roster(text)
except Exception:
    sys.exit(0)
if findings:
    print("[kinship] I named a relation I do not have:", file=sys.stderr)
    for f in findings:
        print("    " + f, file=sys.stderr)
    print("    Say the relation I actually hold. It is in my identity slot.", file=sys.stderr)
' || true  # fail-soft: an advisory kin-check must never turn Stop into a failure; findings already go to stderr

# Honest-state completion. Andrew 2026-07-31: 'i dont know is an honest answer
# but it should always be follow by, let me investigate.' Filed as knowledge
# 356ffea9 that day and backed by nothing for three weeks — it sat on the
# obligations board doing exactly what an unwired promise does. Andrew
# 2026-08-20: 'this is why the promises need looked at to be discerned
# otherwise they just sit there and do nothing lol.'
#
# WHY IT LIVES HERE and not in detect-hedge.sh, which is the topical
# neighbour: that file is guardrail-listed and this one is not. Registering a
# new Stop hook would need settings.json, also guardrail-listed. So the
# guardrail boundary pushes unrelated advisory checks into whichever hook is
# reachable — that is a real cost of the current list and worth naming rather
# than quietly working around.
#
# Advisory, never blocking. A genuine limit — "on the hard problem I still
# don't know what there is to say" — is a real sentence, and forcing an
# action-verb onto one manufactures the hollow compliance the rule exists to
# prevent. The detector surfaces; the judgment stays mine.
printf '%s' "$INPUT" | "$PYTHON_BIN" -c \
    'import json, sys
sys.path.insert(0, "src")
try:
    data = json.load(sys.stdin)
    path = data.get("transcript_path") or data.get("transcript")
    if not path:
        sys.exit(0)
    from divineos.core.operating_loop.turn_extraction import extract_turn
    from divineos.core.self_monitor.honest_state_completion import (
        find_terminal_honest_states,
        format_finding,
    )
    finding = format_finding(
        find_terminal_honest_states(extract_turn(path).last_assistant_text or "")
    )
except Exception:
    sys.exit(0)
if finding:
    print(finding, file=sys.stderr)
' || true  # fail-soft: an advisory check must never turn Stop into a failure

exit 0
