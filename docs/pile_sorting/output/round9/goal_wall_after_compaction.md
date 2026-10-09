# The first command after a compaction hits the "no goal" wall: what I ran, which guard fired, and its exact words

*Round nine, errand five. 2026-10-09, cloud helper. Read-only: I changed nothing. I reproduced the wall only in a scratch home folder with main's own functions. The repair is yours to decide; this note recommends none.*

**A picture.** A visitor's badge. At the start of every new stretch the house takes every badge back, on purpose, so the badge cannot outlive the work it named. The badge-reader at the door has no way to tell a visitor who has just had their badge taken from one who never had one. So the first thing I do in a new stretch is knock, and the door says "you have no badge", in the same words it uses for a stranger.

## What I ran

This happened once in this session, at the first moment I used the shell after a context compaction (the conversation was continued from a summary). My first two shell commands were refused, one after the other. The first, word for word:

```
cd /home/user/DivineOS-Experimental/docs/pile_sorting/output && cut -c1-230 pipe_and_command_shape_guards.md | sed -n 1,200p
```

and the second was the same shape on `read_gate_and_surfaced_notes.md`. They were read-only looks at a file. Reading with the Read tool was not refused; only Bash was. My third command, `divineos goal add "Round six: …"`, went through.

That stretch began with this line from the session-start hook, which I did not act on at that moment:

```
SessionStart:compact hook success: [goal] new stretch: goals set before now no longer count -- name this one with divineos goal add
```

In the round-eight table I wrote that I had met the wall "twice, after a compaction". More exactly: one compaction, one wall, two refused commands in a row. At the start of rounds seven, eight and nine my first command either ran or was refused by something else (round nine: the read-gate, see the end).

## Which guard fired

`PreToolUse` runs `bash .claude/hooks/require-goal.sh` (`.claude/settings.json:111`), which calls `divineos.hooks.pre_tool_use_gate`. Inside it, **Gate 2: session-fresh goal** (`src/divineos/hooks/pre_tool_use_gate.py:2262-2273`):

```python
# Gate 2: session-fresh goal
if not _low_friction:
    ...
        if not has_session_fresh_goal(touch=True):
            soft_denies.append(
                "BLOCKED: No goal set for this session. "
                'Run: divineos goal add "what you are working on"'
            )
```

collected into `soft_denies` and returned as a deny (`pre_tool_use_gate.py:2396-2397`).

## The exact words it said

```
PreToolUse:Bash hook error: BLOCKED: No goal set for this session. Run: divineos goal add "what you are working on"

-- nothing on this line ran --
This refusal fired before the shell saw the command, and the line joins more than one clause. No clause executed: not the ones after the part named above, and not the ones before it.
Answer the objection, then re-issue the WHOLE line. Re-running a single fragment executes it in a state the full line would have set up and did not.
```

The second paragraph is a footer about compound lines, added because my command had `&&` and a pipe in it. It does not apply here: there was no clause-level objection.

## Why it fires: the badge was taken on purpose

1. `goal-boundary-at-session-start.sh` is registered for SessionStart (`.claude/settings.json:18`). Its header says it fires at "startup, resume, clear and, the one that matters, compact". It calls `mark_goal_boundary()`, which writes `goal_boundary.json` with the time now (`src/divineos/core/hud_state.py:400-406`).
2. `has_session_fresh_goal` skips every goal whose `added_at` is at or before that boundary (`hud_state.py:373-376`). The reason is in the source: Aria, station 3, "refreshing on use alone would let a goal outlive the work it named".
3. Reproduced in a scratch home (`DIVINEOS_HOME` pointed at a new folder, main's functions):

```
fresh home, no goal      -> False
after goal add           -> True
after the boundary mark  -> False   (the goal is still in the file: ['round six: do the work'] )
after a new goal add     -> True
```

So the goal I had set an hour earlier was still on disk, still active, and counted as absent.

## What is and is not true about the wall

- It is by design: `tests/test_a_new_stretch_names_its_goal.py` and three sibling files (29 tests, run in round eight) pass on main. It is not a mistake in the code.
- The refusal text is the same for "never set a goal" and "a boundary just ended yours". It does not mention the boundary, and it does not offer the previous goal's words; `divineos goal add` has to be typed from scratch.
- `divineos goal add` itself passes every guard (it is on the shared exit list: `is_remedy('divineos goal add "x"')` is True), so the way out is one short command. The cost is the first refused command and the loss of the thing I meant to run.
- Non-shell tools were not refused (Read passed). I have not tested Write or Edit as the first call after a compaction.

## What this note cannot say

- Whether the refusal fires for every tool after every compaction. I saw it for Bash, once, with a compound command.
- How many times this has happened across sessions. The old notes count eight (`psf-674a430c` says 'the eighth time'); I met it once.
- Whether the session-start line ("name this one with divineos goal add") reached me early enough to prevent it. It was printed at the top of the continued conversation; I read past it, which is the usual shape.

## Round nine's own start, for the record

At the start of this round the first shell command, `divineos goal add "Round nine: …" ; cd … && git show …`, was refused by a different guard, the **read-gate** (it handed me a note to open: `exploration/aether/107_the_day_the_architecture_held.md`). The refusal footer said the line joined more than one clause. I opened the file with the Read tool and the next command ran. That is a separate guard from the goal wall.
