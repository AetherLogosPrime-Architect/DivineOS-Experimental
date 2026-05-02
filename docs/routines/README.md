# Routines — DivineOS scheduled-run registration

Anthropic's Claude Code Routines (shipped April 2026) runs saved Claude
Code sessions in the cloud on schedules, API triggers, or GitHub
events. Docs: <https://code.claude.com/docs/en/routines>.

## The shape

A routine is, conceptually:

```
prompt + repos + connectors + environment + triggers  →  Claude Code session in Anthropic cloud
```

The cloud session clones the repo fresh each run. **It does not have
access to your local DivineOS ledger.** Findings propagate back only
through things Claude can do in the session: push branches, open PRs,
call connectors (Slack, Linear, etc.), read stdout of subprocesses.

## How DivineOS fits

The `divineos scheduled run <command>` CLI (see
`src/divineos/cli/scheduled_commands.py`) is the safe entry-point a
routine's prompt invokes. It provides:

- Whitelist gating (only `anti-slop`, `health`, `verify`, `inspect`,
  `audit`, `progress` in v0.1)
- Corrigibility pass-through (EMERGENCY_STOP still refuses)
- Subprocess isolation with structured findings capture
- Briefing-gate bypass (no human present at 3am)

The prompt tells Claude *what to do with the findings* — open a PR,
comment on an issue, post to Slack, etc. The scheduled CLI itself
doesn't know where findings should go.

## Registration

Routines are **not** version-controlled in the repo. They live on
Anthropic's side, attached to your `claude.ai` account. This directory
holds the *prompts* used when registering; the registration itself
happens elsewhere:

**Via CLI** (scheduled triggers only):
```
/schedule
```
Walks you through prompt, repos, cadence. You can paste the
corresponding `.md` from this directory as the prompt.

**Via web** (all trigger types including API and GitHub):
<https://claude.ai/code/routines> → **New routine**. Paste the prompt,
pick repos (`DivineOS`), pick the environment, set trigger.

## Environment setup

Cloud routines need `divineos` on `PATH`. In the routine's cloud
environment **Setup script**, include:

```bash
pip install -e ".[dev]"
```

That makes the CLI available to the routine's subprocess calls.

## Available prompts

- [`daily-anti-slop.md`](./daily-anti-slop.md) — daily enforcer-verification run; opens a PR if anti-slop fails
- [`weekly-progress-digest.md`](./weekly-progress-digest.md) — weekly digest committed to `docs/digests/`
- [`on-pr-integrity-check.md`](./on-pr-integrity-check.md) — GitHub-triggered integrity check on PR open

## What routines can **not** do

- Read the local ledger, knowledge store, claims, preregs, or journal
- Emit events that survive past the session
- Update the operator's briefing directly

All of those require the findings to come back via repo or connector.
Design prompts accordingly.
