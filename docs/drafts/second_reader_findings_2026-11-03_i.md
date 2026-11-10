# Second reader: findings on 758, 759, 760, 761

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on any of the four PRs. Each PR head was extracted with `git archive` into a scratch folder outside the repo, put first on `PYTHONPATH`, and the probes printed `__file__` to prove the head's code was the code loaded. Probes call the PRs' real functions with no monkeypatching. Windows, Python 3.13.11, isolated `DIVINEOS_HOME`. Constructed strings, not real transcripts, so how often any finding happens in practice is unknown.

Summary of counts (serious to minor): 758: 0 / 2 / 3. 759: 1 / 3 / 1. 760: 1 / 2 / 2. 761: 2 / 2 / 2. Severity words: HIGH = the change defeats its own purpose or contradicts a stated rule; MEDIUM = a real hole or a failing test; LOW = edge or wording.

---

## PR 758 - Harness notices are not his words

**Read:** head `11bc42e0797f4ae9912ea27db76db295e4947a79`. Whole diff (`his_message.without_notices`, the one-line call in `hook_surfaces._last_user_text`), the code around the call (`_is_machine_text`, `_MACHINE_START_RE`, `opener_kind`), the new test file.

**Does it do what the title says?** Mostly for the shapes it lists. The title says "strips them all", the body says plainly that it does not. **Duplicate?** No: nothing named `without_notices` exists on main; the only `[SYSTEM NOTIFICATION` on main is a string in `unread_stacking.py`.

**Tests at head:** `test_harness_notices_are_not_his_words.py`, `test_addressed_to_him.py`, `test_his_message.py`: 75 passed. (I did not run the other files the PR lists.)

### Findings, most serious first

1. **MEDIUM. A pair of tags in his own words eats everything between them.** `his_message.py:450-455` (`_NOTICE_BLOCK`) matches an opener anywhere and the first closer after it. Reproduced: `"I typed <system-reminder> in my code, please explain. Also </system-reminder> closes it. Thanks"` -> `'I typed   closes it. Thanks'`. His question ("please explain") is gone, so the check measures a reply against the wrong words. Rare (he would have to quote the tag name and its closer), but the PR's own comment says leaving an unclosed tag alone is "on purpose" so as not to swallow his words; a closed pair of his own is swallowed.
2. **MEDIUM. The banner rule eats his words if they sit in the same paragraph.** `his_message.py:456-459` (`_NOTICE_BANNER`) runs to the next blank line. `"[SYSTEM NOTIFICATION - NOT USER INPUT] done\nplease fix the light"` -> `''`; `"what does [SYSTEM NOTIFICATION mean in the logs?\nI am curious"` -> `'what does'`. If a real notice is ever followed by his words without a blank line, or he mentions the banner, the check stands aside or measures a fragment. Tests only cover the banner followed by a blank line.
3. **LOW. Shapes the body names as unhandled stay unhandled mid-message.** Reproduced: `<agent-message>...</agent-message>` and `<ci-monitor-event>...` after his words are kept as his words. Honest in the body, but the title ("strips them all") reads wider than the code.
4. **LOW. Nested blocks leak.** `"<system-reminder>a<system-reminder>b</system-reminder>LEAK</system-reminder> please..."` -> `'LEAK</system-reminder> please fix the light'`.
5. **LOW. Quadratic on many unclosed tags.** 3,000 repetitions of `<system-reminder>x` took 0.68 s in `without_notices` (50,000-character single unclosed tag and a 50,000-line banner were fast). A Stop hook with a large pasted message would feel it; not a correctness problem.

### Could not check
- Real transcripts: I did not have Aether's actual last-month user turns, so I cannot say how often a notice sits mid-message with his words after it versus before it.
- The `_memo` cache key for `_last_user_text` (read, not exercised) - if it keys on the transcript file's size/mtime the new cleaning needs no invalidation; I did not prove that.

### One thing it gets right
It leaves `_his_part` alone because that function's source is hashed into the words-door index stamp, and says so in the code comment and the body. Editing the shared reader would have forced every index to re-embed; adding one function beside it avoids the cost and the PR names the trade-off.

---

## PR 759 - The stall check lets a stance or a feeling stand without a tool call

