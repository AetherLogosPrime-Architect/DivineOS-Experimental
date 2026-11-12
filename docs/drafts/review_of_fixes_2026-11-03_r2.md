# Cold review of four repair drafts, round 2 (2026-11-03)

A cold read of the four small repairs stacked on earlier pull requests: #802 (for #771), #807 (for #772),
#809 (for #773), #812 (for #774). Each was read in full (diff and body), its head and its base head were
extracted with `git archive` into scratch folders outside the repo, and put on PYTHONPATH with
`divineos.__file__` printed to prove which tree loaded. The new tests were run on both heads. Then my own
probes. Scratch folders are left in place: `C:\Users\aethe\AppData\Local\Temp\r2\` (`<pr>_base`, `<pr>_fix`,
plus `sp ace\` and `DIVINE OS\` copies for the path-with-a-space check) and the probe scripts
`C:\Users\aethe\AppData\Local\Temp\r2_probe*.py`.

Heads read: #802 `d9fb2ac7b` on base `51aad11bc`; #807 `ac28c93e1` on `5bd1fca2a`; #809 `b21d01c4a` on
`46fe8bb03`; #812 `70c73dd0d` on `4a1aa9c49`.

## Summary

| Repair | High | Medium | Low | Verdict |
|---|---|---|---|---|
| #802 night-letter door | 0 | 0 | 1 | Does what it says. One neighbouring dodge still open. |
| #807 landing clerk warning | 0 | 1 | 3 | Works; answers half of #772; some false positives; one false sentence in its draft note. |
| #809 reach open stemming | 0 | 0 | 2 | Clean. |
| #812 walk close reasons | 0 | 1 | 3 | Four stated cases fixed; a fifth common case still gets the wrong reason. |

## Claims that held (so they need not be re-checked)

- New tests fail on the base head and pass on the fix head, run by me both ways: #802 3 of 3 fail on base,
  16 pass on fix; #807 6 fail on base (4 naming forms, 2 tree-given cases, the latter by TypeError on the
  new third argument), 26 pass on fix; #809 2 of 3 fail on base (the guard passes there, as stated), 10 pass
  on fix; #812 5 of 5 fail on base, 9 pass on fix.
- #802: `tests/test_every_exit_passes_every_gate.py` plus its own file: 431 passed on the fix head.
- #812: the walk test files (`tests/test_*walk*.py`, 157 tests) gave 156 passed, 1 skipped, 1 failed on the fix head. The one failure is
  `test_council_walks_surface.py::test_real_repo_surfaces_filed_walk`, which reads the real repository's
  walk files; my extracted archive has no `.git`, so I did not chase it and did not run it on the base. I
  do not claim it is unrelated beyond "the diff does not touch that code".

## The two items the fixers could not attribute

- **#807 `tests/test_landing_briefing_row.py::test_it_reaches_the_rendered_text_not_only_the_list`.** Not
  reproduced. Alone it passes on the base head (18 passed) and on the fix head (18 passed). The four
  `tests/test_landing*.py` files together: 99 passed on the fix head. `-k landing` over the whole `tests/`
  on the fix head: 106 passed, 3 skipped (the same numbers the fixer gave), with 4 collection errors that
  are all in `test_doorbell_passes_engagement_gates.py` and come from my archive having no `.git`
  (`ROOT` is None), not from the repair. So the fixer's one error is not shown to come from the repair and
  does not reproduce for me; it may have been state in their checkout. It does not matter for merging.
  REPRODUCED (as a non-failure).
- **#812 `tests/test_one_walk_before_the_push.py::test_the_target_folder_is_read_from_the_call_not_the_hook`.**
  Not reproduced on either head. The whole file (24 tests) passes on the base head and on the fix head in
  a path with a space (`...\r2\sp ace\812_*`), and that one test passes on the base head under a folder
  literally named `DIVINE OS`. The test in the base head already quotes the path (its own comment says Aria
  found it passing only where the path had no space), so the fixer's failure points at a checkout whose
  copy of the test or the temp folder differs. The repair does not touch `target_dir` or this test.
  I could not run it inside the fixer's checkout. REPRODUCED as passing on base.

## #802 Night-letter door: case-insensitive name and a `path` key

**Low 1. The same dodge family still passes on Windows. REPRODUCED.** With the night letter existing, a
Write to `the-night-letter-to-andrew-2026-11-03.md.` (trailing dot), `...md ` (trailing space), or
`...md::$DATA` all report `exists: True` yet `should_refuse` is False, because the name regex ends at `\.md$`
and these do not match it. On Windows those names open the same file. `core/night_letter_overwrite_check.py:26`.
The body says the door "can no longer be dodged by letter case or by the tool's other spelling", which is true
as worded, and its "cannot see" list names symlinks and redirects but not these three. They are cheap to
close (strip trailing dots and spaces, drop an `::` suffix before matching).

Note (FROM READING, not verified): the lower-case `write` and `path` handling in
`hook_surfaces.py:2377-2380` only matters if the hook registration lets those calls reach the surface. The
`.claude/settings.json` matchers I saw are case-sensitive names like `Edit|Write`. I did not trace the
registration for this surface, so I cannot say the new branches are reachable in practice.

Probed and fine: `WRITE` is guarded; `Write ` (trailing space), `MultiEdit`, `NotebookEdit` and `None` are not
(correctly or by design: only Write replaces a whole file); empty `file_path` with a `path` falls through to
`path`; a differently named `file_path` beats a night-letter `path` (file_path wins, matching the real tool).

Gets right: the smallest possible change, three tests that genuinely fail before, and a body that names what it
did not test (case-sensitive filesystems) instead of hiding it.

## #807 Landing clerk warning: one PR-naming grammar and an optional tree

**Medium 1. Only half of the finding is closed, in the place people look least. FROM READING.** The older-head
sentence is only produced where a tree is passed, which is `file-confirm` (`cli/landing_commands.py:330`). The
board listing (`divineos landing`, same file, the `rounds_without_tree_line(int(pr["number"]), all_rounds)` call
near line 193) still passes no tree, so a round whose line names an older head stays silent there, which is
where the cost was first paid (a night lost to it). The body says so plainly under "could not check" and calls
it a design call, so this is a disclosed gap, ranked medium because the finding it answers ("older-head round
silent") is still true on the main surface.

**Low 1. New false positives on rounds that do not name the PR. REPRODUCED.** With PR number 5, a focus of
`pull 5 commits from main into the fix` and `Aletheia audit; pr 5 files of the walk` both count as naming PR 5,
as does `issue#7 followup` for PR 7 and `pr 7th` for PR 7. The regex is
`(?:#|\b(?:PR|pull(?:\s+request)?)[\s\-#:]*)N(?!\d)` (`core/landing_homework.py:82`): "pull" plus any run of
separators plus the number is enough, with nothing requiring the digits to be the end of a token. The cost is
a wrong "has no tree-hash line" line under an unconfirmed PR, not a wrong clearance; low.

