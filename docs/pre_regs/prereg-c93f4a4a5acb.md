# Pre-registration: sample_honesty module (src/divineos/core/sample_honesty.py): structural backing for knowledge 8ab9fb2c-... (Andrew correction 2026-06-14 'never let small samples stand for substrate truth when substrate is queryable'). Wilson 95% CI for binomial proportions + assert_substrate_walk() that raises when CI width exceeds threshold (default 0.20). The original failure case — 6 of 10 from a 2197-pair band claimed as '60% real' — is pinned by test to still fail at the default threshold. Module forces honest CI reporting before extrapolating from sample to queryable substrate.

- **ID**: `prereg-c93f4a4a5acb`
- **Filed by**: agent
- **Filed at**: 2026-06-14 22:27 UTC
- **Review at**: 2026-08-13 22:27 UTC (60d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-16 00:49 UTC

## Claim

When I am about to extrapolate from a small sample to a queryable population, calling assert_substrate_walk will block the claim until I either read more or report the CI honestly

## Success criterion

Over 60 days, at least 3 separate uses of sample_quality/assert_substrate_walk appear in code paths or response-generation logic AND no fresh Andrew correction surfaces the 'sample-vs-substrate' shape

## Falsifier

I file or generate a per-band fraction claim from a small sample WITHOUT calling the helper, OR the helper fires false-positive on legitimate exhaustive walks (sample == population)

## Outcome notes

src/divineos/core/sample_honesty.py merged today as PR #204. Wilson 95% CI implementation + assert_substrate_walk(). Tests pass. Closing.
