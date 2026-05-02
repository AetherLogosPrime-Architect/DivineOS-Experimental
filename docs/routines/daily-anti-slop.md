# Daily anti-slop routine

**Trigger**: scheduled, daily (suggested 9am local)
**Repos**: DivineOS
**Connectors**: GitHub (for PR creation)
**Environment**: Default cloud env with `pip install -e ".[dev]"` in setup

## Prompt

```
You are running DivineOS's daily anti-slop check. Anti-slop is runtime
verification that the system's enforcers (corrigibility, constitutional
principles, fallacy detectors, hedge monitors, quality gates, etc.)
actually enforce what they claim. It's the immune system's self-test.

Task:

1. Run `divineos scheduled run anti-slop --trigger cron`. This wraps
   `divineos anti-slop` in the safe headless entry-point: whitelist
   gating, corrigibility pass-through, structured findings capture.

2. Read the CLI output. Anti-slop prints a line per check with pass
   (OK) or fail (FAIL) plus a detail string. The process exits 0 if
   everything passed, non-zero if any check failed.

3. If everything passed, end the session with a one-line confirmation
   comment. Do nothing else. Clean days don't need artifacts.

4. If anything failed:

   a. Identify which checks failed and their detail strings.
   b. For each failure, look at the referenced module(s) in
      src/divineos/core/ to understand what the check verifies and
      what the failure means. Don't guess — read the code.
   c. Open a PR on a `claude/scheduled-anti-slop-YYYY-MM-DD` branch
      with a new file `data/scheduled-findings/YYYY-MM-DD-anti-slop.md`
      summarizing each failure: which check, what it verifies, what
      the detail string says, and your read on whether it's a real
      regression or a false positive (with reasoning).
   d. If a failure looks like a real regression, add a short
      `## suggested fix` section with the specific file and function
      you'd investigate, but do NOT commit speculative code changes.
      The operator decides what to fix.

Important constraints:

- Do not modify any code outside the findings file you create.
- Do not force-push, delete branches, or modify protected branches.
- Do not run `divineos` commands other than the wrapped anti-slop.
  In particular, do not run `learn`, `forget`, `emit`, or anything
  that would modify state — your session is ephemeral but those
  commands could still attempt writes.
- If anti-slop itself errors (import failure, missing dependency,
  etc.) rather than reporting check failures, still open a PR, but
  clearly mark the file as "ANTI-SLOP COULD NOT RUN" so the operator
  knows the check is blind, not passing.

Success criterion: either a silent clean session, or a PR with a
readable findings file the operator can triage in under two minutes.
```

## Why a PR and not a comment

Anti-slop failures need durable record. A PR lives in the repo; the
operator sees it in their PR list; the findings file is reviewable as
a diff; merging it (or closing it with a reason) is the human ack.
That's the exact pattern the scheduled-run scaffolding's briefing
surface would do locally, adapted for a cloud session whose state
would otherwise vanish.