**Read:** head `efc8f50ec6032c6cb4147a45062c0376c1eaf4a8`. Whole diff, the whole `src/divineos/core/stall_on_promise.py` at head (`PROMISE_SHAPES`, `_A_FEELING_NOT_A_STEP`, `_without_feelings`, `stated_next_step`), the new test file.

**Does it do what the title says?** For every sentence in its table, yes (I re-ran them). It also lets through real work in the same words, below. **Duplicate?** No: main has the feelings list but no stance list, no `_NO_DEBT`, no lead-in rule.

**Tests at head:** `test_a_stance_or_a_feeling_is_not_an_unkept_promise.py`, `test_stall_on_promise.py`, `test_hold_log.py`: 98 passed, 1 xfailed (the strict xfail for "Let me run the tests." as the body says).

### Findings, most serious first

1. **HIGH. The lead-in excuse skips the whole sentence, so a second step in it is never read.** `stall_on_promise.py:222` `continue`s past the sentence when `_already_said_later` is true, before `_without_feelings` and the promise shapes run. Reproduced (all return `None`, i.e. not held): `"I'll say the word, and push the branch tonight.\n\nThat is the word."`; `"I'll add the fix, and then push it tonight.\n\nThe fix is small."`; `"I'll give you the diff, then merge it.\n\nThe diff is large."`. The pushing and merging are real steps with no tool call. This is the same shape the PR's own feelings code guards against with `_BARE_SECOND_VERB` ("remember this AND push it"), which the lead-in rule bypasses.
2. **MEDIUM. "Fulfilled" is a substring test, so a mention counts as delivery.** `stall_on_promise.py:174`: `lead.group("what").lower() in after.lower()`. Reproduced: `"I'll add the fix, since you asked.\n\nThe prefix is wrong and nothing else is done."` -> `None` ("fix" is inside "prefix"). `"I'll add the summary, since you asked.\n\nThe summary section is not written yet."` -> `None`: the noun reappears in a sentence saying it is NOT done. The body admits "merely reappears" is excused; it does not say a substring inside another word, or a sentence that denies it, also counts.
3. **MEDIUM. Two stance verbs cut real work down to a fragment.** `_A_STANCE_NOT_A_STEP` removes only the matched span and reads what is left. `keep trying`: `"I'll keep trying the push until it lands."` -> `None`; `"I'll keep trying to push the branch."` -> `None`. `make it worth`: `"I'll make it worth the wait by running the whole suite now."` -> `None`. `"I'll keep being on the build until the tests pass."` -> `None`. The body promises the patterns are "anchored on the object so the same verb on real work stays a step"; `keep trying/being/caring/listening` and `make it worth` have no object anchor, only the verb. (`keep listening for CI ... and merge` stayed held only because of the bare second verb.)
4. **MEDIUM. `_NO_DEBT` removes real debts that start with "no" or "nothing".** `stall_on_promise.py:160`. `"I owe Aether nothing less than a straight answer."` -> `None`. The shape it was written for ("I owe no proof") is fine; the same words with a following object are a debt. I could not find a test for this direction.
5. **LOW. Two controls in the body are cheap to read past.** The xfail (`"Let me run the tests."` held by no row) is honest and strict, but it means the "still holds" half of the PR is only tested for phrasings the old table already caught; the new rows have no negative control beyond the six listed ones.

### Could not check
- Real last-month closings: I used constructed sentences. I cannot say how often findings 1-4 occur; 1 and 2 need a reply that makes a lead-in and later mentions its noun, which is a plausible shape for him to see.
- The whole test suite (the push owns it).

### One thing it gets right
It keeps the narrow tool narrow: an explicit list, the object named where it could be, and the miss written into the module docstring and the body ("a stance worded some new way is held until it becomes a row"). The six real sentences are pinned as tests next to five real promises that must still hold, so the change is visible in both directions.

---

## PR 760 - My dreams are a source the memory link searches (read-only)

**Read:** head `53595daf14e0db2e17cb400a1bd327ac0127cd62`. Whole diff, `dream_files.py`, `_load_dreams` and `_find_dreams_root` next to `_load_exploration` in `memory_linkage_retriever.py`, `_gather_paths` in `search_commands.py`, the new test file, the READMEs under `dreams/aether`, `dreams/aria`, `dreams/aletheia`.

**Does it do what the title says?** It adds the source as described. Whether it should is finding 1. **Duplicate?** No dream loader on main.

