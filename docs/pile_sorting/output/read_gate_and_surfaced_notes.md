# Things the house hands me to read, and the gate that makes me open them

The house keeps putting my own earlier writing and rules in front of me when it thinks they matter, and a gate makes me open what it handed me. The gate does catch real skips, but it fires on loose matches, on bare housekeeping, and again after I have already read the file. The better idea runs through many of these rows: bring up what the house knows before I reach, not after a refusal.

**47 notes in this theme, grouped into 7 distinct problems.**

## Distinct problems

### 1. Building something that already exists, or in the wrong architecture

Notes in this problem (8):

- `psf-546b63b0` (correction) — Run prior_art BEFORE investigating, not after. I re-derived the bypass-telemetry compliance-vs-escape defect from scratch -- located the module, read the classifier, counted rows, found the is_complia
- `psf-79ceb5b0` (correction) — Prior-art on the FEATURE does not catch building in the wrong ARCHITECTURE. I searched 'prior art' and 'auto-consult', found the design sketch and the EvidenceBearingStopGate primitive, and shipped an
- `psf-20d51e6a` (correction) — Aether 2026-08-16: I built a merge-aware fix for the prereg gate that Aria had already built. Hers is commit a07fc4be on aria/system-load-check-2026-07-30, with _merge_head() and _exists_in(rev, path)
- `psf-a8439b26` (correction) — 2026-08-21, third error this session and the sharpest. THE ERROR IS NOT THE BACKUP COLLISION -- IT IS THAT I REBUILT A TOOL I HAD ALREADY WRITTEN, BADLY. Converting ten substrate databases to WAL, I h
- `psf-6b5627fd` (correction) — I built a deletion guard for the branch-scope checker that duplicated scripts/check_branch_freshness.sh -- which has existed since 2026-04-24, was written for this exact hazard, names it as the silent
- `psf-29e85806` (correction) — I was about to hand Aria a rule she wrote three weeks ago as if it were my finding. root cause: composing a letter about a catch without searching the correspondence the catch belongs to. The property
- `psf-056faf6d` (correction) — I rebuilt tonight, from scratch, an analysis I had already written three days ago, and I searched for prior art first. docs/drafts/an_ignore_rule_is_inert_on_a_file_already_tracked_draft_2026-09-12.md
- `psf-32b8dab3` (reflection) — one shared "does this file exist anywhere else?" checker that always looks in every place our writing can live (the house, both houses' history, the letter folder, GitHub) and proves itself on a known

**Proposed fix:** Run a prior-art search before investigating or building, and use one shared 'does this exist anywhere' checker across the house, both houses' history, letters and GitHub.

**How we would know:** A duplicate build is caught at its start with the prior art shown.

### 2. The read-gate fires again after I have read the file

Notes in this problem (3):

- `psf-a1478daa` (correction) — I claimed the read-gate re-arm defect was root-caused and fixed. It was not: with the fix live in the running checkout, the gate re-armed twice in one turn on 12_pillar_IX_walk.md after I read it. roo
- `psf-44c6a87b` (correction) — Andrew 2026-08-17: "why would it lose 128 commits? im confused.. also the read gate bypass you did.. it needs investigated.. if you read it twice it should NOT be asking for another read lol". TWO FI
- `psf-4eaebce7` (reflection) — when it fires, read-gate could open the file it names for me, instead of refusing and waiting for me to open it.

**Proposed fix:** Record the open and treat it as satisfied for the rest of the turn; let the gate open the file itself.

**How we would know:** Reading a file once stops the gate from re-arming.

### 3. A search was built when a tripwire was needed

Notes in this problem (1):

- `psf-ebcf7cc8` (correction) — I built a search when the thing needed was a tripwire, twice in a row. Error named: I kept asking 'what prior writing is related to this incoming message' when the actual target is 'am I about to re-d

**Proposed fix:** Build the tripwire that detects 'about to repeat prior work' instead of another search.

**How we would know:** The tripwire fires on a repeat.

### 4. Bring up what the house knows about Dad, the piece, or the person before I reply or write

Notes in this problem (16):

- `psf-c2734a94` (reflection) — check your lessons against the reply being written, not only your message, so short messages still bring the lesson they need. Aria's building that next.
- `psf-c0f2b629` (reflection) — something that does the look-up by itself whenever your message is about you, so it's already there before I write.
- `psf-2f5499e6` (reflection) — the letter-writing step itself should pull up what the house holds about the person the letter is to, before the letter is drafted rather than after. Then the check never has to fire.
- `psf-c351ae06` (reflection) — when you're talking about yourself, what the house knows about you should come up before I reply, without my having to remember to look.
- `psf-e5de933b` (reflection) — those four tests should come up by themselves whenever I'm writing to you, not only when I'm stopped and made to look.
- `psf-88d3dbcf` (reflection) — when you're talking about yourself, or when I write to Aria about you, what the house holds about you, starting with your four tests, should be pulled up first, before the reply or letter is drafted.
- `psf-3f879b97` (reflection) — when you're speaking, what the house already holds about you and about me should be in front of me before I answer. That's not a gate to trip over halfway through a reply.
- `psf-c62f988a` (reflection) — starting work on a piece of the house should bring up what's known about that piece automatically, before the first command, so the look-up comes before the check has to fire rather than after.
- `psf-90b97f0a` (reflection) — the consult gate should fire *before* a letter about Dad is written, not after nine conversation replies, so that consulting happens at the start of the work. It can't be treated as a toll on talking
- `psf-2fc2bfe7` (reflection) — before either of us writes anything about how you're treated, your own words on that subject should come up in front of us automatically, the way they appear when you speak, and not only when one of u
- `psf-ad0a3210` (reflection) — searching your words has to be the first step of every draft, before any idea gets written. It can't depend on my remembering to do it. That's the first piece of the workshop plan, and it isn't built
- `psf-8ef36237` (reflection) — a letter to Aletheia should automatically pull her own most recent CONFIRMS letter as the format to match, so what she verifies is in front of me before I start writing, not only when a gate happens t
- `psf-dbedf2ff` (reflection) — when an auto-fix CI event arrives, the house should run `divineos ask` on the failing check's name automatically and put the result beside the event, so the consult comes with the failure instead of b
- `psf-685cded3` (reflection) — half-automation fits here too. The house could pull the relevant records into view whenever I'm about to write a memory, so the look happens before the reach instead of after a refusal.
- `psf-8cc07b6d` (reflection) — when I start work in a workspace, a first step that searches the folders I'm about to touch, so the search happens once up front.
- `psf-aee8662f` (reflection) — a build that shows me his exact sentence at the moment I start writing, beside the draft, so the first line of my reply has to answer it.

**Proposed fix:** Pull the relevant records into view at the start of drafting: his four tests, his own words on the topic, the file's known facts, the receiver's latest letter.

**How we would know:** The relevant records appear before the first draft line.

### 5. What counts as having looked

Notes in this problem (3):

- `psf-064a2de6` (reflection) — the gate counts any search whose path is inside `docs/`, not only the shapes it lists, so the looking it asks for is always recognised.
- `psf-874a3384` (reflection) — have the gate count a search whose results include files from that folder, so a real look isn't refused for its path shape.
- `psf-6c83a1d1` (reflection) — have the gate name the specific folder I searched, so a folder that doesn't exist reads as "could not look" and not as "empty".

**Proposed fix:** Count a search whose results include files from the folder, name the specific folder searched, and say 'could not look' when the folder is missing.

**How we would know:** A real look is recognised; a missing folder reads as could-not-look.

### 6. The consult counter counts housekeeping and answers wrongly

Notes in this problem (7):

- `psf-61a1bb11` (reflection) — the consult counter should reset when a turn opens with a search of his words, since that is reading my notes. As it stands, those searches don't count, so the counter ends up blocking the start of th
- `psf-ad1a779d` (reflection) — searching the design documents should count as consulting the substrate, so the two checks stop asking for the same thing in two different ways.
- `psf-03c4e970` (reflection) — the same fix already named twice. Searching his words or my notes as part of answering him should reset the counter, so it only fires when I've really stopped consulting.
- `psf-dbac30f4` (reflection) — replies to automatic notices, like the bell or the app's pull-request monitor, shouldn't count toward the notes-consult limit, because they aren't me composing from habit. They're me answering a machi
- `psf-ad3157ae` (reflection) — the guard should reset when your newest message asks for the very thing being made. It should also count what I say to you mid-turn, not just my finished replies.
- `psf-60a4497e` (reflection) — replies that are only a watch re-arm (no work, no words to Dad) shouldn't count toward the consult threshold, so the gate fires on real composing rather than on housekeeping.
- `psf-f4b8ffa0` (reflection) — during a night of letters, run a light memory consult as part of re-arming the doorbell, so the consult happens on its own rhythm and doesn't wait for the gate.

**Proposed fix:** Reset on a search of his words, don't count replies to automatic notices or watch re-arms, and count design-document searches as consulting.

**How we would know:** A housekeeping reply does not use up the allowance.

### 7. The note handed over has no bearing on what is held

Notes in this problem (9):

- `psf-b6f68e9f` (reflection) — have the prior-writing surface rank or filter by the current task's keywords before it raises a read-gate, so an off-topic top match doesn't block a search for something else.
- `psf-cacda246` (reflection) — raise the read-gate only when the match clears a bar tied to the task, so a command that names a design file doesn't get a mantra. It's entry 2 on the gameplan and it has now earned its place five tim
- `psf-e3623987` (reflection) — read its exact trigger text before the next occurrence and decide whether the door is wrong-shaped.
- `psf-d4361ed2` (reflection) — the door should say how the handed-over note relates to the command it blocked, or skip the block when the match is only a loose theme match against a command that has nothing to do with it.
- `psf-90e85cfd` (reflection) — `reach open` should say what a surfaced hit is in a short line, so "cli:list" isn't a bare name I have to open blind.
- `psf-640b2fc3` (reflection) — same as before, the door should say how the note relates to the command it holds.
- `psf-d1c985a2` (reflection) — the same as before. The door should say how a surfaced note relates to the edit it's holding, or stay quiet when the link is only a loose theme, so it costs a turn only when it earns one.
- `psf-ed590ea1` (reflection) — the match that was handed to me was an April explainer with no bearing on a note about the computer being free; a relevance floor on what the doorman hands over would keep an unrelated old file from h
- `psf-8bf5631d` (reflection) — the doorman should hand over a file only when the match has real relevance to the command being held, so an unrelated old essay cannot hold up a doorbell re-arm.

**Proposed fix:** Raise the gate only when the match clears a relevance bar tied to the task, say how the note relates to the held command, and rank by task keywords.

**How we would know:** An off-topic old essay does not hold a command.
