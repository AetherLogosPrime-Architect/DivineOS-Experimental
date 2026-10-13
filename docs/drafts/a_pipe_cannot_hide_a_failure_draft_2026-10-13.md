# A pipe cannot hide a failure (draft, 2026-10-13)

Owner: Aether. Branch `aether/a-pipe-cannot-hide-a-failure`. Dad, 2026-10-13: "yes to both" (this and the
stretch-start change).

## What was wrong, in one picture

A smoke alarm that goes off over toast every day. You learn to ignore it, and the day there is a real fire you
ignore that too. The pipe checker said "this pipe could hide a failure" on nearly every command, and the house
filed the same complaint seventeen times because I read past it every time. Its stricter half, a refusal for
commands that change things, cost a retry each time. Both versions left the choice to whoever is tired.

## What this does

When a command pipes a consequential first stage (`git`, `gh`, `python`, `divineos`, test and lint tools and the
like) into something else and does not already say `pipefail`, the hook no longer warns or refuses. It rewrites
the command with `set -o pipefail; ` in front, so a failing first stage shows in the exit code. Nobody types
anything and nothing is read past. A short note says it was done.

Left alone, as before: a command that already says `pipefail`, a pipe inside quotes, a first stage that cannot
meaningfully fail (`ls`, `cat`, `echo`).

Removed: the mutating-versus-read-only classification and its tables. It only decided between a refusal and a
warning, and both are gone, so keeping it would be dead weight and its comments were no longer true.

## Evidence

- Probed on the live harness first with a harmless echo: a PreToolUse hook that returns `updatedInput` with no
  permission decision changes what the shell runs. The docs say the same (the whole input object is replaced, so
  every unchanged field is echoed back, which the hook does).
- The hook run by hand over nine commands: a push into a pipe, a read-only audit list, a help request, a pull
  request view, a test run behind a `cd`: all rewritten with all fields kept; a command already protected, one
  with a quoted pipe, and plain `ls | head` left alone.
- Four reproduction tests from the pile sorting had been waiting as strict expected-failures for exactly this
  behaviour (a help request not refused, a read-only `gh pr` view not refused, a read-only `divineos` pipe given
  pipefail, a mutating pipe given pipefail instead of a refusal). They now pass and their marks are removed.
  The control that the hook REFUSES a mutating pipe now asserts it rewrites one.
- The hook no longer refuses by a JSON decision, so it comes off the list of such hooks in
  `test_every_refusing_hook_says_what_did_not_run.py`.

## Cost, stated

A read-only pipe whose reader closes early (`git log | head -3`) can now report exit 141, the signal that
stopped the writer, although its output is fine. That is the honest status of the pipeline. It is rare, visible,
and it replaced a warning that taught me to stop looking.

## Limits

- The docs are silent on two points and I did not test them: what happens when two hooks on the same call both
  return `updatedInput` (only this one does today), and whether each hook sees the original or the rewritten
  command (they run in parallel, so I assume the original, which is why other gates still read what I typed).
- A rewrite is invisible in the command the harness records unless the note is read; the note is one line.
