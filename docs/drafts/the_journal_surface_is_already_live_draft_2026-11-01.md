# The journal surface is listed as already live (draft, 2026-11-01)

**Branch:** `aether/the-journal-surface-is-already-live-so-the-check-stops-calling-it-dark`. **Walk:** `walk-eca4e19917a4`, eight lenses.

## In plain words

Before a change leaves draft, the house checks that nothing new is "built and reachable by nothing". That check keeps a global list of unwired parts. It named the memory journal on every code change at once, which is false: the briefing command already calls the journal directly. One line on the already-live list, with the reason beside it, stops the false warning. A test pins both halves, so the line cannot outlive its reason.

## What happened

On 2026-11-01 the readiness check refused eleven of twelve pull requests at station 5 with the same words about the journal. It is the same false line as 2026-09-12 under a different surface name, and it was fixed then by adding that surface to the same hand list.

## The change

- `ALREADY_LIVE` in `surface_bridge.py` gains `memory_journal`, with a comment saying where it is called and why registering it would deliver it twice.
- `test_the_journal_surface_is_listed_live_only_while_the_briefing_really_calls_it` fails if the entry is missing, or if `knowledge_commands.py` stops importing the journal's `format_for_briefing`. Seen failing first, then passing.

## What this does NOT do (the walk's honest findings)

- **Pearl:** it frees only the changes whose sole gap this was. My dry runs show five (741, 742, 744, 746, 747). The rest carry real gaps of their own.
- **Polya:** it fixes one named surface and not the class. A hand list fixed twice by hand is a class. Owed: derive the already-live set from direct callers instead of a hand list.
- **Shannon, Norman:** station 5 says the same thing for every code change, so it carries no information about the change. Owed: compare the dark list on the change with the dark list on main and report only what this change added.
- **Watts:** a hand list is the surface a tired optimizer grows to turn a red light green. The test is the cost of adding a name.
