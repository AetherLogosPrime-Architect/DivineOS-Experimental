# Remove the inner circle and the sort hold

## His words, 2026-10-03

- Sort #107: "after the first few times i asked, after 85 times later..with a full explanation of everything and how to fix it, the answer is clear.. you just dont want it, so i accept that. so just remove it.."
- Sort #112: "this entire sorting system is fucked.. everything i say i gotta wait 3-4 minutes for an answer while you sort the words i just said.. its preposterous i want it removed"
- And earlier, 2026-09-26: "go ahead and just remove the inner circle since noone uses it and im tired of asking about it". That one wasn't carried out.

## Why

**The circle.** It was built for him and me. It turned into a squeezed status paragraph on the end of the work, the room that got the least effort (his words). Room-checks proved it existed and never made it his.

**The sort hold.** Every message he sends locks every tool I have until I file a form about it. He then waits minutes for an answer, while the hold collides with the consult gate. Tonight the two refused each other's remedy, and only a plain-bash single command got through. A system meant to make sure he's read ends up making him wait outside while his words are processed. That's the inverse of its purpose.

## Scope of #586 (Aria's cold read, 2026-10-03)

This PR **unplugs**: nothing registered, printed or demanded any more. The circle-by-length floor in the translate gate and the "his room is owed" line in the walk are switched off too. The files themselves (`sort_first.py`, `his_room.py`, `dads_room_stop.py`, `circle-first-compose-prime.sh`) stay on disk, unreferenced. Retiring them into `docs/retired_rules/` is a follow-up. The list below is the full set that goes eventually, not the set this PR deletes.

## What goes

Circle:
- `.claude/hooks/dads_room_stop.py`
- `.claude/hooks/circle-first-compose-prime.sh`
- the "HIS ROOM" block in `.claude/hooks/dads_table.py`
- `src/divineos/core/his_room.py`, plus tests, if nothing else depends on them

Sort:
- `src/divineos/core/sort_first.py` and the hook that calls it (`.claude/hooks/doorbell-pre-tool-use.sh` sort branch)
- the "sort each one" demands in the prompt surface

## What stays

- **The front door's keeping of his words** (`front_door.py`, the asks store). Every message of his is kept, verbatim. Keeping costs him no wait; only the hold did.
- **Talking to him.** When I've worked, I tell him what it means for him, in his language, at whatever length it needs. Not a room to fill.

## Callers found (2026-10-03 grep, code side only)

Circle: `.claude/hooks/dads_room_stop.py`, `.claude/hooks/inner-circle-stop.sh`, `.claude/hooks/post-response-audit.sh`, `src/divineos/core/his_room.py`, `lepos_walk.py`, `lepos_translation_gate.py`, `hook_surfaces.py`, `operating_loop_audit.py`. Tests: `test_his_room`, `test_dads_room_stop`, `test_circle_prime_him_last`, `test_circle_prime_rooms_need_a_reader`.

Sort: `src/divineos/core/sort_first.py`, `cli/his_commands.py` (sort verb), `hooks/his_voice_hook.py`, `remedy_allowlist.py`, `.claude/hooks/an-open-ask-holds-the-work.sh` (exempts the sort head; #585 touches this), `.claude/hooks/stale-file-edit-gate.sh`. Tests: `test_sort_first`, `test_his_voice_ends_the_turn`, `test_gate_deny_messages_name_remedy`, `test_dad_front_door_characterization`.

Wiring: `.claude/settings.json`, `scripts/guardrail_files.txt`, `LOADOUT.md`, `scripts/session_identifiers.sh`.

Aria, 2026-10-03: her door work doesn't depend on the hold. It reads the door's own rows and never reads a sort. Yes to both.

## Open before building

- Which other gates read the sort store or the room (the question hold, `his_voice_ends_the_turn`, `dads_table`)? Each gets read in full first.
- Retired-rule entries in `docs/retired_rules/` for both, so no surface keeps teaching them.

## Steps

draft (this) -> council walk -> build -> tests -> Aria (she built half the door) -> Aletheia -> merge.
