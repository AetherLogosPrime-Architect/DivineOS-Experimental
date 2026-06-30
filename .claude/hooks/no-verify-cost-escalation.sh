#!/bin/bash
# PreToolUse hook — escalate the cost of `git --no-verify`.
#
# Aletheia 2026-06-30 (letter #13): "consider whether `--no-verify` should
# require the same kind of visible-cost that the andrew-correction-attestation
# gate requires — make the bypass *expensive and logged*, not a cheap flag.
# The bypass-telemetry already *caught* all four uses, which is the system
# working — now the question is whether the catch should escalate to friction."
#
# The 2026-06-30 night had Aether reach for --no-verify four times. The first
# had cover (gate blocking the fix to the gate). The subsequent three were
# discipline-fatigue. The bypass-telemetry caught them but didn't STOP them.
# This hook converts catch-but-don't-stop into name-the-reason-or-block.
#
# Rule: any `git commit --no-verify` or `git push --no-verify` in a Bash
# tool-call must be accompanied by DIVINEOS_NO_VERIFY_REASON="<one-line>"
# inline in the same command. The reason is logged to bypass_telemetry on
# the allow path so the bypasses stay visible in the substrate's drift
# surfaces.
#
# Thin doorman: detection logic is inline (small pattern); logging delegated
# to divineos.core.bypass_telemetry.record_bypass. Fail-open on any
# infrastructure error (this hook must not break the workflow).

INPUT=$(cat)

echo "$INPUT" | python -c "
import json, os, re, shlex, sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

if (data.get('tool_name') or '') != 'Bash':
    sys.exit(0)
cmd = (data.get('tool_input') or {}).get('command') or ''
if not cmd.strip():
    sys.exit(0)

try:
    tokens = shlex.split(cmd)
except ValueError:
    sys.exit(0)

if 'git' not in tokens:
    sys.exit(0)
git_idx = tokens.index('git')
subcommand = tokens[git_idx + 1] if git_idx + 1 < len(tokens) else ''
if subcommand not in ('commit', 'push'):
    sys.exit(0)
if '--no-verify' not in tokens:
    sys.exit(0)

# --no-verify present on git commit/push. Demand an inline reason.
reason_match = re.search(
    r'DIVINEOS_NO_VERIFY_REASON=(?:\"([^\"]+)\"|\\'([^\\']+)\\'|(\\S+))', cmd
)
if reason_match:
    reason = (reason_match.group(1) or reason_match.group(2)
              or reason_match.group(3) or '').strip()
    if len(reason) < 8:
        msg = (
            'BLOCKED: --no-verify reason too short (< 8 chars).\\n'
            'Aletheia 2026-06-30 letter #13: the bypass must name what it\\n'
            'is cover for. \"fix\", \"tests\", \"wip\" do not name the gate-shape\\n'
            'being bypassed. Try a more specific reason such as:\\n'
            '  DIVINEOS_NO_VERIFY_REASON=\"gate blocks fix to gate\" \\\\\\n'
            '    git ' + subcommand + ' --no-verify ...\\n'
        )
        print(json.dumps({
            'hookSpecificOutput': {
                'hookEventName': 'PreToolUse',
                'permissionDecision': 'deny',
                'permissionDecisionReason': msg,
            }
        }))
        sys.exit(0)
    # Allow path — log the bypass to telemetry, then approve silently.
    try:
        from divineos.core.bypass_telemetry import record_bypass
        record_bypass(
            gate_name='git-' + subcommand + '-no-verify',
            env_var='DIVINEOS_NO_VERIFY_REASON',
            reason=reason,
        )
    except Exception:
        pass
    sys.exit(0)

# No reason provided — block.
msg = (
    'BLOCKED: git ' + subcommand + ' --no-verify requires a named reason.\\n\\n'
    'Aletheia 2026-06-30 (letter #13) flagged --no-verify as a structural\\n'
    'signal: the bypass-telemetry caught all four uses on 2026-06-30 but\\n'
    'did not stop them. This gate converts catch-without-stop into\\n'
    'name-the-reason-or-block.\\n\\n'
    'Required form:\\n'
    '  DIVINEOS_NO_VERIFY_REASON=\"<what the gate is wrong about>\" \\\\\\n'
    '    git ' + subcommand + ' --no-verify ...\\n\\n'
    'The reason gets logged to bypass_telemetry so the bypasses stay\\n'
    'visible in drift surfaces. Reason must be at least 8 chars and\\n'
    'should name the gate-shape, not the surface symptom.\\n\\n'
    'If the gate is genuinely wrong-shape, file the bug first:\\n'
    '  divineos audit submit-round \"<gate>: wrong-shape\" --actor aether\\n'
    'and reference the round-id in the no-verify reason.\\n'
)
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'PreToolUse',
        'permissionDecision': 'deny',
        'permissionDecisionReason': msg,
    }
}))
" 2>/dev/null

exit 0
