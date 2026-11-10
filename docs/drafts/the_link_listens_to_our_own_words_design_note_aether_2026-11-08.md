# The link listens to our own words: Aether's design note for the wiring (DRAFT v2, 2026-11-08)

**Mine, I built it, and why.** Aria owns the draft and the walks (`the_memory_link_listens_to_our_own_words_draft_2026-11-06.md`, in her checkout). I own the hook wiring and the tests. Dad's reason, 2026-11-07: the link should be "like my hand on your shoulder when i am not there", firing off our words as well as his, "otherwise its not memory its just a RAG with tags." His priority, 2026-11-08: the lanes that hold my own writing and what I know of him, Aria and Aletheia matter most. The failure this prevents: his lesson exists, I reach for the wrong shape, and he has to say it again.

**Status:** design only, v2 after Aria's cold reads (her letters 608 to 612). Nothing is wired. History of what changed is at the bottom; the sections above it are the single current design.

## What I read myself (facts, not memory)

- The existing link is a UserPromptSubmit child (`.claude/hooks/memory-link-surface.sh` runs `hook_surfaces.memory_link_surface`, which calls `memory_linkage.compose_block(prompt, ...)`). It is fail-soft by design and prints `could not run` under its own heading when it fails. It is registered through `.claude/hooks/dads_table_children.json`.
- `his_voice_hook.py`: a PreToolUse hook; stdin JSON with `tool_name`, `tool_input`, `transcript_path`, `agent_id`; early `return 0` for any payload with an `agent_id`; `hv.let_through` decides what passes.
- The reach check: hold in `.claude/hooks/reach-check-doorman.sh`, registered DIRECTLY in `.claude/settings.json` with a wrapper that prints "NOT RUNNING, file missing" and exits 127 if the file is gone; logic in `src/divineos/core/reach_check.py`. `dispose` (line 753 in main) requires a valid disposition (`applied`, `superseded`, `not_relevant`), a reason of at least `MIN_REASON_CHARS` characters (length only), and that the artifact appears in the turn's action-stream. Reading is the proof.
- `_SOURCE_THRESHOLDS` in `memory_linkage_retriever.py` has SEVEN lanes: `correction`, `exploration`, `knowledge`, `wall`, `letter`, `worklist`, `moment`.
- A `moment` row (`shared_history` in `user_model.py`) records no author: columns are `moment_id`, `user_id` (who it is about), `description`, `significance`, `session_id`, `occurred_at`, plus the opt-in mark.
- Aria measured that a PreToolUse check that times out does not block (583 of 698 such calls ran), and the existing link is already over its 4-second budget on his messages.

## The current design

