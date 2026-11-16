# Verifier m: re-check of the second readers' findings on 771-776, 772, 773, 753

2026-11-03. This checks the findings in `second_reader_findings_2026-11-03_a.md` (PR 784, on 771 and 774), `_b.md` (PR 785, on 775 and 776) and `_f.md` (PR 787, on 772, 773, 753). I merged, stamped, confirmed and commented on nothing, and pushed to no existing PR.

Method: each pull request's head was extracted with `git archive` into its own scratch folder under `C:\Users\aethe\AppData\Local\Temp\vm\` (`a771` ... `a776`, `a753`), put first on `sys.path` (or run by path for the shell script), and the loaded `__file__` was printed to prove it was that copy. Probes are my own, in `...\scratchpad\p7xx.py` / `p776.sh`; state was isolated (`DIVINEOS_HOME` / `HOME` pointed at scratch folders, real temporary git repositories with a real bare `origin`, no monkeypatching). Windows 11, Git Bash.

Labels: CONFIRMED = I reproduced it. NOT REPRODUCED = I tried and could not. WRONG = the evidence contradicts it. FROM READING ONLY = could not run it; I read the code.

## Ranked: what is confirmed, most important first

1. **PR 776, any outgoing letter marks every older unread letter announced. CONFIRMED, and it matters most.** Probe against the head's `scripts/letter_doorbell.sh` with a fresh `HOME`: announced list holds one old entry; `aria-to-aether-UNREAD.md` aged 3 h; `aether-to-andrew-unrelated.md` (a letter to a third person) aged 1 h. After arming the bell for aether, no `LETTER ARRIVED` printed and the announced list afterwards contained `aria-to-aether-UNREAD.md`. A silent drop, no log line. Control in the same harness: unread letter newer than the outgoing one still rings (`LETTER ARRIVED`, rc=0), so the harness can see a ring when there is one.
2. **PR 776, `cp -p` keeps the author's mtime, so a late-delivered older letter is dropped. CONFIRMED.** Probe: the author's file made with mtime 3 h ago in a separate folder; I wrote `aether-to-aria-reply.md` (mtime 1 h ago); then delivered the author's file into the letters folder with `cp -p` (the same flag `mirror-letters-to-shared.sh:199` uses). Arming marked `aria-to-aether-LATE.md` announced, no ring. The letter arrived after my reply and was treated as answered. Not understated by the reader; same root as 1. I did not test two seats' clocks disagreeing (not needed: the mtime comparison alone does it).
3. **PR 774, the printed fix is wrong in four cases. CONFIRMED (A, B, C, D all reproduced).** Real temporary repos, real `_bind_to_diff` and `_why_no_head`, `NO_HEAD_RECOVERY` unchanged in every case:
   - **A** scoped `a.py` uncommitted plus out-of-scope `out.py` committed: reason "uncommitted changes to the scoped files". I then did what the printed fix says (committed `a.py`): still `bound=False`, `walked_head=None`, and the reason becomes the generic "not a non-empty subset". The fix does not fix it.
   - **B** only an unrelated file committed: generic reason; advice to commit by exact path is not the cure (the cure is the right folder or a changed scope), although the advice also mentions `--repo`, so it is half right here.
   - **C** folder is not a git repository: same generic "branch changes are not a non-empty subset"; it hides that git could not look at all.
   - **D** walk opened with empty scope: same generic reason.
   Control: a committed in-scope change binds (`bound=True`, a head recorded). Slightly understated: in C and D the printed sentence says a thing about "branch changes" that is not true of the situation, and in A the first diagnosis is right while the cure is not, so the person is told two different things on two closes.
