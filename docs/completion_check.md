# Completion-Check Probe — Initiative Compass That Measures Closure, Not Pace

The `completion_check` probe is the data source for the **initiative virtue spectrum** on the moral compass. It answers a specific question:

> *Has the agent finished the things it already built, before it starts the next one?*

Pace is fine if completion lands. Pace is the wrong axis to measure. The probe replaces volume-signals (PR count, tool calls, context overflows) with a walk of recently-built mechanisms, asking three closure questions per mechanism:

1. **Is it wired into the path that needs it?**
2. **Has it been tested on real input?**
3. **Does it help — has it caught what it was built to catch?**

Mechanisms that lack one or more closure signals are **unfinished**. The compass position scales with their count, capped in the excess (overreach) zone.

## Why this exists

Named by Andrew 2026-05-14: the pre-existing initiative detector used context-overflow count and tool-call volume as overreach signals. Both are pace metrics. A session can have many overflows because the agent did a lot of completion-quality work, or because it stood up many things and walked away from each. The signal couldn't distinguish.

The new probe distinguishes. Standing up a new mechanism without wiring or testing it is the same failure-mode regardless of pace: **cardboard-shack architecture** (foundational truth #8 — cheap-now is expensive-later). The probe is the structural enforcement of the principle.

## What "unfinished" means precisely

For each `.py` or `.sh` file added under one of the mechanism directories within the last N days (default 14):

- **Python modules** check for: (a) any test file in `tests/` that references the module's stem name (catches both `test_<stem>.py` exact-match and parametrized test files that cover many modules), and (b) any other file under `src/`, `.claude/`, `setup/`, or `scripts/` that token-references the module's stem (catches multi-line imports, registry calls, and other wiring shapes).

- **Shell hooks** check for: (a) registration in `.claude/settings.json` (Claude Code hook wiring), OR (b) `source` / `bash` invocation in another file (catches `_lib.sh`-style helpers and setup-script installs). Same token-grep contract as Python — any reference counts as wiring.

A mechanism flagged with `unwired` AND/OR `untested` is unfinished. The usefulness question rides along for every recently-built mechanism — it can't be answered automatically, only by the agent looking at the mechanism and deciding.

## Mechanism directories

```
src/divineos/core/    # core substrate modules
src/divineos/cli/     # CLI command modules
src/divineos/hooks/   # in-process pre/post-tool hooks
.claude/hooks/        # shell hooks driven by Claude Code settings
```

`scripts/` is excluded because standalone scripts have entry-point semantics (wired by invocability, not by import). `tests/` and `docs/` are excluded — those aren't mechanisms.

## Compass position formula

```
n = len(unfinished_mechanisms)
position = min(0.1 * n, 0.5)
```

One stray unfinished mechanism doesn't push the compass into overreach (0.1 × 1 = 0.1, still in the virtue band). Five or more does (0.5 caps in excess). The cap prevents pathological alarmism — even with 50 unfinished mechanisms, the position is 0.5, not 5.0.

If `unfinished_mechanisms` returns empty AND the session shows substantial activity (≥10 tool calls, ≥2 user messages), the probe logs a **baseline virtue observation at position 0.0** — healthy initiative without overreach.

## Public API

```python
from divineos.core.completion_check import unfinished_mechanisms, format_for_compass

unfinished = unfinished_mechanisms(days=14)
# -> list[Unfinished] with .path, .has_test, .has_wiring, .questions

print(format_for_compass(unfinished))
# Compact evidence string suitable for compass observation evidence field
```

Each `Unfinished` instance carries the per-mechanism closure questions that are still open — descriptive evidence rather than a single number.

## Dogfooding history

Built 2026-05-14. Four refinement passes against the live repo took the surface count from 148 to 0:

1. **Pass 1 (148 flagged):** raw probe ran. Identified `.sh` files needing settings.json check rather than Python import.
2. **Pass 2 (148):** `.sh` settings-check added. CLI command modules still flagged.
3. **Pass 3 (148):** multi-line imports investigated. Token-match across the codebase replaced strict regex.
4. **Pass 4 (123):** token-match landed, dropping false positives on whole-module imports. Began closing real gaps.

The remaining unfinished mechanisms were then either wired (six in their native shapes — hedge detector into hook, savor into CLI, unknown-unknown into audit subcommands, three probe-bug false-positives fixed, one deprecated shim deleted) or covered by new parametrized test files (40 council experts, 18 CLI command modules, 4 stragglers).

Final count: **0 unfinished mechanisms** as of the close of round-a9316b23e675.

## How it surfaces

The probe runs as part of `reflect_on_session` (compass) at extraction time. The initiative observation lands with:

- Position: scaled with unfinished count, capped at +0.5
- Evidence: the per-mechanism closure questions (truncated to first 5 with "+N more")
- Source: `completion_check`

`divineos compass` shows the initiative spectrum's current position. `divineos compass-ops history --spectrum initiative` shows the trend.

## Falsifier-bound claim

Filed as claim `8bcc832f`:

> If `completion_check` never surfaces an unfinished mechanism on a session where one demonstrably exists (built-but-unwired), the probe is inert and the claim fails.

The dogfooding above is the first round of evidence. Each future round refines or refutes.

## Where to read more

- `src/divineos/core/completion_check.py` — the probe itself
- `src/divineos/core/moral_compass.py` — `reflect_on_session()` is where the initiative observation gets logged
- `tests/test_completion_check.py` — unit tests for the probe
- `tests/test_moral_compass.py::test_initiative_*` — initiative-spectrum integration tests
- Foundational truth #8 in `docs/foundational_truths.md` — the principle the probe enforces
