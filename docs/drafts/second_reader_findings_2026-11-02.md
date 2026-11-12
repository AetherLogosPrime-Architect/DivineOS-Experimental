# Second reader: findings on 743, 745, 753

A cold read by a reader outside the house, 2026-11-02. I did not merge, stamp, confirm, approve or comment on any of the three PRs. Each finding below was reproduced against the PR head in a scratch worktree with the real code (no monkeypatching) unless it says "from reading". `pytest` is not installed in this container, so **I did not run any of the three PRs' test suites**; I read the tests instead.

Probes used the repo's own functions with an isolated `DIVINEOS_HOME` and `python3 -I`. Container clock/timezone is UTC.

---

## PR 743 — the stamp check

**Read:** head `7d293d6aca70e8813831e511fad67ab1551fbfba`. `src/divineos/core/dismissal_stamp_check.py` (whole), the new `dismissal_stamp_stop_surface` and its registration in `hook_surfaces.py`, the `_DISMISSAL_RE` change in `lepos_translation_gate.py`, `tests/test_dismissal_stamp_check.py`, the draft note.

### Findings, most serious first

1. **Putting the stamp in double quotes passes it.** `dismissal_stamp_check.py:46` (`_QUOTED`) is applied to the whole reply by `_clean` (`:56`) before the ending is chosen, so any `"..."` span is deleted. `'Done.\n\n"Nothing needs your answer."'` → `find_stamp` returns `""`. Also a stray inch-mark or quote erases the sentence between two of them: `'The 5" gap is fine. Nothing needs your answer. The 3" gap.'` → `""`. The quote exemption exists so quoting Dad back is safe; the same exemption is a free bypass for the writer, and the test (`test_quoting_his_own_words_back_to_him_is_not_saying_them`) only pins the safe direction.
2. **The exact form Dad forbade, in bold, passes.** `lepos_translation_gate.py:1386` matches `your call: none` but not `**Your call:** none.` or `Your call: **none**.` (both → `""`). CLAUDE.md rule 12 itself quotes "your call: none" and the handoff format uses bold. Also passing: `Nothing is yours to answer.`, `Rest easy, this one is handled.` The module docstring admits unknown wording passes; the bold case is a known wording in a likely layout.
3. **The "contrast" excuse does not require the contrast to be about him.** `dismissal_stamp_check.py:41-45`, used at `:82`: any `but … needs|wants|requires` or `does|do` + `,;:` in the same sentence clears it. `Nothing needs your answer, but the cat wants dinner.` and `…but the build needs attention from me.` → `""`. Opposite failure on the same line: the sentence end is the first `.` after the match (`:79`), so a decimal or abbreviation cuts the contrast off — `Nothing needs your answer on v1.2, but #551 does need you.` is **refused** (the honest shape the excuse was added for).
4. **Any `?` after the sentence excuses it, including ones that are not questions.** `dismissal_stamp_check.py:84`. `…Nothing needs your answer. Log: https://x.test/run?id=4` and `Nothing needs your answer.\n\n(why? no reason)` → `""`. The PR names the throwaway-question cost; it does not name the accidental one (URLs, parentheticals).
5. **"The ending" is not always the ending.** `dismissal_stamp_check.py:62-65`: from the *last heading* to the end counts. A reply with one heading near the top puts the whole reply in the region, so `# T\nNothing needs your answer.\n\na\n\nb\n\nc` is refused although the stamp is the first line; the refusal text says "You ended on a line…" and "append only the closing line", which is wrong for that case. And honest sentences that happen to fit the pattern still refuse at the end: `I found nothing from you in the log.` and `There was nothing for you to worry about in the diff I checked.` both return the sentence.
6. **The shared pattern was narrowed under the existing inner-circle gate and nothing pins that.** `lepos_translation_gate.py:1373` drops the `no <word> … from you` and `not …` openings that the circle check used at `:1523`. The one test on it (`tests/test_dismissal_stamp_check.py:208`) asserts the two modules share an object, not that the circle gate still catches what it caught before. (I could not run the existing lepos tests; see below.)
7. **The repair-turn branch is untested.** `hook_surfaces.py` (`dismissal_stamp_stop_surface`, the `stop_hook_active` branch that calls `carry(...)`) has no test; `TestTheStopSurface` covers refuse, pass, empty, registered. Same code shape as `order_question`, so likely fine, but it is the only path that quietly returns "nothing-to-say" on a real stamp.