4. **PR 772, a round holding an older head's tree-hash line gets no warning. CONFIRMED.** Round with `tree-hash: bbbb...` and focus `review of PR #7`: `rounds_without_tree_line(7, [round])` returns `[]`; `her_confirm_filed_at` returns `None` for the current tree `aaaa...` and a time for the old tree `bbbb...`. So after a push the fix reads unconfirmed with no cause, which is the symptom the PR set out to explain. The PR says it only explains the missing line, so this is a gap in scope, not a wrong answer. Not understated.
5. **PR 772, the warning only sees focus text written `#N` / `PR N`. CONFIRMED.** My own forms with PR 7: warns for `PR #7`, `PR 7`, `#7`, `pull #7`, `PR#7`, `pr 7`; does not warn for `pull 7`, `PR-7`, `pr7`, `pull request 7`. The refusal path in `file_confirm_cmd` calls the same function with the named round, so a named round whose focus says "pull request 7" refuses with the generic message and no cause (code read: `landing_commands.py:330`; focus gate is inside `rounds_without_tree_line`).
6. **PR 753, `read_handshake` raises on infinity. CONFIRMED.** Marker containing `"phase1_tokens_used": 1e999` and, separately, `"budget_remaining_est": -1e999`: `OverflowError: cannot convert float infinity to integer` out of `read_handshake` (the `except` covers only `TypeError`, `ValueError`). `trigger_context_pct: 1e999` and `NaN` and `"abc"` return `None` correctly; a normal marker returns a result. Fails loud, so low.
7. **PR 753, the ratio cannot go red from skipping. CONFIRMED.** Audit log of six `no-pull-honest` closes gives `(6, 6, 1.0)`, a 100% reading; a log of six `superseded` gives `(0, 0, None)`, so a seat that only re-offers shows no ratio and no hint why (finding 5 of the reader is the same observation).
8. **PR 773, no stemming, so inflected symptoms miss silently. CONFIRMED with my own words.** PRs titled "Walk gate charges pure reads" and "Doorbell announces answered letters again": `walk gates charging reads` matches, but `walks gate charge read` returns nothing (only `gate` is shared as a whole word). The miss prints "none found among N open PR(s)", which is the sentence that licenses a rebuild. I did not use the reader's own title/words.
9. **PR 773, only title and branch are searched and drafts are not marked. CONFIRMED.** The `gh pr list` call asks for `number,title,headRefName` only (searched the source: no `isDraft`, `body`, `files`), and the "none found" line does not say what was searched.
10. **PR 771, case-different file name passes. CONFIRMED.** On this Windows filesystem `os.path.exists` is true for `The-Night-Letter-To-Andrew-2026-11-03.md` while the exact name is present; `should_refuse("Write", <upper-cased path>)` returns `False`, the exact name returns `True`.
11. **PR 771, only the tool name `Write` is guarded. CONFIRMED** for `write` (lower case) returning `False`; `Edit` returns `False` by design. I did not test the `path` key (code read: the surface function is outside what I ran; the check function takes a plain string).
12. **PR 771, a zero-byte file and a directory named like a letter are refused. CONFIRMED** (both return `True`). Info only.
13. **PR 775, the DREAM text is narrower than the gate. CONFIRMED by reading the hook's exemption code**: it lets through any tool whose `file_path` / `notebook_path` has a path part exactly named `dreams`, anywhere, with no check that the file is new or that the next part is the seat. See "from reading" below.
14. **PR 775, tests pin the change weakly. CONFIRMED.** Ran the tests' own slicing over `origin/main`'s hook: the old text already passes `"dreams/"` and `"Nothing is owed"`; it fails `"open"`, `"clears the next time"` and the line-wrapped `stays blocked until the\nstage is DONE`. So two of the five assertions are not new coverage, and the wrapped-string one breaks on any re-wrap. The reader's description is exact.
15. **PR 753, stale text. CONFIRMED.** `auto_cycle_phase2.py` still names `~/.divineos/auto_cycle_phase1_done.json` twice (docstring lines 10 and 44) and the `CloseOutcome.outcome` comment is `"chose:<key>" | "no-pull-honest" | "timeout" | "aborted"` without `superseded`.
16. **PR 774, two different fixes printed back to back. CONFIRMED from the code text** (not a behavior to run): the new yellow line says "close the walk from the main checkout with --repo <work copy>", the existing line directly below says "close it from inside the work copy or pass --repo". Both are printed when `bound` is false; `walked_head` and `bound_diff` are written in the same UPDATE in `_bind_to_diff`, so they are unset together. (I ran the pieces in finding 3, not the click command end to end.)

