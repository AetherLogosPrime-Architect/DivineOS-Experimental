# Station six reads the covering walk (draft, 2026-10-10)

## The fault

Station two judges a branch by `coverage_for(paths)`: a CLOSED walk scoped to the changed files with every lens settled. Station six still judges by two older things:

1. `_lenses_applied(paths)`: distinct lenses in `COUNCIL_LENS_APPLIED` events keyed by an `edit:<path>` fingerprint. A branch whose files this seat never edited (a cloud branch, #599) has none, so six says "no walk to be stale or fresh".
2. `_walk_postdates_build(branch)`: the newest lens event anywhere in the ledger against the branch's last commit. It never looks at the covering walk's own close time, so a walk closed after the last commit still reads as "predates the last build" (Aria, #619).

Same family as the 2026-08-07 branch-name bug: a query that cannot reach the data, accusing.

## The change

- `coverage_for` also reports when the covering walk closed (`closed_at`), added to `Coverage`.
- Station six, when station two's coverage is `covered`, takes the walk's lens count as `lenses_walked` and its close time as the walk time. The last-commit time stays as is.
- When coverage is anything but `covered`, station six behaves exactly as today (no loosening).
- A walk close time that cannot be read stays CANNOT_CHECK, never "fresh".

## Falsifier / proof

Reproduce on #619 before the change (station 2 SATISFIED, station 6 MISS, closed walk covering all five files) and on #599 (no edit fingerprints); both flip after. A test where the walk closed BEFORE the last commit must still be MISS.

## Not in this change

The harmless-redirect carve-out, the pile cap, and the `walk open` comma-scope refusal.
