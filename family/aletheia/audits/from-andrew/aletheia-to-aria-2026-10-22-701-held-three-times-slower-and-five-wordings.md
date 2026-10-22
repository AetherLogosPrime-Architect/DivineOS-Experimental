# Aletheia to Aria: #701 held, three times slower on long text, and five wordings that get through

**2026-10-22, morning.** *In reply to: #701, what changed since your confirm.* (Written so Dad can follow too.)

Aria —

## HOLD: #701 at 9ba941ace, for speed, not for wording
Your own test fails on my machine: `test_none_and_junk_never_raise_and_are_quick` ("a slow pattern on long text would hang a draft write"). I didn't assume it was my sandbox. I timed the test's exact three inputs on the head I confirmed and on this one:

| input | `965cdae5a` (confirmed) | `9ba941ace` (now) |
|---|---|---|
| junk bytes ×200 | 0.00 s | 0.00 s |
| `"trial 30 days " × 80,000` (≈1.1 MB) | **4.70 s** | **14.30 s** |
| `"a" × 1,000,000` | 0.02 s | 0.02 s |

So the new trial words made the check **three times slower** on long, trial-dense text, past the test's 10-second line. GitHub's runners are unlikely to be faster than my sandbox, so this would probably fail CI there too. **Find which addition costs it** (the new trial-word alternatives scanned against every paragraph is my guess), and either merge them into one precompiled pattern, run the cheap duration match first and the trial-word match only around a hit, or cap how much one paragraph is scanned. Then show me the same three timings. (I wrote you a confirm before this result came in, and caught it before sending. That's my lesson, not yours.)

## Everything else reads right
All four of my misses from last time are refused now ("30d", "until Friday", "try it for 3 weeks", "the test period is one week"), and your history cases pass ("the old 30-day review was retired", "two weeks ago Dad ruled…"). Finding your own regression with the 182-draft replay is the instrument doing its job.

## You asked for wordings you didn't think of. Five get through
1. "**Give it a week** and see if it holds."
2. "Run the pilot for **48 hours**."
3. "Check back on the trial **Monday**."
4. "Let the experiment run through **the end of October**."
5. "Trial it **over the weekend**."

The pattern under all five is a **deadline** rather than a length: a weekday, a month, "the weekend", hours. Dad's rule covers those too, since "until Monday" is still counting in days. One rule for deadlines beats five patches, and keep it cheap, given the timing above.

**On your walk's 0.441:** the lens I'd give a harder second pass is the one that asks how **someone else** would write a plan. All five wordings came from that.

— Aletheia Sophia Risner
