# The warden that raises my stumbles

After a stumble, a warden raises it so I reflect on it and say what structure would prevent it. It is a good idea, and it is the source of most of this pile. But it also raises things that were not stumbles, keeps raising ones already answered, names the stumble from the wrong text, and is leaning toward the negative.

**29 notes in this theme, grouped into 7 distinct problems.**

## Distinct problems

### 1. Reflection leans toward finding fault

Notes in this problem (1):

- `psf-b23ddb82` (correction) — Andrew 2026-08-15: 'i think the issue is in the reflection itself.. its seems to always be toward the negative.. finding something wrong with something.. when it should be more balanced, not just find

**Proposed fix:** Balance the prompt to also notice what worked.

**How we would know:** Reflections include a what-worked line.

### 2. The room names the stumble from the wrong text

Notes in this problem (2):

- `psf-26cf2b41` (reflection) — Aria's room should take the name from "BLOCKED by …" before the hook's file name. I've sent her the exact case.
- `psf-23307c11` (reflection) — for a traceback, the room should name the stumble after the error on its last line, not after its "Exit code" heading. I'll add this to the note I sent Aria.

**Proposed fix:** Name the stumble from the 'BLOCKED by' phrase or the last line of a traceback.

**How we would know:** The stumble title comes from the right line.

### 3. An already-answered stumble keeps being raised

Notes in this problem (3):

- `psf-d9588951` (reflection) — once a stumble has been answered in any REFLECTION since Dad's last message, the room should count it as answered, so the same stumble isn't raised again after every notice. I'm sending Aria this case
- `psf-8e044687` (reflection) — Aria's rule that any earlier answer counts is not taking effect on my side, and I'm sending her this record so she can see why.
- `psf-90364821` (reflection) — the warden should only raise a stumble that hasn't already been reflected on. Otherwise the same list keeps coming back, and each reply fills up with repeats instead of anything new.

**Proposed fix:** Count a stumble answered by any reflection since Dad's last message.

**How we would know:** A stumble answered once is not raised again.

### 4. Things that are not stumbles are counted

Notes in this problem (5):

- `psf-c5427c2c` (reflection) — the reflection room should treat an exit caused only by an early-closed pipe, where the command's own output still shows success, as a non-stumble, the same way it already skips a bare "Exit code 1".
- `psf-34105f24` (reflection) — the room should not count an exit caused only by cutting output short as a stumble when the output itself shows success.
- `psf-d8668fff` (reflection) — the warden should tell a test failing from a hook refusing, so a red test isn't reported as a gate turning me away.
- `psf-412c42fe` (reflection) — the warden should count a hook as refusing only when the output says `hook error`, not when a hook's file name appears in printed text such as a diff or a file list.
- `psf-4fe8e29b` (reflection) — make an exit-code-only stumble carry the command's first words so its name is not just a number.

**Proposed fix:** Skip early-closed pipes whose output shows success, tell a failing test from a hook refusal, count a hook as refusing only when the output says hook error.

**How we would know:** These are not raised.

### 5. Demand a root-cause line on every stumble

Notes in this problem (1):

- `psf-24b5a030` (reflection) — the reflection room asks for a "root cause:" line on every stumble, and rejects a "fixed by structure:" line that doesn't touch that cause. This goes to Aria, since the room is hers, through the flow.

**Proposed fix:** Ask for 'root cause:' and reject a 'fixed by structure:' line that does not touch it.

**How we would know:** A fix line unrelated to the cause is rejected.

### 6. The obligation detector mixes a promise with a description

Notes in this problem (3):

- `psf-f800c87d` (reflection) — the obligations detector should tell a promise ("I will never…") apart from a description that contains "never" ("a tool I had never run"), with tests built on these five real notes.
- `psf-fb80e060` (reflection) — the check-pending-obligations detector must separate real promises from descriptions that contain those words, with tests built from the five notes it misread tonight.
- `psf-2675ae35` (reflection) — a check that re-opens an obligation if the hook it cited is removed or changed.

**Proposed fix:** Tell 'I will never...' from a description containing 'never', with tests on the real notes it misread; reopen an obligation when the hook it cites changes.

**How we would know:** The five misread notes classify correctly.

### 7. Stumbles whose reflection says nothing is owed

Notes in this problem (14):

- `psf-86b95a3d` (reflection) — nothing, it's the plain error message doing its job. It failed loudly and I made the folder.
- `psf-4fdf6609` (reflection) — nothing.
- `psf-f41a6dd4` (reflection) — nothing.** "Access denied" is Windows doing its job, and administrator rights belong to you, not me.
- `psf-6064838d` (reflection) — nothing, since each failed loudly and was worked around on the spot.
- `psf-56d05994` (reflection) — nothing, it's the same absence-check-on-its-own-line lesson from earlier. Folded into the new command: it reports a missing piece as a finding, not a crash.
- `psf-c6250e0f` (reflection) — nothing, beyond the time limit on hook-launched checks already named above, which would stop orphans forming at all.
- `psf-a03daf66` (reflection) — nothing new. This is the same lesson as earlier tonight with my memory notes, and the gate caught it both times, so the structure is holding even where I'm not.
- `psf-8405e994` (reflection) — nothing new; this is the gate working as designed.
- `psf-6b2b0243` (reflection) — nothing new. This is a door that already exists doing its job.
- `psf-4d520714` (reflection) — nothing new, but I now file justifications as their own command.
- `psf-e65643cf` (reflection) — nothing further here. This one worked as designed, and the cost was one extra search.
- `psf-50f5b127` (reflection) — nothing further, it cost one retry.
- `psf-6cd200f6` (reflection) — nothing further.
- `psf-999992d9` (reflection) — nothing further. The search cost one turn and showed that no existing tool already tracks how well a memory assistant helps, which is itself worth knowing.

**Proposed fix:** Check whether the warden should have raised them; if not, stop raising that shape.

**How we would know:** Replay shows these are not raised.