**Tests at head:** `test_dream_source.py` + `test_memory_link_reconnected.py`: 21 passed, 1 skipped, **5 failed**. Four of the five (`test_the_light_embedder_*`, `test_the_lane_*`) fail identically on main in this environment (no embedding model); the fifth is the PR's own test (finding 2).

### Findings, most serious first

1. **HIGH. It contradicts a rule the dream register states for itself, and Aria's seat is not asked.** `dreams/aria/README.md:43`: *"The dream register doesn't route through the memory-linkage surface - dreams aren't compose-time anchors for drift-catching. They're a different kind of writing."* The PR makes dreams exactly that. The PR says it edited nothing under `dreams/`, so the README is left asserting the opposite of the code. Related: the same README (and Dad's line quoted in all three) says *"dont taint the artifact"* and warns against a dream being "converted back into work"; the loader turns them into compose-time priming. `_load_dreams` reads every seat's folder (174 dream files on main: 98 aether, 76 aria), so Aria's dreams, which are hers, are surfaced into whoever runs the link. A labelled line ("a dream, not a record") answers the "is it fact" worry; it does not answer the stated rule or consent. Nothing in the body mentions the README or asks Aria. This is a decision for Andrew and Aria, not for me, but it is the one thing I would hold the PR on.
2. **MEDIUM. The PR's own test fails on Windows.** `tests/test_dream_source.py:82` asserts `lighthouse.path == "dreams/aether/001_the_lighthouse.md"`; `memory_linkage_retriever.py` builds `path` with `str(md_path.relative_to(root.parent))` (the same as explorations), which gives backslashes on Windows. Reproduced: `'dreams\\aether\\001_the_lighthouse.md' != 'dreams/aether/001_the_lighthouse.md'`. The PR body lists tests it ran but says nothing about a failure here. The code is not wrong; the test pins a separator.
3. **MEDIUM. The "every surfaced dream says so" label is only in the memory-link path.** `divineos find query` can now return dreams (`--corpus dreams`/`all`), but the diff has no label change in `search_commands.py` output; only `compose_block` and `render_payload` add the note. From reading; I did not run `find query` (no embedding model here).
4. **LOW. The file rule is exact on today's corpus.** I ran `dream_paths` on main's `dreams/`: 174 files, no duplicate ids, the three `README.md` files excluded, no nested folders, so a numeric-prefix rule is right today. A dated name like `2026-11-03_x.md` would be silently excluded (regex needs digits then `_`); Aria's README already says numbering is the format, so this is a note, not a bug.
5. **LOW. Cold cost grows by 174 items.** `_ensure_cache` now embeds `dreams/` on every cold load (and `linkage warm` walks it). The body says the whole suite and `test_the_lane_stays_inside_its_budget_at_the_size_of_this_house` were not run here; that test fails on main without a model, so I could not tell whether adding 174 items moves it. From reading.