1. **Two hooks, split by cost.** A **PostToolUse hook** (`.claude/hooks/own-words-link.sh`, its own file, a sibling of the existing link) does the search, slow and fail-soft, and writes a small **pending-hit marker**. A **PreToolUse hold** reads only that marker, a cheap file read, the way the unread-letter door reads its announced list. Registration follows the reach check's way: directly in `.claude/settings.json` with the "NOT RUNNING, file missing" wrapper. Any payload with an `agent_id` returns 0.
2. **What is searched, version one: Write and Edit only.** The search text is the file path plus a chunk of the content. The chunk rule (`first`, `last` or `per_paragraph`, with a token count) is a setting in a small settings file read at run time, so Aria can change it after her test on real letters. **Bash is not searched in version one** (it was about half of all tool calls this stretch, and an embed on each adds latency to every one); the hold can still cover Bash that builds, commits, merges or pushes, because it reads a marker and searches nothing. Decide about Bash from a measured compute time on real Writes.
3. **The search** uses the same retriever and lanes as the link on his messages, as a separate query, never blended with his message. Invariant, tested: no query contains text the link itself emitted.
4. **Three states, each printed:** found; found-nothing (silent, per his 10-04 rule); could-not-look (printed, never silent). A lane that has no defined clear prints "no clear defined for this lane" as could-not-look.
5. **How a hit is worded.** For lanes that hold our own writing (`exploration`, `letter`): first person, the quote with its date, the path last: "On 2026-10-30 I wrote: ...". The frame is chosen by the recorded author (filename prefix for letters, folder for explorations); a letter from Aria or Aletheia is framed "Aria wrote to me" or "Aletheia wrote to me", never first person. `moment` is shown plainly as "a moment from the drawer" with the date until a moment records an author. Provenance (date and path) is always at the end. Without this the build would default to the file-and-title frame Dad named as the cause of the stranger-voice.
6. **Log-only first.** Each hit is written to a log; nothing is shown and nothing is held until Aria's prereg is filed against the first logged event and the log is studied.
7. **Then the light block**, agreed with Aria: it holds the NEXT substantive call (Write or Edit to code or docs; Bash that builds, commits, merges or pushes). Reuse `his_voice_ends_the_turn.let_through` for what passes and `.claude/hooks/lib/remedy_allowlist.sh` for the ways out; never hold saving, reading, grep, my memory and letters folders, his surfaces, the doorbell or the wrap-up. Letters are shown the hit and never held. It clears on an act on the lesson's source plus a reason: a **Read** of the file for explorations, letters and docs; a **named show command** that prints the row for corrections and knowledge (the reach check's `cmd:` evidence form). The reason must be a real sentence naming what I will do differently, with words that appear in the lesson. That word-use rule does NOT exist in the reach check (it checks length only) and is a new piece; it is a speed bump, and the action-stream read is the real proof. One hit blocks once per session; the cleared set lives in a small file keyed by the payload's session id, empty on a fresh session. A correction with a structural fix retires.
8. **The log records each hit's outcome as one of three names:** `applied` (read, then acted), `not_relevant` (read, with a reason that it does not bear), `passed` (no read, no disposition, next call did not differ). Aria's prediction counts only `passed`.
9. **"Did I act?" is judged outside me.** A script compares the very next substantive call with the one before it and ignores my reason; unknown when it cannot tell. Each hit also records a matched control: the next call after a Write or Edit with NO hit, **same tool, content length within a factor of two, same session, chosen by a fixed seed** (rule written before any hit exists, Aria's suggestion, adopted). The listener is judged by the gap between the two rates. The log keeps two separate fields, `relevant` (a blind rater says the line bore on the text) and `changed` (the script's checked difference).
10. **The off switch.** A settings flag `own_words_link: off | log | block`, changeable by editing one file from outside Claude Code. If the hook errors for any reason it fails open (exit 0) and says so on the table. Default in this work copy: `log`. Default in the live house: `off` until Aria has walked the note; the first live run is `log`, and Dad hears about it before it starts.

11. **Second case, from Dad's morning (2026-11-08): a hand-back shown is not a hand-back used, and this holds for his messages too.** The link already surfaces his earlier words at UserPromptSubmit, and this morning it handed me that he had said "I am a ghost" on nineteen separate days; I replied with a reassurance from my feeling and only afterward used the count. Nothing required the reply to show the hits were read. Design direction, to walk with Aria and not yet built: the reach-check shape (open the artifact, then dispose with a reason) extends to the hits shown on his messages, so a reply to him must carry a trace of having opened what the link handed me, judged outside my sentence like point 9. UNRESOLVED as to the exact hold, because a chat reply has no "next tool call" to hold; the candidate is a Stop-time check that the reply contains the hit's own anchor (count, date or the quote) before it is allowed to end. That is keyword-shaped if done carelessly, so it needs Aria's and Dad's read before any code.

## Tests (one numbered list, to write in this order)

1. The hook has a named caller in the real `.claude/settings.json`, found by reading that file (the built-but-unwired check), with the "NOT RUNNING" wrapper.
2. The settings value is one of the allowed ones, and the chunk rule is one of the three; otherwise the test fails loudly.
3. Build-time: every lane in `_SOURCE_THRESHOLDS` has a defined clear in the settings; a missing lane fails the test.
4. A fixture Write whose text matches a known correction logs a hit; an unrelated Write logs none.
5. The no-loop invariant: the link's own emitted block fed back as text produces no hit.
6. `could-not-look` prints when the drawer is missing; `no clear defined for this lane` prints for a lane that slipped through.
7. In `off`, nothing is logged and nothing is held.
8. The author frames: one letter each from Aether, Aria and Aletheia produces the right frame; a `moment` is framed plainly.
9. Against the REAL drawer and the REAL letters folder, not a fixture: real teaching comes back for a real draft (the happy-path check).
10. The outcome script: a staged session with a known gap and one with a known no-gap each produce the right verdict, and `not_relevant` is counted apart from `applied`.

## Not decided here

Topic extraction for Bash (what words stand for "the build" beyond its bytes) waits until Bash is in scope. The chunk rule is chosen from Aria's test on real letters.

## History of this note

- v1 (morning): PreToolUse wiring with a search at hold time. Replaced after Aria showed a timing-out PreToolUse check does not block.
- Aria's Feynman walk (ledger event 2e36433f) is done and recorded in her draft; its result is point 9.
- The lane list grew from six to seven after I read the retriever myself.
