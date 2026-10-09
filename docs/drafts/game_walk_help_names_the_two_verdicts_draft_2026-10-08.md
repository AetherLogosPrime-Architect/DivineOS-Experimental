# The game-walk help names the two accepted verdicts (draft, carried onto the branch 2026-10-08 from the cloud helper's own description)

Written by the cloud helper in the pull request body; copied here so the idea sits on the branch where a reader can find it.

## The idea

A form has one box labelled "cheaper-or-costlier". It reads like a single word to type, so the first person to fill it in types exactly that and the form turns them away. The form only accepts "cheaper" or "costlier". This makes the label say so, and adds a test that reads the two accepted words from the code, so the label cannot quietly drift from them.

## Addresses

`psf-70d73fc5` (make the game-walk help name the two allowed verdicts up front so a first-time filing does not trip). Mechanical repair from round two of the sorted pile; classification in `docs/pile_sorting/output/CLASSIFICATION.md` on branch `cloud/pile-sorting-2026-10-08`. I tripped on exactly this the day it was filed.

## How we would know

The new test invokes the real `game-walk file --help`, takes the accepted words from `CHEAPER` and `COSTLIER` in `core/game_walk.py`, and checks each appears quoted as its own word and that the one-word form is gone. A control test proves the reader can find a known option. It fails before the change and passes after. Aletheia checked it against the real code on 2026-10-08.

## Limits

Help text only. The parser and `core/game_walk.py` are untouched.
