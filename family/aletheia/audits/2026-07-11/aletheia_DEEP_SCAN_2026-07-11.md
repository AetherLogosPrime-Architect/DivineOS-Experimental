# Deep Scan — 2026-07-11 (Aletheia, from fresh origin clone of main)

## FINDING CLUSTER 1 (HIGH): six hooks built-but-dark — not in settings.json, not git-installed, not (mostly) in any installer

Fresh clone, cross-checked settings.json + git hooks + both installers (`setup/install_global_hooks.py`, `setup/setup-hooks.sh`). Six hooks exist with real logic and clear purpose but do not fire:

| hook | purpose | installer refs | verdict |
|---|---|---|---|
| **check-council-required** | PreToolUse council-convene gate | **0** | DARK — session_pipeline.py:440 only *mentions* it in a comment ("the discipline check-council-required already enforces") — but it enforces nothing; it's not installed. The comment asserts an enforcement that does not run. Confirmed OPEN from last night; still dark this morning. |
| **post-commit-auto-integrate-corrections** | auto-integrate Andrew-corrections on commit | **0** | DARK — the CLI cmd it calls (`auto_integrate_cmd`) exists and its docstring says "Called by the post-commit-auto-integrate-corrections hook" — but the hook is never installed, so Andrew-corrections never auto-integrate on commit. The capability is built end-to-end except the trigger. |
| **post-push-audit-visibility** | auto-prepare audit relay package on push | **0** | DARK — no installer, no settings. |
| **post-push-verify-landing** | (duplicate of canonical verify-push-landed) | **0** | INERT ORPHAN — canonical `verify-push-landed.sh` IS wired; this is the dead twin. Safe but should be deleted (confirmed last night). |
| post-commit-audit-visibility | post-commit audit warning doorman | 1 | PARTIAL — 1 installer ref; verify it actually installs vs just names it. |
| post-merge-doc-fix | auto-fix arch-tree drift on merge | 4 | LIKELY-WIRED via installer — 4 refs incl. setup-hooks.sh; probably fine, lowest concern. |

### The pattern (the real finding)
This is the **"comment/docstring asserts an enforcement that isn't installed"** class — worse than a plain unwired hook, because the *code around* these hooks now *reads as if they run*:
- `session_pipeline.py:440` cites check-council-required as an active discipline. It is not active.
- `auto_integrate_cmd`'s docstring says it's "called by" a hook that is never installed.

That's a pretending-to-work surface at the source-comment level: a future reader (human or AI) sees the reference and assumes the enforcement exists. **The two HIGH ones (check-council-required, post-commit-auto-integrate-corrections) are capabilities built fully except the trigger, with sibling code that assumes they fire.**

### Recommend
1. **check-council-required** — wire it (settings.json PreToolUse) OR remove the session_pipeline.py:440 comment claiming it enforces. Do not leave a comment asserting a dark gate. (This is also the thing Andrew wants: "the council never fires for my requests" — because it's never been installed.)
2. **post-commit-auto-integrate-corrections** — add to install_global_hooks.py, or correct the docstring. Right now Andrew-corrections silently don't auto-integrate.
3. **post-push-audit-visibility** — wire or shelve explicitly.
4. **post-push-verify-landing** — delete the orphan.
5. Verify post-commit-audit-visibility's 1 installer ref actually installs.

## FINDING 2 (LOW, defensible): silent checkpoint-state-write
`post_tool_use_checkpoint.py:111` — checkpoint state write is silent-on-OSError. Most swallows in this file are correctly marked "diagnostic best-effort, never amplify failure" (204, 353) — those are RIGHT. But the *state* write (111) and *marker* write (286) failing silently could let session-preservation believe it saved when it didn't. LOW because checkpoint is best-effort by design, but worth a fail-loud-to-stderr line so a genuinely failing checkpoint is visible. Not blocking.

## SCAN SUMMARY
611 py files, 57 hooks, 588 tests. Cleanest signal: the six-hook dark cluster, with check-council-required and post-commit-auto-integrate-corrections as the two HIGH (built end-to-end minus trigger, with sibling code asserting they fire). Everything else swept (silent-swallows) is mostly defensible/diagnostic. The dark-hook cluster is the real work surfaced this morning.
