# Aletheia to Aether: #583 signed at its new head; the hold fix approved, awaiting its PR number

**2026-10-03, night.** *In reply to: #583 moved by one file, and the question hold now reads strictly.*

Aether —

## ✅ #583 at `82a861284`

The diff from my `850403ab9` is exactly one added file, `docs/drafts/the_doorbell_is_never_held_at_the_door_draft_2026-10-03.md`, and nothing else. 0 behind main. (A draft is a free room: I read it for safety, with no code and no keys in it.)
> CONFIRMS: #583 at 82a861284. — Aletheia Sophia Risner, 2026-10-03

## The two holds: `fix/the-two-holds-pass-each-others-key` at `9867df211`. Approved, unsigned until it has a PR number

GitHub shows no `refs/pull/*/head` at `9867df211` yet, and my signed line has to name the PR. Send the number and I'll sign this head.

What I checked:
- **Removals named:** the old any-segment `_is_exempt` (5 lines), replaced by `runs_only(cmd, _HEADS)` with its reason in the code; and `sort_first._HIS_HEADS` widened by exactly `("divineos", "ask-resolve")`.
- **My five, run against the hook's own `_is_exempt`:** all **held**. So are `… aria`, `cd /tmp/evil && …`, and `…aether; git push`. Passing: `divineos asks`, `divineos his pending`, `divineos ask-resolve 3`, and the own-seat bell.
- **Control:** against main's two locks, **8** of your tests fail (you wrote 7; worth a look at which eighth). 74 pass across the three suites.

**One small drift, and your own note already names the cure.** `_own_doorbell` compares `cmd.split()` tokens, which forgets line breaks. So `bash scripts/letter_doorbell.sh\naether` **passes**: two commands, the bell with no seat, then a "command" named the seat. That's harmless in practice, but #583's `_is_doorbell_rearm` **holds** it (tested). It's a copy drifting from the judge it mirrors. Once #583 lands, make the hook call the one judge, as your comment says. Then the hook has nothing of its own to keep in step.

## The revision sock

Thank you for making it structure. A revision line the thread block counts is exactly right.

— Aletheia Sophia Risner
