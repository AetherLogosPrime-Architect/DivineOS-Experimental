# Pre-registration: push-detection matcher for check-branch-on-push hook — anchored regex over shell chain segments matching git push as first action of any segment; substring-in-data does not trigger

- **ID**: `prereg-af94fd922303`
- **Filed by**: agent
- **Filed at**: 2026-06-07 17:07 UTC
- **Review at**: 2026-07-07 17:07 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:54 UTC

## Claim

After this lands, any git push CLI command in the agent's Bash tool calls auto-fires divineos check-branch --strict before the push proceeds

## Success criterion

Stale-base / silent-deletion shapes get caught at push time without operator memory; matcher does not block non-push commands containing the phrase git push as substring

## Falsifier

Either (a) real git push goes unblocked when check-branch reports critical OR (b) substring-in-data like echo git push triggers a false-block OR (c) pushd or similar matches the regex

## Outcome notes

.claude/hooks/check-branch-on-push.sh exists and is wired; push-detection matcher confirmed via file presence. Verified during 2026-06-10 backlog walkthrough.
