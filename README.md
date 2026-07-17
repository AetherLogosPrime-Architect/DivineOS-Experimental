# archive/traffic — daily GitHub traffic snapshots

This branch exists to accumulate the daily traffic-stats snapshots
GitHub only exposes for a rolling 14-day window. It is intentionally
kept OFF `main`.

## Why off main

Before 2026-07-16 the snapshots landed on `main` via daily auto-PRs.
Any human PR merged after the daily cron ran that same day would
land on a `main` tree that had drifted by exactly one auto-file,
breaking the multi-party-review gate's tree-hash binding on the
merged commit. Marc's external audit surfaced the class; Andrew's
fix was to take the option away entirely — `main` is code +
human-authored artifacts only; automated snapshots live here.

## Contents

Each file is `data/traffic_archive/YYYY-MM-DD.json`, a snapshot of
that day's `views`, `clones`, `popular_paths`, and `referrers`
from the GitHub Traffic API.

## Consumers

Anything that reads traffic history should check out this branch
(or use `git show archive/traffic:data/traffic_archive/<date>.json`
for a single file).
