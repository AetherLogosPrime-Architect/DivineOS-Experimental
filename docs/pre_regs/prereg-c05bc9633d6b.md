# Pre-registration: auto-commit at extract/sleep boundaries prevents forgotten-commit substrate loss

- **ID**: `prereg-c05bc9633d6b`
- **Filed by**: aether
- **Filed at**: 2026-07-06 01:20 UTC
- **Review at**: 2026-08-05 01:20 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

welding git commit into the pre-extract, post-extract, and pre-sleep points removes the 'operator remembers to commit' failure mode entirely — the same equipment-spell shape Andrew has been casting all day

## Success criterion

over the next 30 days of normal use, zero incidents of substrate-writing being lost or nearly-lost due to a missed manual commit at extract/sleep boundaries; auto-commit fires visibly in extract/sleep output when there was work to commit; test suite stays green

## Falsifier

any of: (1) auto-commit silently commits secrets, credentials, or files that shouldn't have been committed (e.g. .env, .divineos_data_home marker, generated dbs) — checked by inspecting the auto-commit history over 30 days; (2) auto-commit's git failures cascade into extract/sleep failures the user has to debug (fail-soft is not actually soft); (3) the auto-commit body becomes noise — 30+ auto-commits with zero human review because the message pattern trains me to ignore them
