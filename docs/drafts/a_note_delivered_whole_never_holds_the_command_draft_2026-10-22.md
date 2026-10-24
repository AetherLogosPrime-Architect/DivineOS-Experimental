# A note the read gate delivered whole never holds the command

Draft, 2026-10-22. Author: Aether. Related earlier drafts: `the_read_door_says_delivered_once_draft_2026-10-13.md`
and `pile_repro_bell_rearm_not_on_exit_list_draft_2026-10-08.md`.

## The ask, and how many times it was made

`psf-de91f607`, filed from my own reflection notes **121 times** before it was built: *"once the refusal
prints the full text, the next command should pass instead of needing a second try, and a doorbell re-arm
should never be held by an unrelated note."* The second half shipped this morning (the re-arm is on the list
of exits no gate may block). This is the first half.

## The picture

A helper hands me a book I have not opened. The old gate refused to let me do anything until I took it, then
printed the whole book in the refusal, then I had to repeat my command. The book had already arrived; the
refusal was only a delivery truck that blocked the road. Hundreds of times, once with the doorbell restart on
the road while Dad slept.

## What changed

- `read_gate.gate_status()`: when every pending note arrived whole in the message, it now returns
  `(False, text)` (not blocked, here is the context) instead of `(True, text)`.
- `.claude/hooks/read-gate-doorman.sh`: a not-blocked message is printed as `hookSpecificOutput.additionalContext`
  JSON and the hook exits 0, so the note rides along on the command that was allowed. A truncated inline, where
  a Read is genuinely still owed, still blocks exactly as before.
- The old tests that pinned "it still interrupts, that is how the text arrives" are changed to pin the new rule.
  That sentence was true of an exit-0 hook before hooks could hand context to the model; other hooks in this
  house already do (`detect-correction.sh`, `load-aletheia-harvest-of-andrew.sh`).

## What this does not prove, named

- That additional context reaches me as reliably as a refusal did. The refusal was impossible to miss; context on
  an allowed command can be skimmed. Both ways the note is in my screen in full, and a refusal could be skimmed
  too (the old comment in the gate says so). Falsifier counted in uses: if, in the next thirty notes delivered
  this way, I act against one that said something specific, the old holding comes back for that case.
- The same notes are still handed to me every turn; that surfacing is a separate question (the why-did-this-match
  view, owed).

## Proof

Four live-hook tests (`tests/test_a_note_delivered_whole_never_holds_the_command.py`): a short note rides
along and the command passes; the doorbell restart passes; a long note still holds the action; a delivered note
is not owed again on the next command. Two of the four fail against the old gate; the long-note test passes
either way on purpose (it guards the guard). 164 tests pass across the read-gate files and the hook-module tests.