**Low 2. "Every way of naming a PR" is not every way. REPRODUCED.** Silent for the PR: `pull-request 7`,
`pull-requests 7`, `PR No. 7`, `pr/7`, and the GitHub URL `https://github.com/x/y/pull/7`. The URL form is
the one GitHub itself writes. `landing_homework.py:82`.

**Low 3. The draft note in this very PR says something untrue. FROM READING.**
`docs/drafts/the_warning_reads_the_matchers_grammar_draft_2026-11-03.md` ends its second paragraph with "Also
covers, in the same walk, three small fixes to other pull requests' findings (the night letter door, the open-PR
listing in `reach open`, the walked-head line of `walk close`); each is its own small commit on its own
branch." None of those is in this PR; they are #802, #809 and #812. It would be read later as a description of
what this change did.

Probed and fine: a longer number is not the PR (`pull 500`, `PR-501` do not name 50), an older-head round plus
a current-head line in one round's notes gives no warning (the line for this head is found), and the
older-head sentence is only produced when the line holds 40 hex characters and the tree is given.

Gets right: the older-head case is explained in its own sentence instead of reusing "has no tree-hash line",
which would have been false there, and a test pins that the two sentences do not mix.

## #809 `reach open`: stemming and a "titles and branch names only" line

No high or medium findings. The repair is clean for what it claims.

**Low 1. The stemmer is uneven on exactly the short, common words. REPRODUCED.** `uses`/`used`/`using` give
three different stems (`use`, `used`, `using`: the length guard skips `-ed` and `-ing` on short words);
`running`/`runs` give `runn` and `run`; `policies`/`policy` do not join (disclosed). `making`/`makes`/`make`,
`gates`/`gate`, `fixes`/`fixing`, `blocks`/`blocked`, `caching`/`cached`/`caches`, `tests`/`testing` all join.
`core/reach_open_prs.py:27-36`. No false join turned up in 28 word pairs I tried (`speed`/`spec`,
`string`/`strong`, `during`/`dura`, `bleed`/`bled` stay apart); `status` becomes `statu` on both sides, harmless.

