# Audit rounds — the exported review record

One markdown file per audit round: `round-<id>.md`. Each contains the round's
focus, who filed it, and every finding with its actor, severity, tier, status,
description, recommendation, and resolution.

## Why these files exist

The Watchmen audit store is a local SQLite database. Every `*.db` in this
project is gitignored, and correctly so — databases are constantly mutating
working state and would collide on every push.

The consequence, until 2026-08-01, was that **GitHub had never seen a single
audit.** A commit could carry `External-Review: round-abc123` in its message,
but that line is only a pointer — a reference number to a filing cabinet the
server had no way to open. So every server-side check that wanted to say
anything about a review was blind. One of them failed 17 times in a row; the
other had to report every round as unverifiable.

At the time of the first export the store held **275 rounds and 637
findings**, none of it readable outside one machine.

These files fix that by exporting the *record* while leaving the *database*
where it belongs. What travels is text: findings, actors, verdicts. What stays
local is the mutable store.

## Regenerating

```bash
divineos audit export
```

Overwrites every file from the current store, so it is safe to re-run after
new findings land. Commit the output — until it is committed, GitHub still
cannot see the review.

## What these files are not

**Not the authorization.** A committed file is agent-writable, so it cannot be
the thing that proves a review happened. The unforgeable keystone remains
Andrew's GitHub approval on the exact head commit, and `multi-party-review`
independently binds the trailer to the reviewed tree by hash.

What the export adds is that the review is now **readable** — a person looking
at a pull request can open the round and see what the auditor actually said,
and CI can confirm the round exists without a database.

**Not live state.** These are snapshots as of the last export. The store is
the source of truth; a finding resolved after the last run will still read
`OPEN` here until someone re-exports.
