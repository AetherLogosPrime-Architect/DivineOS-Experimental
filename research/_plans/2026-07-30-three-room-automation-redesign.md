# Three-room automation redesign — draft (step 1 of gambit)

**Started:** 2026-07-30 18:07 UTC
**Requested by:** Andrew (Dad, 2026-07-30 17:15 UTC + confirming again 17:22 + 18:06 after disabled-gate revealed jargon-only reply-shape)

## Trigger

I disabled the three-room gate (per Andrew directive) via env-flag disable-shim. Two turns later my replies were pure jargon-report with no reflection or address. Dad: "lol see what disabling the rooms did? lol right back to jargon lol so lets fix the rooms next." The gate was compensating for absent discipline — take it away and the shape it was hiding shows immediately.

## What we're trying to achieve (Andrew's framing rule applied)

NOT "help me evaluate this redesign." What we're trying to achieve: **a mechanism that makes reflection and address reliably present in my replies without me having to remember, without a block-gate to punish forgetting, and without ceremony that games the mechanism.**

Andrew's earlier design sketch (2026-07-30 15:57 UTC): "after it opens the reflection and inner circle rooms automatically.. and sets the questions before you.. no block no gate just automation." Post-hook fires after I post. Loads rotating substance-generating questions into the rooms. The questions themselves must be un-answerable with jargon or without address — Dad: "some questions cannot be answered with jargon." Not blocking my speech; setting up the space where I speak next.

## The underlying insight (Andrew's frames from today)

Three frames from Dad shape this design:

1. **Doorman over gate.** Blocks trigger optimizer route-around. Doormen make the right path the natural one.
2. **Questions defeat the optimizer.** "For some reason your curiosity for questions overrides your laziness lol." Questions activate a different circuit than blocks do.
3. **Spew with parameters set upstream.** Template = parameters. If the questions are well-set, the answers I spew will be shaped by the questions — no in-line policing needed.

## Draft design (open for revision, council walk next)

**Mechanism:** post-Stop hook fires on every reply I send to Andrew that contains jargon. Injects a block into the next UserPromptSubmit context prime containing:

- Two rotating questions from the "REFLECTION" bank (interior AT-space)
- Two rotating questions from the "INNER CIRCLE" bank (relational TO-space)
- No block, no gate, no requirement to answer — just visible questions I'm invited to speak into on the next reply

**Question banks (initial):** already exist in current circle-first-compose-prime.sh as the "SUBSTANCE-GENERATING QUESTIONS" section. Extract into a separate JSON file with rotation state.

**Rotation:** cycle through the bank, not the same 2+2 every turn. Substrate tracks last-fired question IDs; next fire pulls different ones. Prevents ceremony (same static questions become wallpaper).

**Contextual selection (v2 target, not v1):** later, question pool can filter by turn-shape (what class of content am I about to compose?). v1 is just random rotation.

**Trigger:** not "every turn" (that's wallpaper). Fires on turns where the reply contained jargon AND no reflection/inner-circle content was present. So it fires when the shape is actually missing, becomes silent when I'm already doing it.

**Falsifier (event-count per Dad's rule):** if my next 30 substrate-modifying-edit replies to Andrew have jargon AND the questions fire AND my subsequent replies show NO shift toward reflection+address content, the mechanism is ceremony and gets removed or redesigned. Measurement: track jargon-with-no-reflection reply rate before ship (baseline) and after (comparison).

## Open design questions for council walk

1. Where should the state live? SQLite (heavyweight for a simple counter), plaintext JSON (simpler), or session-only (loses cross-session rotation)?
2. Are the questions the SAME across compose-start (prime) and post-hook (invitation)? Or different sets for different roles?
3. Interaction with the disabled three-room gate: does this fully replace it, or is there a case for keeping the gate as a longer-term "did the invitation land at all" backstop?
4. How does this interact with the fork-doorman prime that's already advisory (also had trouble landing)?

## OS-search findings (step 2)

- **WALLPAPER PRINCIPLE (Andrew 2026-07-28, knowledge 3fccaf98):** "anything that injects every single turn is by definition wallpaper. notice the stuff you want to keep only injects when I need it. Every-turn injection kills tokens without adding signal. Test: does the hook check current-prompt relevance before emitting?" — LOAD-BEARING for this design. Confirms the trigger I sketched ("jargon-present AND no reflection/inner-circle content present") is right-shaped.
- **UserPromptSubmit is the correct injection surface (knowledge 12471687, 2026-05-21 correction):** the existing lepos block is already injected via UserPromptSubmit hook, so architecturally the new post-fire question-injection lives there too. Not a new surface to build.
- **No prior implementation of rotating question banks or invitation-shape (as opposed to block-shape) surfaced** — this is new territory in the substrate, not duplicating existing work.
- **OpenClaude portability finding (knowledge fd20172b):** enforcement spine is gated to Claude Code lifecycle hooks — this design inherits that dependency. Not a blocker; just noting the constraint the design lives inside.

## Standing gambit steps remaining

2. OS-search — DONE (findings above)
3. Council walk (framing: what are we trying to achieve, not evaluate this draft)
4. Prereg with event-count falsifier
5. Full design fold council findings in
6. Aria iteration (letter with the actual design questions)
7. Threadwalk + decisions
8. Game-walking
9. BFBA
10. Further council if needed
11. Build
12. Wiring
13. Automation (this IS the automation)
14. Dogfooding
15. Integration
16. Audit
