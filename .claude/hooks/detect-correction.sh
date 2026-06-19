#!/bin/bash
# UserPromptSubmit hook — detect correction-shaped language in user input.
#
# If the user's latest message matches any CORRECTION_PATTERNS (imperative
# pushback: "no", "wrong", "don't do that", "you missed", etc.), write a
# marker file at ~/.divineos/correction_unlogged.json. The PreToolUse gate
# reads this marker and blocks non-bypass tools until the correction is
# logged via `divineos learn` or `divineos correction`.
#
# Closes the enforcement gap from ChatGPT audit claim-964493
# (theater-learning bypass) by converting "I should log corrections" from
# intent into structural requirement.
#
# Fail-open: any error here exits 0 without blocking, so a broken hook
# doesn't break the user's session.

INPUT=$(cat)

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

# Delegate to Python — regex matching + marker write in one interpreter call.
echo "$INPUT" | "$PYTHON_BIN" -c "
import json, sys
try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

prompt = data.get('prompt', '') or ''
if not prompt:
    sys.exit(0)

# Prior-turn context (#16): the correction is a RESPONSE to what I just did.
# At UserPromptSubmit, the transcript's last assistant turn is that prior turn.
transcript = data.get('transcript_path', '') or ''
prior_text, prior_calls = '', ()
if transcript:
    try:
        from divineos.core.operating_loop.turn_extraction import extract_turn
        tt = extract_turn(transcript)
        prior_text = tt.last_assistant_text or ''
        prior_calls = tuple(tt.tool_calls_in_turn or ())
    except Exception:
        pass

try:
    from divineos.core.correction_marker import classify_correction, set_marker
except Exception:
    sys.exit(0)

# Evidence-bearing return (Andrew 2026-06-19 / prereg-897aade9ef38):
# classify_correction now returns CorrectionMatch | None instead of str |
# None. The match object carries (verdict, pattern, matched_text, position,
# tier) so set_marker stores the citation and format_gate_message shows it.
match = classify_correction(prompt, prior_text, prior_calls)
if match is None:
    sys.exit(0)

if match.verdict == 'block':
    set_marker(prompt, match)
elif match.verdict == 'advise':
    # Non-blocking: a weak/ambiguous pattern with no corrective prior-turn
    # context. Surface it (so a real correction is never silently dropped) but
    # do NOT block the tool. UserPromptSubmit stdout is injected as context.
    # The advisory now cites the specific evidence so the agent can judge it
    # against the matched text rather than re-reading the prompt blind.
    print(
        f'ADVISORY (correction-detector): {match.tier} pattern '
        f'{match.pattern!r} matched {match.matched_text!r} at position '
        f'{match.position}, but the prior turn does not look corrected '
        '(no completion-claim, no substantive edit) - NOT blocking. If it '
        'was a real correction, log it via: divineos learn'
    )
" 2>/dev/null

exit 0
