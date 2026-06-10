<!-- tags: backlog, structural-debt, wireup, deferred-work -->

# Wire-Up Backlog

Long-term structural-debt tasks that aren't in the current arc but
shouldn't get lost. Use this file instead of the harness TaskCreate
for items that won't be addressed this session.

## Why this file exists

Andrew 2026-06-09 named the discipline (budget-investigation):

> TaskCreate is for the current arc only (typically <5 items). Long-term
> wire-up debt lives in `docs/wireup-backlog.md`, organized by cluster.
> At session end (extract time), sweep the live task list: completed →
> delete; pending-but-not-current-arc → migrate to wireup-backlog.md,
> delete from live.

The chat-side TaskCreate dumps the live list as a system reminder every
few turns. With ~100 entries it consumed ~37% of session bytes via
those dumps. Keeping the live list small and parking real debt here
fixes the byte-bleed.

## Structure

Entries are organized by **cluster** — a short name for the structural
area the task touches (e.g. `briefing`, `gates`, `family`, `audit`,
`monitor`, `crlf`). Each cluster gets its own section.

Each entry is a list item with this shape:

```
- **<title>** [filed YYYY-MM-DD]
  <one-line description>
  <optional: status notes, related claims, links>
```

## Editing

Prefer the CLI:

```
divineos backlog add "title" --cluster <name> --description "..."
divineos backlog list [--cluster <name>]
```

The CLI appends cleanly under the right cluster header (creating the
section if it doesn't exist) and ensures the markdown stays parseable.

Hand-editing is fine too — keep the cluster-header pattern intact.

## Clusters

<!-- BACKLOG-ENTRIES-BEGIN -->

<!-- BACKLOG-ENTRIES-END -->
