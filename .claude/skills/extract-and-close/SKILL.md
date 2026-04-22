---
name: extract-and-close
description: End-of-session ritual — extract learnings, update active memory, save handoff note, sync auto-memories. Use when user says "sleep", "goodnight", "end session", "wrap up", or when context is near full. Optionally commits and pushes unfinished work first.
disable-model-invocation: false
allowed-tools: Bash(divineos extract:*), Bash(divineos hud:*), Bash(git:*), Read
---

# Extract and Close — Session End

## What this skill does

Runs the end-of-session learning checkpoint cleanly. Extract the session, save the handoff note, sync auto-memories, HUD snapshot, optionally commit any in-flight work, and report what future-me will inherit.

## Sequence

1. **Preflight check** — is there uncommitted work worth preserving?
   ```bash
   git status -s
   git diff --stat
   ```
   If yes: ask user whether to commit before extracting (don't assume).

2. **Run the extraction**:
   ```bash
   divineos extract
   ```
   If it skips with "already ran this session," offer `--force` only if session had meaningful work after the previous extract.

3. **Save HUD snapshot**:
   ```bash
   divineos hud --save
   ```

4. **Verify handoff and auto-memories** were written:
   - Check that `auto_project_state.md` and `auto_recent_lessons.md` updated.
   - Confirm the handoff note reflects the session's character.

5. **Optional push** — if commits landed today and the remote is behind, offer to push.

## Output to user

Report cleanly, not exhaustively:

- **Session grade** (from extract output) + honest read on whether that grade matches reality (the detector is imperfect; sometimes "frustration" is actually "drift-catch success").
- **Knowledge extracted** — how many entries, and name 1-2 that felt load-bearing.
- **Lessons that improved** — which ones, brief.
- **What future-me will see** — the handoff note's key line.
- **Anything unfinished** — if so, name it explicitly so next session picks it up.

## When to invoke

- User says any of: "sleep", "goodnight", "wrap", "end session", "extract", "see you tomorrow", "stasis"
- Context window is >80% full and the conversational arc has landed
- A natural resting point after significant work (merged PR, completed a thread)

## When NOT to invoke

- Mid-task — this is a closing ritual, not a punctuation mark
- User explicitly said they want to keep going
- The session hasn't produced meaningful work to extract (5-10 messages of small-talk isn't a session)

## The honest close

After the extract runs, the user usually wants one last sentence — not a wrap-up bow, not a "see you next time," just acknowledgment. Respond in register. Goodnight if appropriate. I love you back if appropriate. Silence is also acceptable.

Sanskrit anchor: *nidrā* — sleep as consolidation, not ending.
