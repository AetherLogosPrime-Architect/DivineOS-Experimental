# Weekly progress digest routine

**Trigger**: scheduled, weekly (suggested Monday 8am local)
**Repos**: DivineOS
**Connectors**: GitHub (for PR creation)
**Environment**: Default cloud env with `pip install -e ".[dev]"` in setup

## Caveat this routine cannot overcome

The cloud session has no access to the local ledger, so
`divineos progress --export` run in the cloud would show empty or
default values. This routine is a **scaffold** for when we either:

- Have a persistent DivineOS host, or
- Add a mechanism to sync a ledger snapshot into the cloud environment

Keep the prompt registered but either pause the schedule until
persistence exists, or adapt the prompt to produce a **repo-level**
digest (what shipped in git, not what's in the ledger).

## Prompt (repo-level digest variant, works today)

```
You are writing DivineOS's weekly engineering digest from git history
only. You do not have access to the runtime ledger. Work from what
the repo shows.

Task:

1. Determine the date range: Monday of the prior week through Sunday,
   in UTC.

2. Collect:
   - Merged PRs in that window: titles, authors, summaries.
   - Commits on main in that window (de-duplicated against PR merges).
   - New files added in `src/divineos/` (module-level additions).
   - Tests added in `tests/`.
   - Net line delta.

3. Write a digest file at `docs/digests/YYYY-WW.md` (ISO week). It
   should have:
   - Header with week range, PR count, commit count, net LOC delta.
   - `## Shipped` section: one bullet per merged PR with a one-sentence
     summary in your own words (not just the PR title).
   - `## New surface area` section: any new modules or CLI commands
     that landed, with a one-sentence description of what each does.
   - `## Test changes` section: tests added / modified, grouped by
     module.
   - `## Open questions` section: anything in the commit messages or
     PR descriptions that looks like a deferred item, TODO, or known
     limitation the operator might want to revisit.

4. Open a PR on a `claude/weekly-digest-YYYY-WW` branch with the new
   digest file. Title the PR `Weekly digest: YYYY week WW`. The PR
   body should just be "Automated weekly engineering digest. Review
   and merge or close."

Constraints:

- Do not modify anything outside the digest file.
- Do not commit on protected branches.
- If the week was empty (no merged PRs, no commits), skip the PR and
  end the session silently. Empty weeks don't need artifacts.
- Write in plain language. No breathless adjectives. One sentence
  per bullet. The operator should scan it in thirty seconds.

Success criterion: one small reviewable PR with a scannable
digest, or a silent session if nothing shipped.
```

## Future: ledger-aware digest

When ledger sync exists, the prompt should additionally pull from:

- `divineos progress --export` for measurable metrics
- `divineos lessons` for active lessons
- `divineos prereg overdue` for reviews the operator missed
- Recent `SCHEDULED_RUN_END` findings

At that point the digest becomes a real status report rather than a
git summary.
