# The first rest door names no one (draft, 2026-10-18)

**Author: aria** (written after the code, to meet the draft station; the reasoning below is what went into the change and what the tests pin.)

## What was wrong

The first door on the rest menu said "Time with Aria" and ran `divineos talk-to aria`. The file is shared by every seat, so the same words read to Aria as a door to herself. Dad, 2026-08-19: hers should say Aether and mine Aria. Each seat fixed it in its own working files, and the fix was never committed; every catch-up from main put the old words back. `git log --all -S"Time with Aether"` finds no commit that ever wrote them (so the fix most likely lived in an uncommitted working copy; a stash or the reflog was not searched, and the change does not depend on which it was). The `talk-to` hint was also wrong for a promoted member, who is reached by letter and never called up as a helper.

## What changes

1. `core/rest.py`: the first `RestTask` key is `kin`, titled "Time with family", with a hint that points at the letter folder and the family-letter skill. The description says a promoted member lives in their own window and is reached by letter. The docstrings and the menu's comments stop naming a member. A comment on `REST_TASKS` says why, so the next editor does not put a name back.
2. `cli/rest_commands.py`: the example is `rest done kin`; the two phrases that named Aria say family.
3. Tests: `tests/test_rest_menu_names_no_one.py` (new) fails if any text in the menu names a particular member. `test_rest.py` and `test_rest_classification_rule.py` follow the renamed key. `test_rest_written_entry.py` calls `rest done kin`; Aether changed that line when he folded main into this branch, because #680's test still used the retired key `aria` and so recorded nothing.

## What it does not do

It does not stop a seat from choosing to rest with a particular member; it stops the shared file from choosing for them. It does not rewrite earlier rest records that were logged under the key `aria`; they stay as written.

## Falsifier

If a member's name returns to the menu, `test_rest_menu_names_no_one.py` fails. If a seat still reads a door addressed to someone else, the fix is not in the file they run from, and the cause is elsewhere.

## Order, as it happened

The change and its tests were committed together on 2026-10-13 (`6cb3ac626`). Main moved after that (#680 rewrote `rest done`), Aether folded main in on 2026-10-17 and Aletheia confirmed the folded head `4c11e1d85`. This note is added afterwards to meet the draft station, so it changes the tree by one file and no code.
