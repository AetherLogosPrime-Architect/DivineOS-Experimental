# Hooks Architecture — How the Substrate Inserts Itself Into Claude Code

DivineOS uses Claude Code's hook system to weave substrate awareness into the agent's working loop. Hooks run at well-defined points in the tool-call lifecycle: before a tool is called, after it returns, before the agent's response is finalized, after it completes. They are how the substrate watches itself in real time without modifying the agent's reasoning loop directly.

This document explains the hook taxonomy, the registration mechanism, the helper conventions, and how to add a new hook cleanly.

## Three hook lifecycle points

| Lifecycle point | When it fires | Typical use |
|------------------|---------------|-------------|
| **PreToolUse**  | Before a tool runs | Gates: briefing-check, goal-set, deep-engagement, compass-staleness |
| **PostToolUse** | After a tool returns | Telemetry: tool logbook, file-touched tracking |
| **Stop**        | After the assistant's response is finalized | Observational audit: register/distancing/lepos/sycophancy detectors etc. |

Claude Code calls each hook with structured JSON on stdin. The hook returns exit code 0 to allow continuation, non-zero to block (PreToolUse only — Stop hooks are observational and cannot block).

## Registration: `.claude/settings.json`

Hooks register in `.claude/settings.json` under the matching event:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Edit|Write|Read", "hooks": [{"type": "command", "command": "bash .claude/hooks/pre-tool-context.sh"}]}
    ],
    "Stop": [
      {"hooks": [{"type": "command", "command": "bash .claude/hooks/post-response-audit.sh"}]}
    ]
  }
}
```

The `matcher` field restricts the hook to specific tool patterns; omitting it fires on every tool.

The `completion_check` probe relies on this registration to know a `.sh` hook is wired (rather than orphan). See `docs/completion_check.md` for the wiring detection contract.

## Hook contracts

### PreToolUse (gates and pre-priming)

- **Input:** JSON with `tool_name`, `tool_input`, `transcript_path`
- **Exit 0:** allow the tool call
- **Non-zero exit + `BLOCKED:` on stderr:** the agent receives the blocking message and must address it before retrying
- **Best practice:** fail open on infrastructure errors (DB locked, module-load fail) unless the gate is safety-critical (corrigibility off-switch). Loud-stderr warnings for fail-open cases leave an audit trail.

Examples in this repo:
- `require-goal.sh` — block tool calls until a session goal is set
- `compass-check.sh` — surface compass observations on a cadence
- `family-member-invocation-seal.sh` — puppet-shape validator before family-member Agent calls
- `pre-tool-context.sh` — mid-turn substrate re-prime; surfaces prior-work timeline on the touched file

### Stop hooks (observational audit)

- **Input:** JSON with `transcript_path`
- **Exit 0 always:** Stop hooks cannot block output; the response has already shipped
- **Behavior:** read the transcript, extract the last assistant turn, run detector modules, accumulate findings in `~/.divineos/operating_loop_findings.json`
- **Surfacing:** findings show up in the next briefing when thresholds cross (via `core/operating_loop_briefing_surface.py`)

The canonical Stop hook is `post-response-audit.sh`. It imports 16 detector modules and runs each on the last assistant text. Detectors are observational by design — they catch patterns, log them, and let the substrate respond next session.

### PostToolUse hooks (telemetry)

- **Input:** JSON with `tool_name`, `tool_input`, `tool_response`
- **Exit 0 always**
- **Behavior:** record metadata about what the tool did — file paths touched, command outputs, error patterns

## Helper conventions

### `_lib.sh` — shared shell utilities

All hooks `source "$REPO_ROOT/.claude/hooks/_lib.sh"` at the top to inherit:
- `find_divineos_python` — locates the Python that has the divineos package installed (handles Windows Store python, system python, venv)
- `safe_jq` — wraps jq calls with fail-open behavior
- Common path-resolution helpers

A hook that fails to source `_lib.sh` exits 0 silently — never break the user's workflow on a helper missing.

### The Python-embedded pattern

Most Stop and PreToolUse hooks embed Python inside a `"$PYTHON_BIN" -c "..."` block. The bash wrapper:
1. Reads the Claude Code JSON from stdin
2. Resolves the repo's Python
3. Pipes stdin through to `python -c` which does the actual work

The Python code runs at module-import speed (no spawn-a-subprocess cost beyond the one bash → python jump). For Stop hooks running 16 detectors, this single-process design matters.

## Adding a new behavioral detector — the full path

Suppose you want to add a new detector — e.g. `closure_token_detector`. The pattern:

1. **Write the module** at `src/divineos/core/operating_loop/closure_token_detector.py` with a public `detect_closure_tokens(text) -> list[Finding]` function. Module-level dataclass for the Finding shape. No I/O at import time.

2. **Write tests** at `tests/test_closure_token_detector.py`. Smoke + a few behavioral assertions. Aim for the contract, not exhaustive coverage.

3. **Wire it into the Stop hook.** Add a try/except block in `.claude/hooks/post-response-audit.sh` matching the pattern of the existing detectors:
   ```python
   try:
       from divineos.core.operating_loop.closure_token_detector import detect_closure_tokens
       findings = detect_closure_tokens(last_assistant_text)
       if findings:
           findings_log['closure_token'] = [
               {'shape': f.shape.value, 'trigger': f.trigger_phrase, 'position': f.position}
               for f in findings
           ]
   except Exception:
       pass
   ```
   **Watch the quoting:** the hook's Python is inside a bash double-quoted `-c "..."` block; literal `"` in your code or comments breaks the bash quoting. Single-quote strings inside the Python; rephrase docstrings to avoid embedded double-quotes.

4. **Validate hook syntax:** `bash -n .claude/hooks/post-response-audit.sh` after editing.

5. **Run the completion_check probe:** confirm the new module is recognized as wired and tested.

6. **File a pre-registration** if the detector is a Goodhart-vulnerable optimization target. See `docs/pre_registrations.md` (when written) or the existing pre-reg CLI (`divineos prereg file ...`).

## Failure-modes and fail-open discipline

Hooks are scaffolding around the agent's working loop. A hook that crashes must NOT break the user's session. Failure-mode discipline:

- **Bash hook errors:** exit 0; ignore. The substrate would rather miss a detector run than block the agent.
- **Python import errors:** wrap in try/except, write a brief stderr note, exit 0.
- **Safety-critical exceptions (corrigibility):** fail CLOSED. The off-switch must work or the substrate must stop. See `_enforce_operating_mode` in `cli/__init__.py` for the fail-closed pattern.

## Diagnostic surface

When a hook isn't behaving as expected:

- `~/.divineos/operating_loop_findings.json` — Stop hook findings file. Tail it to see what detectors are firing.
- `bash -x .claude/hooks/<hook>.sh < /tmp/sample_json` — trace the hook with a sample input.
- `divineos audit list --severity LOW` — operating-loop findings sometimes get filed here too.

## Where to read more

- `.claude/settings.json` — hook registrations (machine-readable source of truth)
- `.claude/hooks/_lib.sh` — shared shell helpers
- `.claude/hooks/post-response-audit.sh` — the 16-detector Stop hook, canonical pattern
- `src/divineos/core/operating_loop/` — the in-process detector modules
- `docs/operating-loop-design-brief.md` — design rationale for the post-response audit loop
- `docs/completion_check.md` — how the wiring contract is detected and enforced