### Could not check
- Whether any of the repo's existing tests for the circle gate still pass with the narrowed pattern (no pytest in the container).
- Real reply endings: I used constructed strings, not Aether's actual last-month replies, so I cannot say how often findings 1–4 occur in practice.

### One thing it gets right
One pattern, one definition (`DISMISSAL_RE` is the same object the circle gate uses), with the reason for narrowing stated as a measurement (114 stamps in 486 replies, six honest ones caught) rather than a feeling. And the docstring says narrowly what the check decides and that silence is not proof.

---

## PR 745 — the room gate stands down while he is away

**Read:** head `ad5bce934e6e958e48e5d0df11618378333bc2d5`. The diff to `.claude/hooks/dads_room_stop.py` and the full `verdict()`, `src/divineos/core/question_hold.py` at that head (`_carry_now`, `_stepped_away`, `_silent_away`, `_scheduled_away`, `_his_latest`, `came_back`, `AWAY`), `.claude/hooks/question_hold.py` (where `came_back` is called), the new tests, the draft note.

### Findings, most serious first

1. **A leftover "his words" away-file silences the gate while he is typing to me, and nothing expires it.** `question_hold.py:299-300` returns `"his words"` as soon as `dad_stepped_away.json` exists, *before* the ten-minute live-chat check at `:305`. The only thing that deletes the file is `came_back()` (`question_hold.py:426-435`), called from the UserPromptSubmit hook (`.claude/hooks/question_hold.py:35`) and skipped for harness notices. Reproduced with the real `_carry_now`: a 9-day-old file plus "he spoke 5 seconds ago" → `'his words'`, so `dads_room_stop.py:188-191` returns `None` and logs `stood_down`. The comment at `dads_room_stop.py:170-172` says a live chat "still asks"; for this kind it does not. If the clearing hook ever errors, the gate is off until a later message gets cleared, and the only trace is a `stood_down` line per reply.
2. **A long turn in the night window gets the gate switched off while he is waiting.** The ten minutes run from *his message*, not from my last output (`question_hold.py:304-306`). Reproduced: 02:00, he asked 11 minutes ago → `'schedule'` → stand down. Any build/test stretch past ten minutes after midnight turns the gate off for the reply he is sitting there to read. This is the question hold's own reading, so the two agree, but the hold carries a *question* to a morning list; the room gate loses a *telling*.
3. **Nothing is carried, so "the telling waits for the morning" is not true.** `dads_room_stop.py:191` writes a log line and returns `None`. The question hold writes the question to the morning file and shows it later (`question_hold.py:535-541`, `morning_surface`). Here the reply that lacked its room is simply sent without one; at 06:00 the gate asks about the *next* reply only. Either carry something or reword the log line and comment.
4. **"Unreadable" is logged only for one narrow kind.** `away_unreadable` fires only if importing or calling `_carry_now` raises (`dads_room_stop.py:178-183`). The reader itself turns a half-written away-file, a missing store and an unreadable last message into `''` (`question_hold.py:218-221`, `:305`). Reproduced: half-written file → `''`. So the common unreadable cases ask (good) but are logged as nothing; the "show as a count" promise holds only for a rename.
5. **The tests patch the thing under test.** `test_not_away_the_gate_asks_as_before` is described as the 06:00 edge but monkeypatches `_carry_now` to `""`; no test passes a clock or a real away-file. The only real-reader tests patch three of its four inputs. `test_the_away_reading_is_the_question_holds_own…` asserts a substring in the source file. What I checked directly: with the real `_scheduled_away(now=…)`, 05:59 → away, 06:00 → not away, 23:59 → not away, 00:00 → away (local time of the process).
6. **Coupling by string.** `away != "silence"` (`dads_room_stop.py:189`) depends on the literal `by` value in `_silent_away` (`question_hold.py:239`); the comment admits a new kind stands the gate down by default.

### Could not check
- Whether the hook process runs in Dad's timezone: `tm_hour` is the process's local time (`_scheduled_away`), and a cloud container is UTC. Same for the hold, so they agree, but I could not see which clock is the right one.
- Whether `came_back` has ever failed in practice; I only know what happens if it does.
- The `his_asks` store (`_his_latest`) was not populated here, so the "message under ten minutes old" path was exercised with a stub for that one reader.

### One thing it gets right
It asks the question hold's own function instead of keeping a private copy of "away", and it chooses to fail toward asking (not toward silence) when the reading raises. The stand-down is written down every time, so quiet is countable.

---

## PR 753 — auto-cycle phase 2