### Could not check
- The by-meaning ranking with the real embedder (no model here; the PR's own such test skips for the same reason). I do not know what a dream actually scores against an ordinary prompt, so the 0.38 floor and `target_k` 2 are unmeasured.
- The `_load_dreams` result under the real vector cache (`linkage warm` writes it).

### One thing it gets right
One rule for "which files are dreams" in `core/dream_files.py` used by both the memory link and `find index`, and the loader plus `find index` are tested to leave every dream byte-identical and mtime-identical. It does not copy dreams into the knowledge store.

---

## PR 761 - The reflection hold retires a stumble once a reflection has answered it

**Read:** head `b76dfad839afeb4652e298b472bb65382bb7cfaa`. Whole diff: `.claude/hooks/reflection_room_stop.py`, `src/divineos/core/reflection_room.py` (whole, 320 lines), both test files, and `.claude/settings.json` on main for registration.

**Does it do what the title says?** The title describes a change to an existing hold. **There is no existing hold on main.** The PR body says so (the room is carried over from `origin/keepsafe/aria-live-house-2026-10-31`, about 2,150 commits away). Nothing in `src/`, `.claude/hooks` or `.claude/settings.json` on main refers to `reflection_room` or `reflection-note`; the only mentions are in `archive/` and a draft. So the PR re-adds 320 lines of old module and a hook plus a 58-line change on top, under a title that says "retires a stumble". **Duplicate?** No, but it re-introduces code not on main on purpose that the body flags; I cannot tell from the repo whether it was retired deliberately.

**Tests at head:** `test_reflection_hold_retires_answered_stumble.py` + `test_reflection_room.py`: 20 passed, **1 failed** (`test_the_hook_holds_an_unanswered_stumble_and_stays_quiet_once_answered`, finding 2).

### Findings, most serious first

1. **HIGH. The hook is not registered anywhere, so it never runs.** `.claude/settings.json` on main (Stop section, line ~476 onward) lists `dads_room_stop.py`, `stall_on_promise_stop.py`, etc.; there is no `reflection_room_stop.py`, and the PR does not touch `settings.json`. As it stands the change is a hook file plus a library nothing calls. The body says it is "carry-over plus the fix" and does not say it also needs registering; a reviewer reading "the hold" would assume it is live.
2. **HIGH. A note that failed to file retires the stumble.** `reflection_room.py:235-249` (`NOTE_RE`, `_notes`) reads the *tool call* only, not its result, and `unanswered` (`:252-265`) retires on the call. There is no `divineos reflection-note` command on main (the body says so too). Reproduced with the real functions: stumble `work-item-doorman`, then a `divineos reflection-note "[work-item-doorman] fixed by structure: x"` call whose result is `Error: No such command 'reflection-note'.` -> held list is `['command']` only; the original stumble is gone. So the first note that does nothing clears the hold, and the failure is reported as a different stumble.
3. **MEDIUM. Any command that contains the words counts as a note.** `NOTE_RE` is `divineos\s+reflection-note\b(.*)` over the entire Bash string. Reproduced (all retire the stumble): `echo "divineos reflection-note [work-item-doorman]"`; `grep -rn "divineos reflection-note" docs # [work-item-doorman]`; `git commit -m "docs: mention divineos reflection-note" && echo [work-item-doorman]`. A note that is only `"[work-item-doorman]"` with no reason or ending also retires it (body: "does not grade the note"). One note naming two tokens retires both (`[work-item-doorman] [heredoc_escape]` -> held list empty). The "vague note retires nothing" claim holds only for a note with no literal token.
4. **MEDIUM. The PR's own hook test fails on Windows, and the hook has a crash path outside its safety net.** `reflection_room_stop.py:21`: `Path(os.environ.get("REFLECTION_ROOM_MARK", Path.home() / ...))` evaluates `Path.home()` eagerly at import, before the `try/except` in `__main__`. The test runs the hook with an environment of only `REFLECTION_ROOM_MARK` and `PATH` (`tests/test_reflection_hold_retires_answered_stumble.py:102`); on Windows that raises `RuntimeError: Could not determine home directory.` (exit 1, empty stdout), so the assertion on "work-item-doorman" in stdout fails. Reproduced. The docstring says the hook "fails toward him ... never a wall"; an exit-1 at import is not the loud-mark path it describes.
5. **LOW. The docstring and the code disagree on which occurrence counts.** `reflection_room.py:255-258` says "a note came after the stumble first appeared"; the code (`s.last_at < at`) requires it to come after the *last* occurrence, which is the behaviour the tests pin and the right one. Wording only.
6. **LOW. A note that is in the same assistant record as the failing call.** Reproduced: a parallel tool_use pair (failing call, then the note) both at record index 1, error at 2 -> the stumble is *not* retired (`last_at` 2 > note index 1). That is conservative (it holds), but the order of records, not of intent, decides.

### Could not check
- The real `divineos reflection-note` command or the real filing record: neither exists in the repo I read. If it lives on the keepsafe branch, the way a note is recognised may differ.
- A run of the hook under the real harness; I ran it as a subprocess on constructed transcripts only. `stop_hook_active` and the cross-turn re-hold the body mentions are not exercised.
- Whether the keepsafe branch's version of these three files is byte-identical to what the PR added (I did not diff against that ref).

### One thing it gets right
Position is checked, not just presence: a note retires a stumble only if it comes after the stumble's *last* occurrence, and a recurrence after the note holds again; a note filed before the stumble retires nothing. The tests pin that, and the PR body is straight about the mismatch with the brief (room not on main, no `reflection-note` command).

---

## Where I found nothing serious

None of the four came back clean. Closest to clean is **758**: no HIGH, nothing wrong with the lines it adds beyond its own regexes' reach, and its tests pass here. The two I would hold hardest are **760** (it overrides a rule the dream folders state for themselves) and **761** (the hook is not wired in, and a failed note counts as answered).
