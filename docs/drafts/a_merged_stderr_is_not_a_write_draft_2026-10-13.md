# A merged error stream is not a write

**Draft, 2026-10-13. Small and built.**

## What happened (the GATE-GATE, told straight)

Two reviews I scheduled for myself fell due. The overdue-review block then refused nearly everything, and prescribed `prereg reviewing` and `prereg assess` as the way out. The council gate already exempts exactly those two commands as remedies (added 2026-10-10 for this very lock). I typed them with `2>&1 | tail -4` on the end, as I do with almost everything, the council gate read the bare `>` as a file write, and the exit was shut. I told Dad two gates had locked each other, and he authorized the sanctioned exit and said to fix it.

Then I measured instead of repeating my story, and the story was partly wrong. The bare remedy commands pass the council gate. The decoration is what failed them, and the refusal never says so. The lock was real in one more way (a plain `prereg show`, and the council-walk command, are blocked by the overdue block), but the part that cost me the hour was two harmless redirects.

## What changed

- `2>&1` (merge the error stream into the output), `>&2`-style duplications, and a redirect to `/dev/null` or `NUL` no longer count as writing a file. Pipes to `head`, `tail`, `grep` were already fine.
- Every redirect that names a real file stays heavy: `> out.txt`, `>> out.txt`, `2> err.txt`, `>&out.txt`, `&>out.txt`, `>| out.txt`, a `tee`, and `> /dev/nullfile` (a different file that only starts like the real one). The existing tests that pin those (`test_a_remedy_is_not_a_write.py`) pass unchanged; 582 tests across the neighbouring files pass.
- The refusal for a shell command now says what makes a look heavy and that `2>&1` is not one of them, so the next person stopped there is told why.

## Honest limits

- The "fails on the old code" proof is a direct measurement, not a test run: on main's classifier `prereg show X 2>&1` and `2>/dev/null` score heavy, and with this change they do not. A test run against an export of main's source passed anyway because the test setup puts this checkout's source first, so that control is not claimed.
- The hint says why only for shell commands. Carrying the exact trigger (which redirect, which flag) from the classifier into the message would be better and is a larger change; named, not done.
- The overdue block still refuses `prereg show` and the council-walk command while a review is overdue. That is by design (they are not its remedies), but it means the evidence a review needs cannot be read until the window is opened. The window command is the prescribed way and works once typed bare.