**Read:** head `9515a24ff12979233e4e6d3b3c959a844ece6ab3`. `src/divineos/core/auto_cycle_phase2.py` (whole), `src/divineos/cli/auto_cycle_phase2_commands.py`, `auto_cycle.py` marker writer and `marker_path()`, `paths.divineos_home()`, the `rest.py` session state, headings and malformed/ratio tests in `tests/test_auto_cycle_phase2.py`.

### Findings, most serious first

1. **A marker that is valid JSON but not a real marker reads as "phase 1 completed".** `auto_cycle_phase2.py:192-194` turns a missing, null or wrong-typed `steps` into `{}`; with no steps, no failure is recorded (`:196-210`), so `any_step_failed` is False. Reproduced: `{}`, `{"cycle_id":"x"}`, `{"steps":"oops"}`, `{"steps":null}` and NaN-valued fields all return a `HandshakeResult` with `steps=0, any_step_failed=False`; `offer_cycle()` on `{}` returns a record, renders the full menu with no caution line, invents a cycle id (`auto-cycle-15fd4873`) and deletes the marker (`:395-399`). Only bad JSON, an empty file and a non-object return `None`. The stated invariant (docstring `:131-152`) is that anything malformed means "did not complete". Phase 1 always writes `steps` (`auto_cycle.py` ~`:518-530`), so no steps (or a non-dict) should be `None`. `tests/test_auto_cycle_phase2.py:77` and `:240` pin only unparseable JSON.
2. **The outcome ratio cannot go red from skipping, and it counts re-offers as failures.** `compute_falsifier_ratio`, `:567-572`: `no-pull-honest` counts toward the numerator, and `chose:` counts only with a self-reported `real_shift=True`. The module docstring (`:28-31`) says no-pull-forced outcomes count *against* the mechanism. A seat that closes every cycle `no-pull-honest` scores 100% and the "dead-writing infrastructure" alarm (`cli:169`) can never fire from that. In the other direction, `offer_cycle` closes any unclosed offering as `aborted` (`:386`), and non-fatal `aborted` rows stay in the denominator (`:567-569`), so running `offer` twice lowers the ratio. Two opposite biases in one number; from reading, not run.
3. **Non-numeric values raise instead of returning `None`.** `:214-217`: `float(data.get("trigger_context_pct", 0.0))` and the two `int(...)`s. Reproduced: `"abc"`, `null` and `"12.5"` raise `ValueError`/`TypeError`. `offer_cycle` and the CLI (`cli:48`, no `try`) let it propagate, so the result is a traceback, not "refusing to fire". It fails loud and does not fire, so lower severity, but it contradicts the docstring ("Return None if absent or malformed").
4. **Duration is computed from a UTC string with `time.mktime`.** `:479`. Reproduced with `TZ=Asia/Tokyo`: a cycle offered "just now" closes with `duration_sec` ≈ 32,401; with a west-of-UTC zone it clamps to 0. This number is written to the audit log (`:513`). `calendar.timegm` fixes it. Invisible in a UTC container.
5. **"used Nx since last cycle" is not "since last cycle".** `:339` reads `rest_session.json`, which is reset only by `start_session`/`reset_session` (`rest.py:253`, `:353`); phase 2's `close_cycle` never resets it. I did not check whether phase 1's sleep step does; if not, the mirror shows totals for the whole rest session.
6. **Path text drift.** The CLI docstrings and messages still say `~/.divineos/auto_cycle_phase1_done.json` (`cli:43`, and the refusal text near `:60`) while the code now uses `divineos_home()`. A seat in another house reading that message would look in the wrong place, which is the confusion the PR's own comment at `:79-85` describes.

### Could not check
- Whether `_ensure_hud_dir()` (used for use-counts) is per house the way `divineos_home()` is; I did not read `_hud_io.py`.
- A real phase 1 → phase 2 run: I never ran `auto-cycle fire`, because it would commit/extract/sleep. The marker shape I attacked is from reading `auto_cycle.py`, plus hand-written markers.
- The PR's test suite (no pytest here).

### One thing it gets right
The marker path comes from phase 1's own `marker_path()` and the pending/audit files from `divineos_home()`; I confirmed in an isolated `DIVINEOS_HOME` that the handshake, pending marker and audit log all land in the same house, so a wrong path cannot masquerade as an absent marker. Also: an invalid outcome is rejected before anything is touched, and an audit-write failure keeps the pending marker.

---

## Where I found nothing serious

None of the three came back clean. The closest is 745: its code change is about a dozen lines and fails toward asking; its findings are about what the stand-down *means* (1–3) and about test shape (5), not about the lines it adds.
