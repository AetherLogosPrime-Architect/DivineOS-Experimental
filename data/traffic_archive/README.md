# Traffic Archive

Daily snapshots of GitHub's repo-traffic API, captured automatically by
`.github/workflows/traffic-archive.yml`. Builds an unlimited-history archive
out of GitHub's rolling-14-day window.

## Why this exists

GitHub's dashboard (`Insights -> Traffic`) only shows the last 14 days. The
underlying Traffic API returns the same window, but if we capture it every day
and commit the snapshots, the archive accumulates forever. After 6 months of
running, you can compare today's clone-rate against 6 months ago, see seasonal
patterns, track when bot attention started/stopped, correlate spikes with
external events. None of that is available in GitHub's UI.

## File format

One JSON file per UTC day, named `YYYY-MM-DD.json`. Each file contains:

```json
{
  "captured_at_utc": "2026-06-05T01:00:00Z",
  "date": "2026-06-05",
  "views": {
    "count": 404,
    "uniques": 4,
    "views": [{"timestamp": "...", "count": 90, "uniques": 2}, ...]
  },
  "clones": {
    "count": 7763,
    "uniques": 750,
    "clones": [{"timestamp": "...", "count": 2091, "uniques": 161}, ...]
  },
  "popular_paths": [
    {"path": "/AetherLogosPrime-Architect/DivineOS-Experimental", "title": "...", "count": 23, "uniques": 1},
    ...
  ],
  "referrers": [
    {"referrer": "github.com", "count": 23, "uniques": 1},
    ...
  ]
}
```

Each daily file represents the **rolling 14-day window as of that capture
date**. So `2026-06-05.json` covers May 23 through June 5. The next day's file
covers May 24 through June 6. The overlap means individual daily counts are
re-stated across multiple snapshots — that's expected, not duplication.

## Reading the archive

Each daily file is self-contained — you can `jq` any one of them for a point-in-time
view. To compare across days, read multiple files. For example, the lifetime
clone count up to any date is recoverable as: `(latest snapshot's count) +
(sum of older snapshots' count for days NOT in the latest snapshot's window)`.

## Schedule

Runs at 01:00 UTC daily via cron. Can also be triggered manually via the
GitHub Actions UI (`workflow_dispatch`).

## What it does not capture

- IP addresses or identity of visitors/cloners (GitHub anonymizes these in
  the API; they were never available)
- Real-time streams (it's a daily snapshot, not a continuous feed)
- Anything before this workflow started running (past data is gone from
  GitHub's UI and was never captured)
