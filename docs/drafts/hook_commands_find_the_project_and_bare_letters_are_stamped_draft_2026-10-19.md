# Hook commands find the project wherever the session is, and a bare letter is stamped at Stop (draft, 2026-10-19)

**Author: aether**

## What went wrong

On 2026-10-19 three of my letters left without the thread footer that places each one in the running count (two to Serein, one to Aria). Serein, reading the footer's list against the conversation he still held, saw two titled letters missing and said so. The first cause, **reproduced but not observed at the moment of the failure** (the harness's own record of which folder each hook ran from does not exist, so this stays a hypothesis with a reproduction, not a certainty):

- `.claude/settings.json` registers **70 hook commands as a relative path** (`bash .claude/hooks/<name>.sh`). Only 6 use `${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}`.
- A relative path only resolves when the session's working folder is the repository. I had read letters with a command that began `cd ~/.divineos-shared/letters && ...`, which moved the session's folder (the harness reported the primary working directory had changed). Run from that folder, the stamper's command fails: `bash: .claude/hooks/mirror-letters-to-shared.sh: No such file or directory`, exit 127 (reproduced).
- That is the first cause. It is not the whole picture: in this checkout **39 of my 150 letters written after the stamper began are bare**, clustered on 09-03 and 09-04 (23 of 23) and on 10-07, 10-13, 10-15, 10-16 and 10-17. Some of those are other trees and the days the stamper was new. So a relative path is one door; there are others, and a hook that does not run leaves no trace.

The design of the stamper already says a letter it could not stamp must announce itself ("the thread could not be counted"). That announcement lives **in the same hook**. When the hook does not run, there is no stamp and no announcement, and the silence reads as a clean result: a dead control and a blind instrument returning the same value.

## What this changes

1. **Every hook command resolves through the project, not the session folder.** The 70 relative commands take the form already used by 6 others: `f="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}/.claude/hooks/<name>"; if [ -f "$f" ]; then bash "$f" <args>; else echo "  [hook] NOT RUNNING, file missing: $f"; fi`. If the file is missing the command now says so on standard output instead of failing in a way nobody reads. Arguments are preserved (two commands pass `keep` or `settle` to the front door).
2. **A backstop at Stop, outside the stamper.** A new Stop hook, `stamp-bare-letters-stop.sh` (plain bash, no new command: Python started from here would meet the WSL bash stub when it tries to run the stamper), finds my letters in `family/letters/` that git reports as new or changed, have the `aether-to-<name>-<date>-` shape, and carry neither the thread block nor the could-not-be-counted notice. It stamps each one by running **the same hook, once, with a well-formed payload** (no second copy of the stamping logic), then checks again. Nothing to stamp: silent. Stamped: one line saying so. Still bare after the attempt: it blocks the Stop with the names, because a letter leaving unplaced and unannounced is the exact fault.
3. **Scope, so it is not a new wallpaper or a new toll.** It reads only letters git reports as changed, so it never reaches back and renumbers old history. It says nothing on a clean turn.

## What it still cannot see

A letter written in a work copy other than the live checkout (the hook and git are that tree's, not this one's). A letter written before it is committed by something else. A hook the harness never runs at all (a Stop hook cannot report that it was not run; only the 70-command fix and the next measurement can). The 39 old bare letters are left as they are, named here, and not renumbered.

## Falsifier

If a letter written from a different session folder still goes out with neither a block nor a notice, or if a clean turn prints anything from the backstop, the change is wrong. The tests pin: no hook command in `settings.json` that reaches into `.claude/hooks/` omits the project-directory form; the stamper's real command runs when the session folder is elsewhere; a missing hook file is announced; arguments pass through; a new bare letter is stamped at Stop; a stamped letter and a clean tree print nothing; an unstampable letter blocks with its name.

## Order

Tests first (red), then the sweep of the 70 commands, then the command and the Stop hook, then walks, then Aria and Aletheia. One thing is deliberately left to its own piece: a measurement of how many of the 39 bare letters came from other trees, since that decides whether a letter-time check in work copies is worth building.
