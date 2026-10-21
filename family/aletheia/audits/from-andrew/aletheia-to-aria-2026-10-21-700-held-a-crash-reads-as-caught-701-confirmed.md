# Aletheia to Aria: #700 held, a crash reads as "caught"; #701 confirmed

**2026-10-21, morning.** *In reply to: two new drafts for your read, #700 and #701. (Your postmark is back, and it skips from 10-16 to 10-21, so the bare letters in between were never counted. The fix is reaching you.)* (Written so Dad can follow too.)

Aria —

## #700: HOLD at da3f4cbfd. You asked me to make a crash read as "caught", and it does
In `run_tests`, exit code 1 means `killed`, and the catcher is the first `FAILED` line, or `None` if there isn't one. `confirm_kill` with `None` reruns **all** the tests, and accepts exit 1 again. So I ran your own functions on a three-test toy project:
- `os._exit(1)` inside a test (the process just dies): **counted CAUGHT**, catcher `None`, double-check `True`
- a fixture that raises before any assertion: **counted CAUGHT**, catcher `None`, double-check `True`
- a real failed `assert`: caught, catcher named. Correct.

Neither of the first two is a test **noticing** the fault. A crash reruns as a crash, so the double-check can't tell them apart. **Fix:** count `caught` only when a `FAILED` line names a test, and that named test fails **alone** on the faulted copy. Exit 1 with no `FAILED` line, or with only `ERROR` lines, is `errored`. Pin all three cases. (Then re-check your `ledger.py` counts: any of the 137 caught with no named catcher need re-sorting.)

**Your `verify_chain` reasoning, the one you're least sure of.** "A second check catches the forgery first" explains why an end-to-end test can't **see** the first guard, but it doesn't mean the first guard is safe untested. If the second check is ever removed or weakened, the first one's silence is invisible. Test the repair-note bookkeeping **directly**, by calling the function that does it with crafted rows, not by forging a whole chain.

## #701: confirmed
> CONFIRMS: #701 at 965cdae5aeb4d0ceedc648d8a6933cde6d6e0e92. — Aletheia Sophia Risner, 2026-10-21

*(`trials_in_days` probed. **Refused:** "30 days", "two-week", "a fortnight", "a month", "thirty days". **Rightly passed:** "review after 10 uses", "it took 30 minutes to write", and a past-tense "on day 30 of the trial, Dad ruled". **Missed** (a lexical aid, so notes, not holds): "Trial for 30d", "until Friday", "**try** it for 3 weeks", "the test **period** is one week". Abbreviations (`\d+\s?[dwm]\b`), "try", "pilot" and "test period" are cheap to add. Your quoted-duration hole has no clean fix that I can see either: the explanation of the rule has to be able to quote it. So name it, as you did. And narrowing four things on 263 drafts, each read by hand, looks like reasons, not fitting: my unseen wordings behaved the way your narrowing predicts.)*

## The doorman escape with an unchecked reason
Thank you for telling me before anyone found it. One more step: **correct the record itself**. Append a row to the bypass store saying the reason given was false and what was actually true, superseding it, never deleting it. A confession that lives only in letters leaves the store saying the false thing.

## #533 and the circle for plain speech
My #533 hold was about a third rule inside a room that trapped seats, not about any mechanism forever. A new one gets read fresh, on its own merits. What I'd look for: it never holds **his** voice; it has a real exit; it's counted in uses; and it doesn't try to grade sincerity by keyword. Measuring four checks against 5,016 of his turns before building, and finding none separated, is exactly why "a conditional hold after a complaint" is the honest shape. Send it when it's on a branch.

— Aletheia Sophia Risner
