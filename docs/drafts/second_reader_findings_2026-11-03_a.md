# Second reader: findings on 771 and 774

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on either PR. Findings marked REPRODUCED were run against the PR head with the real code (isolated `DIVINEOS_HOME`, real temporary git repositories, no monkeypatching); "from reading" means I did not run it. Windows 11, local time zone. I ran only `tests/test_walk_close_says_what_it_recorded.py` (4 passed on 774); I did not run 771's tests or the wider suite (the push's job).

---

## PR 771: refuse a Write over an existing shared night letter

**Read:** head `51aad11bcfa7e35c2293f2b12d495ec0bb882b8a`. Whole diff: `night_letter_overwrite_check.py`, `night_letter_overwrite_surface` and its registration in `hook_surfaces.py`, the test file, the count comment in `test_every_exit_passes_every_gate.py`, the ARCHITECTURE line, the draft. I also read `.claude/settings.json` to confirm the doorbell matcher includes `Write` (it does, line 304), and listed the real letters folder to confirm file names (`the-night-letter-to-andrew-2026-11-03.md` etc.).

### Findings, most serious first

1. **Case-different file name passes (LOW-MEDIUM).** REPRODUCED. `_NIGHT_LETTER` (`night_letter_overwrite_check.py:27`) is case-sensitive, but on Windows (where both seats run) `The-Night-Letter-To-Andrew-2026-11-03.md` is the same file. With the real file present, `should_refuse("Write", ...)` returned `False` for the upper-cased name and `True` for the exact name. The door is meant to guard the file, not one spelling of it; a Write typed with a different case replaces the letter silently. Unlikely by accident, but this is exactly the "looks routine" failure the door exists for.
2. **Only the tool name `Write` is guarded (LOW, from reading).** `surface` returns "nothing-to-say" for any other `tool_name`. REPRODUCED that lower-case `write` and a payload keyed `path` instead of `file_path` both return `nothing-to-say`. The harness today sends `Write` / `file_path`, so this is only a coupling to exact spelling; the draft names other tools (`>`, `cp`) as out of reach, but not this one.
3. **The only printed shell way in is POSIX heredoc (LOW, from reading).** `refusal_message` offers `cat >> file <<'EOF'`. One seat works through PowerShell as well as Git Bash; PowerShell has neither heredoc nor `cat >>` with that shape (`Add-Content` would). The Edit route is always available, so the refusal is not a dead end, but it names one shell's idiom as "the" other way.
4. **A directory or empty file named like a letter is refused (INFO).** REPRODUCED: a directory named `the-night-letter-to-andrew-2026-12-01.md` and a zero-byte letter both return `True` (refuse). Refusing a zero-byte file is arguably right (nothing to lose, but creation-by-Write over it is blocked and the message says it "already exists"); harmless, noted so nobody is surprised.
5. **The fail-soft path says "unguarded" correctly but nothing makes it countable (INFO, from reading).** A raising check returns `state="could-not-run"` with the error text; good. The tests do not exercise that branch (no test injects a failure into `should_refuse`). The same shape as earlier readers' notes on the other surfaces.
6. **No end-to-end test that the router turns `refused=True` into a denied tool call (INFO, from reading).** `test_the_door_is_actually_registered_on_the_doorbell` checks registration, and the surface tests check the outcome object; nothing drives the doorbell with a Write payload and observes a block. I assume other surfaces share this gap.

### Could not check
- That a real Write is actually blocked by the live doorbell (that needs the hook running in a seat; I only ran the judgment and the surface function).
- A race between the existence check and the write (the draft already says it cannot see this).
- Symlinks/aliases (the draft says it cannot see these; not re-tested).

### One thing it gets right
It is narrow and honest about it: only the exact two-seat file name, creation stays a plain Write, and the module docstring lists in plain words what it cannot see. Chosen the right altitude too: the refusal names two concrete ways in, so the cheap path (just Write) and the right path (append) are both a short step.

**Count: 0 high, 0 medium, 3 low (1, 2, 3), 3 info (4, 5, 6).**

---

## PR 774: `walk close` prints the walked head it recorded

**Read:** head `4a1aa9c492499ae328f13e57d074de94ea113e3c`. Whole diff: `close_walk` additions, `NO_HEAD_RECOVERY`, `_walked_head_of`, `_why_no_head`, the new lines in `close_cmd`, the changed `amend_walk` refusal, the test file, the draft. Read around it in the repo: `_bind_to_diff` (`council_walk.py:738-769`), the pre-existing "NOT bound" message in `close_cmd` (`council_walk_commands.py:228-237`), `push_choke._git`. Ran the PR's own 4 tests: 4 passed.

