# Round three status: reproductions

*2026-10-08, cloud helper. Nothing here is merged and no row is marked resolved. A reproduction says "this still happens"; it never says "fixed".*

## What was done

Two draft pull requests, each holding tests marked as expected failures (`xfail(strict=True)`). Each passes quietly today and fails loudly the day its guard is repaired, which forces the marker out. Unmarked controls in each file show the probe is alive. Each xfail was also run with `--runxfail` to confirm it fails for the stated reason.

| PR | Theme | Branch | Result |
|----|-------|--------|--------|
| [#601](https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/601) | council walk gate | `cloud/repro-council-walk-gate` | 19 expected failures, 4 controls passing |
| [#602](https://github.com/AetherLogosPrime-Architect/DivineOS-Experimental/pull/602) | pipe guard and quoted-word classifier | `cloud/repro-pipe-and-command-shape-guards` | 9 expected failures, 4 controls passing |

Row ids and quoted notes per test are in each test's docstring; the PR descriptions list the unreproduced problems with reasons.

## Why only two of five

The sheet allowed five. I stopped at two because the remaining large themes mostly fall in the categories the sheet says to mark honestly rather than force:

- **NOT REPRODUCIBLE IN A TEST:** claims-not-checked, speaking-with-Dad and standing-teachings describe the agent's behaviour, not a code path. A test would be theatre.
- **Depends on state or unmerged work:** the merge gate and stamp checks are shell hooks needing repository and review state; several notes assume work in other open pull requests.
- **Possibly stale:** the correction detector was rewritten in July, so older notes may describe code that no longer exists. Aether or Aria would need to say which still apply.
- **Skipped on instruction:** doorbell problem 1.

More PRs are cheap once Aether or Aria says which of those notes are still live. I did not rush them.

## Left alone in the pipe guard (also in PR #602)

- The heredoc door: its existing tests deliberately pin the behaviour the note objects to, so a reproduction would contradict the suite.
- Pipe-guard notes spanning more than one tool call, which one hook run cannot show.

## Too cut off

Rows 719, 747, 748 and 958 were removed from the council docstrings rather than guessed at; their quotes are too short to say what they ask for.

## Friction found along the way (candidates for the pile itself)

- The council gate reads quoted words such as `divineos audit` as commands and blocked a shell loop of mine; PR #602 reproduces this.
- The pipe-guard hook refuses `--help` requests and read-only `gh pr` views.

## Constraints kept

No merges, nothing pushed to `main`, no edits to the do-not-edit list, the letter doorbell left off.