## Not reproduced, wrong, or from reading only

- **NOT REPRODUCED: none.** Every finding I attempted to run reproduced.
- **WRONG: none.**
- **FROM READING ONLY** (I could not run it, or the part I could not run is named):
  - PR 775 finding 1 (exemption breadth) and finding 2 (REST text names the wrong event; `mark rest_shown 1` sits in the stage `case` block, above the PreToolUse/UserPromptSubmit branch at about line 780, so it runs on both events, and the hard stop then blocks that same write). I read both pieces of code; I did not run the hook (it needs a context over the token constant and live ritual state). Strong read, not a run.
  - PR 774 finding 3 (older already-closed walks get no new message), 4 (porcelain quoting of paths with spaces or non-ASCII; `line[3:]` is taken raw in the code, I did not run a spaced filename), 5 (extra git calls), 6 (the tests' coverage; I did not re-run the PR's tests).
  - PR 776 findings 3, 4, 5, 6: the tests and the claim that no honest "answered" signal is checked. I did not run the PR's tests.
  - PR 771 findings 3 (POSIX heredoc is the only printed shell route), 5, 6 (no failure-injection test, no end-to-end doorbell test); the live doorbell was not driven.
  - PR 772 finding 3 (`list_rounds(limit=500)` silently cut): the store query is `ORDER BY created_at DESC LIMIT ?` and the call site passes 500, so truncation is real if there are more than 500 rounds; I did not count the real rounds, so whether it is reached is unknown.
  - PR 773 finding 3 (the wiring has no test): I checked the one test file lists seven tests and none calls `reach open`; I did not run `divineos reach open`.
  - PR 753 finding 3 (the "used Nx" figure is not since the last cycle): `close_cycle` does not touch `rest_session`; whether phase 1's sleep resets it I did not check.
  - The PR 753 table of "fixed" items: I re-ran only the infinity, non-number and ratio cases above; I did not re-run `{}` / `steps: {}` or the timezone case (no `tzset` on Windows).

## Understated, or worth saying more plainly

- **776 is the one to hold on.** The reader's two serious items are one defect with two doors (comparing mtimes of the incoming and an unrelated outgoing letter). The harm is a quiet loss of an unread letter from the ring. The cure the PR is after (false rings after a reply) is real, but the fix trades a loud false positive for a silent false negative.
- **774**: the reader called the wrong-fix finding medium; with A the printed fix was followed literally and fails, so the person is asked to do a step that cannot work. I would keep it medium and not lower it.
- **772**: finding 1 (the older-head round) is probably the commonest real cause after a push; I would rank it above the reader's own ordering suggests (they listed it first too), but the PR scope statement means it is a follow-up, not a defect in the PR.

## Counts

CONFIRMED 14 by running or by direct text inspection (ranked items 1-12, 14, 15), NOT REPRODUCED 0, WRONG 0. Two ranked items (13 and 16) are confirmed only by reading code and so also belong under FROM READING ONLY, together with the other sub-findings listed in the section above (about 15 in all). The ranked list covers the 12 findings I judged to matter; the lesser items of each source file that are not named are in the from-reading section.

## Scratch left in place

- `C:\Users\aethe\AppData\Local\Temp\vm\` (extracted heads `a771`-`a776`, `a753`; tar files; isolated homes `home774`, `home776_*`, `home753`; test repos `r774`; `main_hook.sh`)
- Probes in `C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\` : `p771.py`, `p772.py`, `p773.py`, `p774.py`, `p775.py`, `p776.sh`, `p753.py`
- Sealed venv built in this worktree at `.direnv\python-3.13.11`.