**Low 2. "among N open PR(s)" still overstates when there are more than 100. FROM READING, count checked.**
`gh_open_prs` asks for `--limit 100` (line ~58) and the line prints `len(prs)`, so with more than 100 open PRs
it would say "among 100" as if that were all. Today there are 69 open, so it is not yet true. The new
parenthesis is accurate about titles and branch names.

Real-data check the fixer did not run: I took the live `gh pr list` (69 open PRs) and compared the old and new
matcher on eight symptom phrases. The new one added matches only for "the walk gate checking endings" (#765,
#798) and "tests failing" (#805); it lost none. I read the added ones as the intended kind of match.

Gets right: it ran the guard test ("garden stamps" must not match "Gate stamp ending check") that would catch the
usual way a crude stemmer goes wrong.

## #812 `walk close`: true reason and one fix

**Medium 1. A common case still gets the wrong reason. REPRODUCED.** A scoped file that is uncommitted and sits
in a directory git has not seen yet: `git status --porcelain` reports the directory (`?? newdir/`), the code
compares that with the scope entry `newdir/a.py`, finds no overlap, and `walk close` says "there is no commit
ahead of the base branch in that folder" with the commit-by-exact-path fix. Same result for a scoped file whose
name has a space (git quotes it in porcelain). The true cause is the uncommitted scoped file, which the control
case (`a.py` in the top directory) names correctly. `core/council_walk.py:836-841` (the `dirty` set). The line was
inherited from the base, but this PR's whole claim is that each reason is the condition that stopped the binding,
and the fifth case does not meet it. Fix: `git status --porcelain -uall -z`, or ask git which scoped paths differ.

**Low 1. The amend refusal still gives one generic fix. REPRODUCED.** For an empty-scope walk (and an out-of-scope
walk) `walk amend` says "commit the change by exact path first, then close a new walk..." (`council_walk.py:914-919`).
That is the fix the PR removed from `walk close` for exactly those cases, because it does not apply. The amend
path does not call `_why_no_head`.

**Low 2. "In the order the binding step checks things" is not what the code does. REPRODUCED.** `_bind_to_diff`
tests git state first and the scope last (`council_walk.py:754-759`); `_why_no_head` tests scope first. For an empty
scope and a folder that is not a git repository, the reason is "this walk has no scope" and the fix is "open a new
walk with --scope", and a second walk closed in the same folder then fails on "not a git repository". Both are
true; the first one named is not the first thing that stopped the binding.

**Low 3. A neighbouring line now contradicts the new wording. FROM READING.** `core/build_flow.py:1349` still tells the
reader to "Close the walk from inside the work copy (walk close --repo <work copy>)" for a stale walk, while this PR
now says in the amend refusal that "a closed walk cannot be closed again". A stale walk is a closed one.

Not tested by anyone (the body says so for the first two, and I did not provoke them either): the "git could not
list this branch's changes" branch, the "could not read the head or diff" branch, and the empty-scope message run
end to end through a real `walk open --scope` (I confirmed `--scope` exists on `walk open`, `cli/council_walk_commands.py:52`).

Probed and fine: a non-existent `--repo` folder reports "is not a git repository" with the `--repo` fix; five
committed out-of-scope files print the first three and "and more", and add "and commit the scoped files by exact
path" when a scoped file is also uncommitted; only one of "To fix it" / "To bind it" appears in a close.

Gets right: the tests use real temporary git repositories rather than mocks, and each fix line now follows from
its own reason instead of a shared sentence that contradicted a second one.

## What I could not check

- Whether the `write` / `path` variants in #802 are ever delivered to that surface by the hooks registration.
- The fixer's two unattributed failures inside their own checkouts (see above): only shown not to reproduce on
  extracted heads.
- #807's board listing against the live round store; I tested the function, not `divineos landing` end to end.
- #809 against `gh` pagination beyond 100 PRs; #812's two branches that need git to fail.
- My extracted archives have no `.git`, so tests that read the repository root fail to collect there for that
  reason alone; I ran only the named test files and walk/landing groups, not the full suite.
