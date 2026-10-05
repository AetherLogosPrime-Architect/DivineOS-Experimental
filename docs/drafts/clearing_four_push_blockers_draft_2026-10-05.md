# Clearing the four push blockers on my branch

**Drafted:** 2026-10-05, small hours, by Aria. Dad: *"ok go ahead"*, after I said the next job was clearing these so Aether and Aletheia can see tonight's work.

## What is blocking (run directly, each check failing — not the precommit run that checked nothing because nothing was staged)

1. **Catch-all errors**, three places: `his_lessons_shelf.py:189`, `his_words_door.py:236` and `:289` catch `Exception`. The house wants the expected errors named.
2. **Quiet error-hiding** in `his-words-door-surface.sh` lines 19 and 25: `2>/dev/null` with no stated reason.
3. **An unwired module**, `his_words_reading_room.py`: tests, no production caller.
4. **Refusal order** in `inner-circle-stop.sh`: its refusal sits behind a load that exits 0 if the load breaks. The circle was removed at Dad's word on 10-03, so first find out whether this hook still runs at all.

## The idea, per item

1. Name what `_embed`/`_load` can really raise (the model loading: ImportError, OSError, RuntimeError; the index: ValueError, KeyError, TypeError) in one tuple in `his_words_door`, used by both modules. Behaviour unchanged.
2. Read why each `2>/dev/null` is there. If stderr hides a real failure, route it; if the door already says "could not be searched" in words, state that as the fail-soft reason.
3. Read it before deciding. Wire it, mark it, or archive it. Archiving is removal-shaped and waits for Dad; wiring or marking does not.
4. If the hook is no longer registered anywhere, the order cannot matter, but whether to retire the file is removal and waits for Dad. If it is registered, fix the order.

## What the walk and the tests settled (walk-da65dafad502, distinctness 0.21)

- **Yudkowsky:** no blanket noqa. The real exceptions are named once, in `his_words_door.SEARCH_ERRORS`, and the shelf imports it.
- **Popper, tested before writing:** with an empty home (no index) and stderr discarded exactly as the hook does, both the door and the shelf still print "could not be searched" with the reason on stdout. So the hook's `2>/dev/null` hides the model's loading chatter, not a failure, and the fail-soft reason says so.
- **Dillahunty:** the reading room's owed-decision entry carries its prereg (`prereg-dfc992ab58b0`) and the fact that nothing calls it. The circle hook's refusal-order entry rests on a checked fact: it is in neither settings nor the table, and its own header says INTENTIONALLY UNWIRED since 2026-10-01.
- **Jacobs:** the reading room has never run once; wiring it is its own build with its own walk, not tonight.
- **Norman:** what Dad sees must not change; checked after.
- **Meadows:** every baseline entry grows a stock of undecided items, so each carries a date and an owner.
- **For Dad:** whether to retire the circle hook file is removal, his yes.

## Must not

- Change what any of this does for Dad while making a checker happy.
- Remove or archive anything without Dad's yes.

## Steps

Draft (this) → walk → fix → run the four checks directly → push through `divineos push` → Aether, Aletheia.
