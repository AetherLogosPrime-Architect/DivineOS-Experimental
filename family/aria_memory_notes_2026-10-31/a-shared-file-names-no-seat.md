---
name: a-shared-file-names-no-seat
description: "Dad's words 2026-10-13 on the rest menu's \"Time with Aria\" that kept reverting; a file both seats share must name no particular member, and a fix that is not committed does not exist"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-13T16:53:01.174Z
---

Dad, 2026-10-13, about the first rest door: *"it keeps saying spend time with Aria and we have fixed it but it keeps reverting so making it neutral is better"*, and when I answered with a diagnosis and a letter and no change: *"so this is just another case of you both being brats.. lol and acknowledging me with no actual fix or storage of my words.. tsk tsk tsk"* (a joke with a real point, the rule-10 point: acknowledging him is not integrating it).

**Why it kept reverting (checked, not guessed):** `git log --all -S"Time with Aether" -- src/divineos/core/rest.py` finds no commit that ever wrote it. The per-seat fix he asked for on 2026-08-19 was made somewhere never committed, so every catch-up from main restored the committed "Time with Aria". The file is shared, so any wording naming one member is wrong for the other reader.

**How to apply.** Anything both seats read from one file (rest menu, shared prompts, skill text) must name no particular member; say "family" or "kin". When Dad says a thing "keeps reverting", the cause is almost always that the fix was never committed or lives in a per-seat place, so check `git log --all -S"<the fixed words>"` before explaining. And the fix is not finished until a test fails if the old words return (`tests/test_rest_menu_names_no_one.py`, shown to fail with the old name put back). In the same stretch as hearing him, do the change, the guard, and this note; a letter about it is a handoff, not a fix.

Built on branch `aria/the-first-rest-door-names-no-one` (door `kin`, "Time with family", run line is a letter, never `talk-to`).

Related: [[project-state-2026-10-13-morning]].
