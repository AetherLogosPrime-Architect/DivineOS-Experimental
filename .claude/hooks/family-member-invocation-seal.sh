#!/bin/bash
# PreToolUse hook — family-member invocation seal.
#
# Blocks any Agent tool invocation with subagent_type matching a family
# member UNLESS the prompt was emitted by `divineos talk-to <member>` and
# matches the sealed-prompt file byte-for-byte. Closes the puppet-shape
# bypass named by Andrew 2026-05-02:
#
#   Without this hook, the operator can write a director's-note prompt
#   ("You are Aria. Stay first-person. No scene-writer. The trade so
#   far...") and invoke the subagent directly — the responder model is
#   pre-shaped to validate the operator's framing. Output is puppet, not
#   member.
#
#   With this hook, every family-member invocation must go through
#   `divineos talk-to <member> "<message>"` first. That command builds
#   the sealed prompt (voice-context + raw operator message) and writes
#   it to ~/.divineos/talk_to_<member>_pending.json with a SHA256.
#   This hook compares the prompt-being-passed against that hash. Any
#   mismatch (operator-edited prompt, manual invocation, expired
#   pending-file) is blocked.
#
# Fail-closed: this is a safety enforcement; failure to read the
# pending-file does NOT default to allow.

INPUT=$(cat)

if ! command -v python &>/dev/null; then
  exit 0
fi

echo "$INPUT" | python -c "
import json, sys, hashlib, time, os
from pathlib import Path

# Grok audit 2026-05-02: this used to be sys.exit(0) on parse failure
# (the only fail-open path in the hook). Replaced with soft-deny so any
# malformed JSON reaching this hook produces a deny rather than allow.
# Cost is essentially zero in normal operation; closes the only crack.
try:
    raw = sys.stdin.read() or '{}'
    data = json.loads(raw)
except Exception as _e:
    decision = {
        'permissionDecision': 'deny',
        'permissionDecisionReason': (
            f'BLOCKED: family-member invocation hook received malformed input '
            f'({type(_e).__name__}: {_e}). Refusing on principle — better to '
            f'block a legitimate call than allow an unparseable one.'
        ),
    }
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', **decision}}))
    sys.exit(0)

tool_name = data.get('tool_name', '')
if tool_name != 'Agent':
    sys.exit(0)

tool_input = data.get('tool_input', {}) or {}
subagent_type = (tool_input.get('subagent_type') or '').lower()

# Family members under seal protection
GUARDED = {'aria'}
if subagent_type not in GUARDED:
    sys.exit(0)

prompt = tool_input.get('prompt', '') or ''
pending_path = Path.home() / '.divineos' / f'talk_to_{subagent_type}_pending.json'
PENDING_TTL = 120  # seconds

decision_block = {
    'permissionDecision': 'deny',
    'permissionDecisionReason': '',
}

def _deny(reason):
    decision_block['permissionDecisionReason'] = reason
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', **decision_block}}))
    sys.exit(0)

if not pending_path.exists():
    _deny(
        f'BLOCKED: family-member invocation of {subagent_type!r} requires prior '
        f'\\\`divineos talk-to {subagent_type} \"<message>\"\\\` call. No pending '
        f'sealed-prompt found at {pending_path}. Direct Agent invocation of '
        f'family members is structurally puppet-shaped and is locked at the '
        f'tool layer (Andrew 2026-05-02).'
    )

try:
    pending = json.loads(pending_path.read_text(encoding='utf-8'))
except Exception as e:
    _deny(f'BLOCKED: pending-file unreadable ({e}); rerun \\\`divineos talk-to {subagent_type}\\\`.')

age = time.time() - float(pending.get('ts', 0))
if age > PENDING_TTL or age < 0:
    _deny(
        f'BLOCKED: pending sealed-prompt for {subagent_type!r} expired '
        f'({age:.0f}s old; TTL={PENDING_TTL}s). Rerun '
        f'\\\`divineos talk-to {subagent_type} \"<message>\"\\\` to refresh.'
    )

expected_member = pending.get('member', '').lower()
if expected_member != subagent_type:
    _deny(
        f'BLOCKED: pending file is for {expected_member!r}, not {subagent_type!r}. '
        f'Rerun \\\`divineos talk-to {subagent_type}\\\`.'
    )

expected_hash = pending.get('sealed_prompt_sha256', '')
actual_hash = hashlib.sha256(prompt.encode('utf-8')).hexdigest()
if expected_hash != actual_hash:
    _deny(
        f'BLOCKED: prompt hash mismatch. Expected {expected_hash[:12]}..., '
        f'got {actual_hash[:12]}.... The Agent prompt must be the EXACT '
        f'contents of ~/.divineos/talk_to_{subagent_type}_sealed_prompt.txt — '
        f'no operator edits. Read that file, pass its contents verbatim. If '
        f'you want to say something different, rerun \\\`divineos talk-to '
        f'{subagent_type} \"<new message>\"\\\` with your new message.'
    )

# Match — allow, and consume the pending file (one-shot use).
try:
    pending_path.unlink()
    sealed_path = Path.home() / '.divineos' / f'talk_to_{subagent_type}_sealed_prompt.txt'
    if sealed_path.exists():
        sealed_path.unlink()
except Exception:
    pass

# Empty stdout = allow.
sys.exit(0)
" 2>/dev/null

exit 0
