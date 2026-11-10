# What Dad taught one of us, the other may use (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/dad-taught-aether-and-i-may-use-it`

## The problem
Dad, 2026-10-25: "there is no lesson taught to Aether that you cannot use.. if you need to change the wording to address you over Aether you have my full permission." The lessons shelf dropped any lesson whose `for_` was the other seat.

## What the branch does
`meant_for` lets the two family seats (aria, aether) see each other's lessons. It is keyed on those two names and never on "anything not mine", so a new value stays out until it is chosen. Aletheia's lessons and anything relayed never cross. His passage is not edited; only the label says "taught to aether, yours to use". The log records each brought lesson's `for`.

## What it does not do
It adds depth, not new coverage: Aether measured twelve real messages and no silent message became loud.

## How it was checked
`tests/test_lesson_seat_family.py` (7 tests) with the real embedder; the skip says what is not checked.

## Open
Whether any other seat should ever be added to the pair; today none is.
