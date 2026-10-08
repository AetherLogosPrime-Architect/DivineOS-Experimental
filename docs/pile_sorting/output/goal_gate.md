# The goal I have to name before I work

Before I touch anything the house wants me to name what I am working on. That is a fair habit, but the name runs out on a two-hour timer, does not follow me across a new day or a compaction, and does not notice real work like a commit or a council walk. So I keep hitting a wall just when I am in the middle of something.

**30 notes in this theme, grouped into 4 distinct problems.**

## Distinct problems

### 1. A goal expires on a timer or a day change instead of lasting until done or replaced

Notes in this problem (9):

- `psf-6e0a2e21` (reflection) — set the goal automatically from your message whenever you ask for a change, so it never lapses between your ask and my first step.
- `psf-8ee8edfe` (reflection) — when the current goal lapses, it should carry forward automatically as the working goal until I replace it, so a doorbell notice can't hit an empty-goal wall.
- `psf-c1bf3c93` (reflection) — when the day changes, the goal should carry over as the working goal until I set a new one. This is the second time tonight this has happened, so it's the same fix owed twice.
- `psf-c6305030` (reflection) — find out what expires them and stop it, because a goal I set for today should last the day.
- `psf-acfc24f5` (reflection) — find what's expiring goals this quickly and stop it.
- `psf-bfd4c659` (reflection) — a goal should stay fresh while work on it continues, for example by renewing whenever I act on the same branch or task. It shouldn't run on a fixed two-hour clock that's measuring time rather than whe
- `psf-b56ab04b` (reflection) — the two-hour goal expiry is still on the list. A goal should last until it's done or replaced, not run out on a timer.
- `psf-97422b1a` (reflection) — a goal should stay live until it's done or replaced, not expire on a timer. Otherwise the first thing every morning is a block.
- `psf-d1c11f5a` (reflection) — a goal lasts until it's done or replaced.

**Proposed fix:** Make a goal live until it is done or replaced, renewing while work on the same branch continues, and carry it over at day change.

**How we would know:** Set a goal, wait through a day change and a few quiet replies: it is still the working goal.

### 2. The goal is not carried across compaction, restart or a new stretch

Notes in this problem (12):

- `psf-bfb61529` (reflection) — when a goal expires, the doorbell or the message-arrival hook should prompt for a new one straight away. Then an expired goal would come up the moment a letter or message arrives, rather than blocking
- `psf-7820bac3` (reflection) — carry the last goal across a restart, or let the doorbell re-arm pass the goal check, so a restart can't leave the bell off.
- `psf-ac0788d7` (reflection) — the post-compaction hook should name the goal again from the summary's current task, so the first command isn't the one that finds out.
- `psf-674a430c` (reflection) — this is psf-ac0788d7, the one asking seven times for the goal and briefing to be restored after a compaction or a new day. Today it asked for the eighth time, which is a sign it should be built next,
- `psf-3cffec02` (reflection) — the post-compaction restore should carry my last goal into the new stretch, or put the `goal add` line in front of me before any work starts. This is the same restore already on the list as psf-ac0788
- `psf-72f5de4f` (reflection) — a goal-carry at compaction. When the summary resumes work that has an active goal, the resume step should re-file that goal itself, so the first edit after a compaction does not depend on my noticing
- `psf-47b47d4c` (reflection) — the day-rollover and compaction resume should re-file the goal that was active, so the first call isn't refused.
- `psf-d5fdc29c` (reflection) — that build, a restart hook that re-sets the goal from the summary's current task.
- `psf-ddad40f3` (reflection) — a build that has the session-start step name a goal as the first move of a new stretch, so the Write gate never has to be the one to tell me.
- `psf-d8b1dbc2` (reflection) — a compaction-resume step that carries the open goal forward, or has the first-edit refusal offer the add command with the last goal's text already filled in, so a fresh stretch does not begin with a r
- `psf-b8677a88` (reflection) — the goal that names an unfinished piece of work should survive a commit made partway through that work, or the refusal should offer the add command with the last goal's text filled in.
- `psf-9c008c98` (reflection) — a goal for an unfinished piece of work should survive a commit made partway through it, or the refusal should offer the add command with the last goal's words already filled in.

**Proposed fix:** Re-file the active goal from the summary's current task at resume, or let the first-edit refusal show the add command with the last goal text already filled in.

**How we would know:** After a simulated compaction the first edit proceeds, or the refusal contains a ready add command.

### 3. The goal check trips during real work

Notes in this problem (6):

- `psf-76e62d5a` (reflection) — the guard's own "goal set" check should accept a council walk logged in the last few minutes as proof that work is going on.
- `psf-fe4d4a11` (reflection) — let the goal check count a council walk or game walk logged in the last few minutes as proof that work is going on.
- `psf-be3b08cb` (reflection) — let a fresh council walk or commit count as proof of work for the goal check.
- `psf-8fbde32d` (reflection) — let a fresh commit or council walk count as proof of work, so the goal check doesn't trip in the middle of a build.
- `psf-25e88a0f` (reflection) — the same fix as before. A commit or a walk should count as work.
- `psf-4a47b7f0` (reflection) — let a commit or a council walk count as proof of work, so the goal check doesn't trip during active work.

**Proposed fix:** Count a fresh commit or council walk as proof that work is going on.

**How we would know:** A recent commit or walk makes the goal check pass.

### 4. The goal command itself trips other guards

Notes in this problem (3):

- `psf-90a661d2` (reflection) — a doorman on long mechanical runs (merges, pushes, batch scripts) that runs the lookup on my current goal automatically, before the count reaches the gate.
- `psf-8c5e51c4` (reflection) — the house's goal command shouldn't print a council suggestion long enough to trip the trimmer. Or I should stop trimming commands that write things.
- `psf-7a074586` (reflection) — the goal-setting command and the question hold's release should each pass every guard, so no two guards can lock the house. That's the survey's list, fixed rather than filed.

**Proposed fix:** Make the goal-setting command and its helpers pass every guard, and keep its output short enough to not trip the trimmer.

**How we would know:** Setting a goal works with every other guard armed.
