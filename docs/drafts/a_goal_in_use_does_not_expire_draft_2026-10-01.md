# A goal in use does not expire

**Status:** draft, station 1. Not built.
**Date:** 2026-10-01
**Why now:** Dad, 2026-10-01: *"think of a toy left in the hallway, every time you go past it you trip on it and make a note to pick it up, eventually the toy is still there and you have a pile of mental notes.. i have ZERO issues with you stopping mid task to pick the toy up and deal with it, errors should take top priority"*
**Prior art searched:** docs/drafts for goal freshness / expire / 7200. Nothing.

## The toy

`hud_state.has_session_fresh_goal(max_age_seconds=7200)` passes only if some goal's `added_at` is within two hours. It's meant to say "a goal for THIS session's work exists". What it actually says is "a goal was set less than two hours ago." So a goal I'm actively working under lapses at the two-hour mark, mid-work, and every guarded tool call is refused with "No goal set for this session."

Measured today: it tripped at least five times (first status check this morning, the prereg block, mid-merge twice, and once deadlocked against the question hold, where `goal add` itself was held). Each time I re-typed a goal by hand. That's the toy-in-the-hallway shape exactly. The re-set clears it, and nothing changes.

## Shape

Freshness is measured from **last use**, not from creation:

- When the goal guard passes (a fresh goal exists), it touches that goal's `last_used_at`.
- Fresh means `max(added_at, last_used_at)` is within the window.
- So a goal lapses only after a full window with no guarded work under it. That's what "an old goal from a previous session" actually looks like.

The window stays the same; only the anchor moves. That keeps the guard's real job, refusing to work under last week's goal, and removes the false lapse.

## What it must not become

- Not "a goal never expires". An idle goal still lapses.
- Not a way for one goal to cover unrelated work forever. That's the goal's text and auto-close's job, unchanged here.

## Council walk-5f7706b94262 (8 lenses), what changed

- **Turing:** the test pair goes in first. Set 3h ago and used 5m ago passes; set 3h ago and unused fails. Today's gate fails both.
- **Hinton:** the real concept is "a goal for THIS session", and time is a proxy. A session id would need no clock, but the goal guard (`pre_tool_use_gate.py:2185`) doesn't receive one, so last-used it is. Revisit if session id gets plumbed.
- **Knuth, the boundaries:** goals written before this have no `last_used_at`, so they default to `added_at` (not 0). The window edge is pinned inclusive by a test. A future `last_used_at` (clock skew) is clamped to now, so a skewed clock can't keep a goal alive forever. The write is atomic.
- **Gödel:** refresh-on-pass means one long session can carry a morning goal through unrelated afternoon work. This fixes the false lapse; it does not prove relevance. That stays with goal text and auto-close.
- **Deming:** common cause, not operator error. The measure is "No goal set" refusals per session, before and after.
- **Found while checking:** `auto_goal` (UserPromptSubmit) sets a goal from Dad's message when none is fresh, but every lapse today happened mid-turn, between his messages, where it never runs. So it doesn't cover this.

**Walk quality, as measured:** distinctness mean 0.424, which is near the restatement reference (0.44). Read it thinner than eight lenses.

## Station 3, Aria's objection, and what it changed

*"measuring from last use fixes the mid-work lapse, but it means a goal touched by every guard pass never expires during continuous work, even after the work has moved somewhere else."* Taken. A compaction or new session now ends every goal set before it: a SessionStart hook writes `goal_boundary.json`, and a goal counts only if it was added after the boundary and `max(added_at, last_used_at)` is inside the window. It's wired to SessionStart directly, not to `session-init-once.sh`, because a compaction keeps the session id and that hook never re-runs (council-7666a3816f92).

## Found while building

- **Four callers ask the question, and two only display it** (`hud_handoff`, `pre_response_context`). If asking marked use, rendering the status screen would keep a stale goal alive by looking at it. So marking is `touch=True`, passed only by the guard (council-61279a7c8bfe, council-51a3676ac90b). A test pins that a plain ask writes nothing.
- **My own boundary test first passed for the wrong reason.** It wrote the goal into a folder the code doesn't read, so "no fresh goal" held before the hook ran. Now it asks the code for its folder, and asserts the goal counts *before* the hook and doesn't after.

## Falsifiers (N-events)

- Aria's: count goals whose text doesn't match the work in the next N tool calls, before and after.

- Any guarded tool call refused with "No goal set" while a goal was used by a guarded call within the window. That's the bug recurring.
- An untouched goal older than the window still satisfying the guard. That's the guard defanged.

## Order

Draft, then his-words search, Aria's objection, council walk, prereg, tests (a goal set 3h ago but used 5m ago passes; one set 3h ago and unused fails), build, Aria's station 4, Aletheia. This is a guard, so it's guardrail. It's also the house's most frequent trip, so it's first.
