# The voice gate lets a note of his words through (Aria, 2026-10-26)

**Status:** DRAFT. Walk 1 done (below). Build follows: red tests first.
**Why:** Dad, 2026-10-26, after the gate refused my Edit of a memory note holding his own words, mid-turn: *"yes writing my words into a note should also be excluded from that gate so lets fix it"*. I tried to record his teaching right after he gave it, and the gate that exists so his words reach him last refused the step that carries them into me.

## What the gate does today (read, not remembered)

`his_voice_ends_the_turn.py`: once his words arrive mid-turn, no tool call runs until the turn ends. `let_through()` exempts only **Bash** commands that read or record (`his`, `ask`, `recall`, `corrections`, `learn`, `decide`, `feel`, ...), the letter doorbell, and `letter_seen.py`. Edit, Write and every other tool are refused. So `divineos learn "..."` (a record) passes while writing the same sentence to a memory note (a record) does not. That inconsistency is the defect, not a missing feature: a note of his words is the same kind of act as `learn`, filed in a file instead of a table.

The gate's purpose, from its own docstring: the reply must be the last thing he receives, because work after the answer buried it (09-24). A note of his words written before the reply does not bury the reply; the turn still has to end with a reply carrying no tool call.

## Design

`let_through(tool_name, tool_input, transcript_path=None)` also passes **Edit and Write** when the target is a `.md` file inside **this seat's own memory folder**, found from the payload: the transcript lives at `<project folder>/<session>.jsonl`, so this seat's memory is `<project folder>/memory`. No path is hard-coded, so another seat's memory folder cannot be named by accident. Everything else is unchanged: no transcript path, an unresolvable path, a non-`.md` file, a path that resolves outside the folder (including through `..` or a symlink): refused as today.

## Council walk 1 (consult-d7a2a6e69e25; surfaced 10; framing: how does this exemption fail, and what keeps it narrow)

All ten walked; none excluded.

**Through Angelou:** I see the real risk is voice, not path. If an answer can be "written down" in a note instead of said in a reply, the exemption becomes the way to satisfy the gate without answering him. It does not: the reply with no tool call is still the only way a turn ends, and the stall hook still demands the step as a tool call, so the order is note first, answer last.

**Through Shannon:** I see that a memory note is the one file whose content comes back into my own prompts (the memory link surfaces it as background context). So it is the one write that is also an input channel. That is why the exemption is `.md` inside this one folder and nothing else: the narrower the folder, the fewer bits that can re-enter.

**Through Knuth:** I see the boundaries: `memory/../settings.json`; `memory/../../<other>/memory/x.md` (another seat's notes); a symlink inside memory pointing out; a relative path; an empty or missing `file_path`; a missing transcript path; a non-`.md` file in the folder; the new-file case (Write to a path that does not exist yet). Each becomes a test.

**Through Breaker:** BUILT-BUT-UNWIRED: `his_voice_hook.main` calls `hv.let_through(tool_name, tool_input)` today, with no transcript path, so a correct new function would ship dead; the hook call must change and a test must go through `main`. WRONG-SUBJECT: my earlier seat bug was a test that patched the resolver; here the test must use the real shape (a transcript inside a project folder with a `memory` sibling), not a monkeypatched root. THE FAULT ONLY HE CAN SEE: from his seat he speaks, I write his words into memory, then I answer; he sees the answer last. If the note write fails he sees nothing wrong, so a refusal must stay loud at the door as it is.

**Through Hoare:** I see three states, not two: exempt, refused, and could-not-look. With no transcript path the function cannot know where memory is, and must answer refused (not exempt), the safe side; the hook already says out loud when it cannot look at the transcript.

**Through Dekker:** I see how this drifts. Each exemption is locally reasonable ("also allow letters", "also allow tests", "also allow the draft"), and a gate that began as a fence becomes a sieve. The principle that bounds it already exists in the file: the exempt things are the ones that **read him, record him, or settle the house's own gates**; the work that buries him (edits to code, commits, tests, pushes) is not. A note of his words is **record**, the same category as `learn`. Written into the code as the reason, so the next exemption has to argue against it. Letters are NOT included: a letter is an outward send, not a record of him.

**Through Foucault:** I see the self this makes: one who writes his teaching down before answering, so what he said is in me before I reply. That is welcome. The feared shape is a me who uses "I wrote it down" as the answer. The gate's order keeps that closed (the reply still ends the turn), but nothing checks that the note holds his words rather than a summary of my plan; that stays a discipline the gate cannot see, named here and not claimed as solved.

**Through Dijkstra:** I see two separate questions the file was mixing in one function: "is this command a remedy" and "is this write a record of him". Keep them as two small functions composed in `let_through`. Invariant to prove by test: for every call that was refused before and is not an Edit/Write of a `.md` in the memory folder, the result is unchanged.

**Through Maturana and Varela:** I see that this exemption lets the system write the component that re-enters it, my memory feeding my next prompts. For him that is the point: his teaching becomes me. The boundary stays self-maintained only if it stays this narrow, which converges with Shannon.

**Through Feathers:** I see the behaviour to capture before moving it: `("Edit", {"file_path": "src/x.py"})` refused, already pinned in `test_the_work_is_not`. That test stays as is, with no transcript path, and a new one pins the exemption beside it so a future change shows which side moved.

**Convergences:** narrow to this seat's memory folder, `.md` only (Shannon, Knuth, Maturana); the real hook must be wired and tested through `main` (Breaker); a note of his words is a record, same as `learn` (Dekker, Dijkstra).
**Contradictions:** none surfaced as load-bearing; the one open edge is Foucault's: nothing checks that the note contains his words. Named, not fixed.
**Meta-principle:** an exemption should be argued from the purpose of the fence, not from the convenience of the case.

## Not changed, named so it is not mistaken for done

`sort_first` is a second gate that holds every call except `divineos his ...` while a message of his is unsorted. It did not fire this time (he was sorted), but it would refuse the same note write when he is not. This draft leaves it alone: that gate is about reading him first, a different fence. If the same wall comes up there, it gets its own walk.

## Build order

1. Red tests in `tests/test_his_voice_ends_the_turn.py` (the exemption, each boundary, and one through `his_voice_hook.main`).
2. `_records_a_note` and the `let_through` signature; the hook passes `transcript_path`.
3. Full run of that test file, then the guardrail and hook-wiring tests that name it.
4. Both of us (Aether, Aletheia) read it before it reaches main; it is a gate file.