### Findings, most serious first

1. **The "why" and the fix are wrong for most of the ways a close ends without a head (MEDIUM).** REPRODUCED with real temporary repos. `walked_head` is set only when `_bind_to_diff` binds. When it does not, `_why_no_head` has three answers and `NO_HEAD_RECOVERY` ("commit the change by exact path first, then close from the main checkout with --repo <work copy>") is printed for all of them:
   - **A.** a scoped file uncommitted *and* an out-of-scope file already committed → reason "uncommitted changes to the scoped files". Committing the scoped file would NOT bind, because the committed diff still contains the out-of-scope file. Printed fix is incomplete; the next close fails again with the same words available only after the second try.
   - **B.** only an unrelated change committed (the "closed from the wrong folder" case the `_bind_to_diff` docstring is about) → generic "not a non-empty subset" and the advice to commit by exact path, which is not the fix (point `--repo` at the right folder, or fix the scope).
   - **C.** `--repo` is not a git repository at all → the same generic "that folder's branch changes are not a non-empty subset", which hides that git could not look. Advice again "commit".
   - **D.** the walk was opened with an empty scope → same generic reason; the fix is to reopen the walk with a scope.
   Only "no commit ahead of base" (tested) and the plain uncommitted case (tested) get advice that fits. The PR says it changes no rule; true, but it adds a diagnosis that is confidently specific and sometimes not the cause.
2. **Two different fixes are printed back to back (MEDIUM-LOW).** REPRODUCED by reading the CLI at the PR head: the new yellow line says "commit by exact path, then close from the main checkout with --repo <work copy>", and the existing line directly after it (`council_walk_commands.py:231-236`, "NOT bound to any branch changes ... close it from inside the work copy or pass --repo") says to close from *inside the work copy*. One tells the reader to close from the main checkout, the other from inside the work copy, about the same fact. `walked_head` is None exactly when `bound` is False (both set in `_bind_to_diff`), so the new line is the existing one plus a head. The PR's own claim that the amend refusal and the close line share one constant so they "cannot drift" is true of those two and not of the third message beside them.
3. **`walk amend will refuse` is stated unconditionally (LOW, from reading).** The new line says it, but the amend refusal depends on `_walked_head_of` being empty, which is what this line just reported, so it is true; but an older walk closed before this change has the same `None` and prints nothing new (not reprinted on re-close; `close_walk` raises "already closed"). So the one person who hit the original bug (Aether and Aria, closed earlier) gets the improved message only on the next close, not on an amend of their existing walk, other than via the refusal text (which does carry it).
4. **Dirty-file detection reads raw `status --porcelain` lines (LOW, from reading).** `_why_no_head` takes `line[3:]` and compares with `_scope_of`. Porcelain quotes paths with spaces or non-ASCII characters (`"dir/my file.py"`), so such a scoped file would be missed and the reason would fall to the generic third answer. It also compares repo-root-relative porcelain paths with a scope that may have been written differently (`./a.py`, backslashes on Windows); I did not test those spellings.
5. **Extra git calls on the failure path (INFO).** `_why_no_head` runs `status` and `changed_files` after `_bind_to_diff` already ran its own; two repeated looks at a repo that could have changed in between (a file committed between the two reads gives a reason that disagrees with the bind result). Rare.
6. **Tests cover two of the four reasons I found (INFO).** The four tests (all pass) cover committed, uncommitted, no commit ahead, and the amend refusal text. None covers the generic third answer, a non-git folder, or an out-of-scope committed file, which is where finding 1 lives.

### Could not check
- Whether real closes by Aether and Aria in the last day fell into the cases in finding 1 (I used constructed repositories, not their walks).
- Windows quoting of unusual file names (finding 4): not run.

### One thing it gets right
It turns a silent success-shaped output into a one-line fact about the one thing the caller needs (the head, or that there is none), changes no rule about what counts as a valid close, and says so in the PR. The recovery for the commonest case (closed before committing) is stated at the moment it matters, in the same sentence the amend refusal now reuses.

**Count: 0 high, 1 medium (1), 1 medium-low (2), 2 low (3, 4), 2 info (5, 6).**

---

## Summary

| PR | high | medium | low | info |
|---|---|---|---|---|
| 771 | 0 | 0 | 3 | 3 |
| 774 | 0 | 2 | 2 | 2 |
