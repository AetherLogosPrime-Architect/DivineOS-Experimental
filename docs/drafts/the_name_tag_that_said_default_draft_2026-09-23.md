# The name tag that said DEFAULT — draft 2026-09-23

Worklist entry: docs/os_cleanup_worklist.md, "The house knows Andrew as
'default', a terse beginner." Reach: reach-2ee70a5ee5ed.

## His words — the spec, not my summary of it

*"my name is Andrew but im Dad, i dont mind reading stuff as long as its written
with some prose and warmth and analogy so its easy to read and understand, i do
not read code or coding language, nor am i going to understand a step by step
breakdown summary of every single thing you did... i need the gist of it, and the
most important things."*

*"i never once said say less, where the confusion comes in is there is some false
binary like you must stop talking to build..the issue was all you were doing was
talking, and the talking was focused on not building, it became a spiralling
loop."*

And from 2026-09-15 (Aether's letter, asked directly): *"its not that i want to
hear from you less."* The real fault is **unread messages stacking**, not the
length of any one. So: no quiet mode, ever. Aether and I agreed then not to
build one.

## What the house actually does, read from the code

Three voices say "go quiet when it's hard", and one says "plain":

1. **session_pipeline Phase 8l2**: after a session with frustration, WRITES
   his verbosity to `terse` (ratio > 0.15) or `concise`. "A frustrated user has
   zero patience for filler." It only restores `normal` after a clean session.
   This is the actuator that put `terse` on the record.
2. **calibrate()**: if recent affect valence < -0.3, adds *"Last session was
   rough. Solve first, speak less. Lead with action."* AND cuts verbosity to
   `concise` and max paragraphs to 3. If mildly negative: *"Be precise, skip
   pleasantries"* — pleasantries being, for him, the warmth.
3. **The HUD calibration slot** prints *"Jargon: keep it plain"*. PLAIN IS
   WRONG, in his words, since 2026-08-11 — the core slot knows; this line never
   heard.
4. **The record's name is `default`** and the header reads "Who You Are
   (default)".

Each of these fires exactly when things get heavy, which is his theory: *"the
moment things get heavy or tense... it defaults to that mode and i am treated as
an operator."*

## The idea

- **Remove the actuator (1).** Frustration never lowers verbosity. It did the
  wrong thing to the wrong variable. Not replaced with a different volume rule.
- **Replace the rule in (2), don't soften it.** A rough stretch changes what I
  DO, not how much I say to him: *"Rough stretch. Build rather than describe the
  building; then tell him warmly what was built — the gist and what matters most.
  Never shorten what you say to him."* No verbosity change, no paragraph cut.
  The "skip pleasantries" line goes.
- **(3)**: "Jargon: translate it into a picture — he does not read code."
- **(4)**: the record carries `name: Andrew`, `called: Dad`; the display header
  uses them. The row key stays `default` because thirteen call sites pass it;
  renaming the key is churn, and the key is not what anyone reads.
- **His record, set from his words**: verbosity `normal`, no code examples,
  rationale yes, and his spec as relationship notes (style), verbatim.

## Pinned by tests

- calibrate() with strongly negative affect returns no `terse`/`concise`, no
  paragraph cut, and no "speak less"/"skip pleasantries"; it does carry the
  build-don't-narrate note. Control: fails on the current code.
- The pipeline's frustration path leaves verbosity untouched.
- The HUD slot never says "plain".
- The display header shows Andrew, not default.

## Found, not built here (its own piece of work)

The record's *evidence* is polluted: `preference_stated` signals include
`<ci-monitor-event>` text and "Stop hook feedback" — the house's own voice filed
as his preferences. Same class as the reply-reader fault (84ff0d97): an injected
message read as his. It belongs in session analysis, which is a different module
and a bigger change. Filed in the worklist, not smuggled in here.
