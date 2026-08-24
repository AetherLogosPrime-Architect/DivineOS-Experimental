# Whose map this is, and what it cannot show me

Copied 2026-08-14 from Aether's worktree
(`.claude/worktrees/strange-leakey-4c70a2/graphify-out/`), where he rebuilt it
after finding the scan leak. Andrew asked me to take it so I could see the whole
system rather than wait on my own run.

**51,376 nodes / 67,033 links**, against the 31,134 both our old maps carried.
Built at his commit `fd554ca31ff553b23a152908bae9b9ba2aa4e5ac`.

The prose layer was recovered from the old graph rather than regenerated, so no
outside model re-read our writing and Andrew's external spend was not repeated.
He was firm about that, and right: only the author knows what they meant.

The README beside this file says the map is hospitality — *here's the map, so
you don't have to hold the whole house in your head.* That is exactly why the
gap below is written down. A map you trust wrongly is worse than no map.

---

## The gap, stated precisely

**This is a map of HIS tree, not mine.** At the moment of copying, my branch
carried 73 changed files and 9,920 insertions his checkout does not have.
Everything below is invisible to it:

    core/andrew_given.py          the column of what Andrew gives
    core/council_walk.py          the walk with enforced completion
    core/dashboard.py             the check-engine socket
    core/dashboard_checks.py      one light per system
    core/hook_router.py           the seven doorbells
    core/hook_surfaces.py         the surface roster
    core/letter_claims.py         local state of files a sibling's letter names
    core/must_read.py             when a room speaks, open the door

The one that matters most: **`hook_router.py` is the job I am about to pick
up.** Aether wrote it, it lives on my branch, and this map cannot see it. The
map's largest blind spot is exactly the thing I will be working inside.

Also absent: today's repairs to the orphan checker, the ledger chain walk, the
lepos question pool, and the engagement counter.

## Why I took his instead of rebuilding

I would rather have my own, and this is a stand-in. His rebuild script is
committed as `scripts/graphify_rebuild.py` in commits he has not pushed, so it
is not reachable from here, and rebuilding without it means re-paying two traps
he already paid:

* The CLI **blocks forever on stdin** in a shell with no terminal — he watched
  it sit at zero CPU for ten hours and reported it as working-just-slow, because
  he checked the output file instead of the process table. `</dev/null` fixes it.
* `extract()` defaults to `parallel=True`, and on Windows spawn re-imports the
  main module, so a rebuild script with no `if __name__ == "__main__":` guard
  forks itself without bound. Seventeen `collected 4000 files` lines before he
  killed it.

With both handled, 4,000 files took fifteen seconds.

**My own scan leak is closed** (`6b674f24`) — `.direnv/` is guarded in
`.graphifyignore` now, because the bare `*` in its nested ignore file leaks past
its own subtree and zeroes the corpus. A rebuild from here will not repeat the
failure that produced the 31k map. It simply has not been run.

## The honest summary

A good map of the shared architecture and a stale map of my branch. Read it for
the system; do not read it for anything I built this week.

---

## The graph files themselves are no longer tracked (2026-08-21)

`graph.json` (51MB), `.graphify_analysis.json` (4.4MB) and `manifest.json`
were removed from version control while resolving PR 406. They were 54 of the
54.2MB that PR added, and a file that size is why GitHub reported the PR as
CONFLICTING with zero changed files for three weeks — its diff engine gives up,
and the reason is invisible from the PR page. The same defect had already been
fixed once for `graphify-out/`; this directory survived because main never had
it, so the merge carried it through unconflicted.

This file and the README stay because they are hand-written: they record whose
map it was and what it could not show me. The map itself is machine-emitted and
regenerable by re-running graphify against the corpus named above.
