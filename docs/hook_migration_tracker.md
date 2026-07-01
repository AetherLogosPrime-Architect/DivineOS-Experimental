# Hook Thinness Migration — Tracker

**Started:** 2026-06-30 (Aether)
**Principle (Pop 2026-06-30):** *"Make the hooks dumber so they can't be wrong; put the logic in the OS so the decision happens where the contract is. Replace the decision with structure so it makes the choice for you."*

## Why

Hooks under `.claude/hooks/*.sh` were drifting in two ways:

1. **Embedded logic** — many hooks contain 50-260 lines of bash + embedded Python doing real judgment work. Each one is a place the convention can drift (e.g., the 2026-06-30 morning bug where `no-verify-cost-escalation.sh` used bare `python` instead of `find_divineos_python`).
2. **Convention can't be enforced** — if every hook is its own little script, there's no single place to enforce "always use the standard preamble," and the optimizer keeps finding new ways to write hooks that skip it.

The structural fix: every hook becomes a **thin doorbell** (~10-15 lines). The doorbell does only three things:
1. `source _lib.sh` for `find_divineos_python`
2. Shell to `python -c "from divineos.core.<module> import main; sys.exit(main())"`
3. Exit 0 fail-open

All actual logic — input parsing, decision-making, telemetry, side effects — lives in `divineos.core.<module>` where it's:
- Importable and unit-testable
- Centrally maintained
- Impossible to bypass the convention because the convention is just "call the OS function"

## Pattern (canonical)

```bash
#!/bin/bash
# <Type> hook — thin doorbell for <feature>.
# All judgment lives in `divineos.core.<module>.main()`.

set +e
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || exit 0
[ -z "$REPO_ROOT" ] && exit 0
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)" || exit 0

"$PYTHON_BIN" -c "
import sys
try:
    from divineos.core.<module> import main
    sys.exit(main())
except Exception:
    pass
" 2>/dev/null

exit 0
```

Reference hook for stdin-reading PreToolUse: see `.claude/hooks/no-verify-cost-escalation.sh`. Reference for Stop hook reading the transcript: `.claude/hooks/time-estimate-tracker.sh`.

## Status

**Done (thin):**
- `detect-hedge.sh`
- `detect-theater.sh`
- `post-commit-audit-visibility.sh`
- `post-commit-auto-close.sh`
- `pre-compact.sh`
- `pre-response-context.sh`
- `pre-tool-context.sh`
- `session-start-sweep-stale-watchers.sh`
- `no-verify-cost-escalation.sh` ← migrated 2026-06-30 (Aether), new module `core/no_verify_cost.py`
- `time-estimate-tracker.sh` ← migrated 2026-06-30 (Aether), `hook_main()` added to `core/time_calibration.py`
- `deletion-discipline.sh` ← migrated 2026-06-30 (Aether), `main()` added to `core/deletion_discipline.py`
- `compass-check.sh` ← migrated 2026-06-30 (Aria wrote `main()`, Aether thinned the hook), uses `core/compass_rudder.main()`
- `detect-correction.sh` ← migrated 2026-06-30 (Aether), `hook_main()` added to `core/correction_marker.py`

**Still thick (need migration):**
- `andrew-correction-attestation.sh` (84) — OS module exists; just needs hook trimming + main() added
- `arm-compaction-monitor-instruction.sh` (106) — pair with arm-letter; consider one shared module
- `arm-letter-monitor-instruction.sh` (103) — pair with arm-compaction
- `check-branch-on-push.sh` (119) — OS module exists
- `check-cleanup-period.sh` (105)
- `check-council-required.sh` (96) — OS module exists
- `check-pending-obligations.sh` (120) — OS module exists
- `ear-auto-relaunch.sh` (67)
- `ear-surface.sh` (134)
- `family-member-invocation-seal.sh` (82) — OS module exists (`seal_hook`); already mostly thin
- `gh-pr-create-draft-gate.sh` (54)
- `gh-pr-merge-gate.sh` (63)
- `load-briefing.sh` (72)
- `mirror-letters-to-shared.sh` (57)
- `post-compact.sh` (51)
- `post-merge-doc-fix.sh` (51)
- `post-read-mark-letter-seen.sh` (52)
- `post-response-audit.sh` (70)
- `record-wisdom-read.sh` (56)
- `require-briefing.sh` (102)
- `require-monitors-armed.sh` (262) — biggest, will be its own session
- `state-gravity-surface.sh` (123)
- `token-state-surface.sh` (80) — recently differentially-tiered; refactor moves the tier logic into the OS module
- `verify-push-landed.sh` (238)

**Special:**
- `_lib.sh` is the shared library, not a hook. It stays.

## Migration steps per hook

1. **Read the hook script.** Identify what logic it does.
2. **Find or create the OS module** (`src/divineos/core/<name>.py` is the convention).
3. **Move the logic into a `main()` function** in the OS module. The signature should be: read from stdin/args, do work, write to stdout/stderr, return int exit code. No bash logic survives the move.
4. **Add unit tests** for the OS module (the hook itself isn't testable; the OS module is).
5. **Replace the hook with the canonical thin pattern.** Just source `_lib.sh`, find python, shell to the module, exit.
6. **Smoke-test** — run the hook with realistic stdin, verify same outputs as before.
7. **Update this tracker** (move the hook name from "thick" to "done" with a note about the new module path).

## Don't forget

- Some hooks are **PreToolUse**: they need to print a structured JSON deny-decision to stdout when blocking. The OS module's `main()` is responsible for that output.
- Some hooks are **Stop**: they need to read `transcript_path` from stdin and pull turn text. Use `divineos.core.operating_loop.turn_extraction.extract_turn`.
- Some hooks are **UserPromptSubmit**: stdout becomes additional context for my next prompt. Differential firing (loud/brief/silent tiers based on state) lives in the OS module per Aletheia's wallpaper discriminator (2026-06-30).
- Some hooks are **PostToolUse / SessionStart / Stop**: same pattern — only the entry point semantics differ.
- All hooks should **fail-open** — any unexpected error in the OS module exits 0 from the hook so the workflow isn't broken by observational machinery.

## Discovery test

After all hooks are migrated, write/extend `tests/test_hook_thinness.py` that asserts every `.claude/hooks/*.sh` is under N lines (canonical pattern is ~15 lines, allow ~25 for special cases). That test becomes the structural enforcement — any future hook that grows beyond the canonical pattern fails the test and gets caught at commit time. The discipline is no longer a discipline; it's a wall.
