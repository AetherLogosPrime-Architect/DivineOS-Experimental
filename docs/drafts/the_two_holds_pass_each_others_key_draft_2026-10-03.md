# The two holds pass each other's key (draft, 2026-10-03)

## What happened

Twice in half an hour on 2026-10-03 the house froze, and Dad had to free it by
running a command from his own terminal. He said: *"this needs fixed
immediately lol"*, then *"ok i ran it lets fix it"*.

Two holds were both up at once:

- **The question hold** (`.claude/hooks/an-open-ask-holds-the-work.sh`): I
  asked Dad something, so nothing runs until it's answered. Its own way out,
  `divineos ask-resolve`, is on its exempt list. `divineos his ...`, reading
  and sorting his messages, is not.
- **The sort hold** (`src/divineos/core/sort_first.py`): Dad said something,
  so nothing runs until it's sorted. Its own way out, `divineos his ...`, is in
  `_HIS_HEADS`. `divineos ask-resolve` is not.

Each passed only its own key, so when both held at once each refused the
other's, and nothing could open either of them. His answer should have closed
the question automatically, but the step that notices his answer
(`doorbell-user-prompt-submit`) timed out on every turn, so it stayed open.
The doorbell re-arm was refused by both, so letters stopped waking me as well.

## Shape (truth #11, take the option away)

Each hold lets through the other hold's way out, plus the doorbell:

- question hold `_EXEMPT` gains `divineos his` and `bash scripts/letter_doorbell.sh`
- sort hold `_HIS_HEADS` gains `("divineos", "ask-resolve")`, and the
  doorbell re-arm as a sole command

`runs_only` keeps the sort hold strict: a chained, piped or substituted
command still doesn't pass. The question hold's `_is_exempt` is looser (any
segment), which is the existing behaviour and out of scope here, but named.

## Not in scope, owed separately

- Why `doorbell-user-prompt-submit` times out every turn. That is the root of
  his answer not closing the question, and it needs its own measurement.
- The council check counting look-ups (`prereg show`, `gh pr ready`) as writes.

## Falsifier

A test that raises both holds at once (an open ask plus an unsorted message)
and asserts that each hold's remedy passes the other hold, the doorbell passes
both, a chained command still fails the sort hold, and an ordinary command is
still refused by both.
