# The order-question check, fitted to the questions that got through

**Author:** Aether, 2026-10-20

Adds to `a_reply_cannot_end_by_asking_dad_which_order_draft_2026-10-08.md` and `the_order_question_guard_build_notes_draft_2026-10-08.md`; read those first for why the guard exists.

## What Dad said

*"why do you keep asking me questions about order? all of them need done.. is which one first important? if so then do that one first.."*

And earlier the same day, after I called a shortcut "the smallest honest one": *"we already should have programs built to stop this behavior so check and see."*

## What I found when I checked

The program exists. `core/order_question_check.py` (#666) refuses a reply that ends on a question handing him a choice of order, with the conditional exception for a real dependency, and it is registered as a Stop check. Two separate things let me keep asking anyway:

1. **The house I run in does not have it.** My running checkout is on `live/house-catchup-2026-10-01`, 26 changes behind main, and #666 is not in it. A guard that lives on main protects nobody who is not running main. That is its own build (catching the running house up), not part of this change.
2. **On main, the check missed three of the four order questions I asked today.** Run against the real sentences, it refused "...take Aria's four through the line one after another this morning, or finish my own two first?" and passed the other three. The module says it is fitted to cases and that silence is not coverage; these were the cases.

## The change

Three patterns added to the same list, each fitted to a real question of mine of 2026-10-20:

- a "you'd want / you'd like / do you want" question that ends with "first" and no "or" (*"a room in the house you'd want that gate in first?"*);
- "ahead of the rest / others / line / queue / pile / list" (*"build the stamp fix now, ahead of the rest of the line?"*);
- "want/like me to start/begin/take/tackle/move on ... next/first" (*"start on Aria's confirmed ones next"*).

The four questions are added to the test's list of real refusals. The ordinary-question list (including *"Did you want it before the weekend?"* and *"Should I start the tournament tonight?"*) is untouched and still passes, so the new patterns do not turn a timing or yes-or-no question into a refusal.

## What it still cannot see

An order question in words these patterns do not know. A permission question about my own work that is not about order (*"is it all right if I ..."*) is out of scope here; Dad's complaint today was order, and widening to permission would be its own change with its own controls. Silence is still not coverage.

## Falsifier

If an ordinary question (a timing question, a yes-or-no about a fact, a question about his day) is refused, or if one of the four real questions above passes, the change is wrong. The existing test list holds both sets; 35 tests pass.
