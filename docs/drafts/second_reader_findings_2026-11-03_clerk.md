# Second reader: findings on 772, 773, 753 (current head)

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on any of the three PRs, and changed nothing in them. Each finding below was reproduced against the PR head in a scratch worktree with the real code (no monkeypatching) unless it says "from reading". I did not run any of the three PRs' test suites (the container has no way to run the suite here and the house's own hook says the push does that), so **I read the tests instead of running them**. Probes used the repo's own functions with an isolated `DIVINEOS_HOME` and `python3 -I`. The open-PR list used for 773 is the 30 newest drafts (one page); I did not read the rest. Container clock/timezone is UTC.

---

## PR 772 — the landing clerk says when a round has no tree-hash line

**Read:** head `5bd1fca2a49601097950f87932dbf48c86209818` (two commits, after Aria's own cold-read update). `src/divineos/core/landing_homework.py` (`TREE_LINE_PREFIX`, `her_confirm_filed_at`, `_TREE_LINE`, `rounds_without_tree_line`, `round_step`), the two call sites in `src/divineos/cli/landing_commands.py` (`:159` list, `:184-186`, `:330`), `audit_commands.py` around `:594` and `:1195-1271` for the other readers of the same line, the PR body.

I ran `her_confirm_filed_at` and `rounds_without_tree_line` side by side on fourteen note forms. **On form, they agree on every case I tried**: exact line (both fine); no line, two spaces, no space, `Tree-Hash:`, upper-case hex, a 12-character short hash, `tree hash:` with a space, and a line that sits in the focus instead of the notes (matcher refuses, warning fires). The one place they differ on the notes is the intended one: a line for a different tree (a head pushed since) makes the matcher refuse while the warning stays quiet, because the line exists.

### Findings, most serious first

1. **The warning is silent for the round forms a human actually writes the PR number in, so the "cost a night" case can still be silent.** `landing_homework.py:88` accepts only `#772` or `PR 772` (case-insensitive). Reproduced with a round whose notes have no line: `pull request 772`, `pull/772`, `PR-772`, `PR772`, `(772)` and a list such as `PRs 771 and 772` / `PRs #771, 772` all return no warning (only the first PR of a list written with `#` is found). `PR #772`, `#772,` and `pr 772` do warn. The PR body admits "a hand-made round that never names the PR is not reported"; it does not say that a round that does name it, in ordinary words, is also missed. The matcher itself does not care what the focus says, so the warning's reach is narrower than the failure it explains.
2. **`landing file-confirm --round <id>` applies the same PR-naming filter to a round the operator named by hand.** `landing_commands.py:330` passes `[audit_round]` through `rounds_without_tree_line(pr, ...)`, which re-checks that the focus names this PR (`landing_homework.py:93`). The operator has just said "this round, this PR", so the check is not needed, and when it fails the refusal (`:332-336`, text at `:333`) goes out with no explanation of the real cause. From reading plus the pure function: focus `audit of the clerk`, notes empty → `[]`.
3. **The message says "has no tree-hash line" for rounds that have one, in the place the house's own tool puts it.** `audit rebind` (cosmetic rebind, `audit_commands.py:1268-1271`) writes `tree-hash: <tree>` into the **focus**, and the clerk reads the notes only. The warning then says "has no tree-hash line" and "file a new round with the designed first call", which is untrue about the text (the line is there, in the wrong field) and so sends the reader looking for the wrong fix. The matcher/warning agreement on *whether* it fails is right; the sentence about *why* is not. (The rebind round's focus does not name a PR number, so the PR-naming filter also makes the warning silent for a plain rebind round; the same cause as finding 1.)
4. **A stale round next to a good one prints a warning that says to file a new round.** `landing_commands.py:184-186` prints one line for every round that names the PR and lacks the line, as long as the PR is not CONFIRMED. A PR that already has a proper round (waiting on Andrew's confirm) and one old hand-made round still gets "file a new round with the designed first call". From reading plus the pure function: two rounds, one good, one bad → one warning line.
5. **Wording: "the designed first call" is not a command.** The sentence tells the reader to do something that is not named on the screen. The clerk's own next step is in `landing_commands.py:298-310` (`landing file-confirm <pr>` without `--round`). Printing that would turn the line into an action.

### Could not check
- The listing path end to end against live GitHub (as the PR says). I read it and ran the pure function over it.
- The seven-form table test and the click-runner tests; I read them, I did not run them.
- Whether `list_rounds(limit=500)` (newest first, `store.py:655`) is enough in practice; I confirmed the order and the cap and nothing more.

### One thing it gets right
One constant (`TREE_LINE_PREFIX`) is now the only definition of the text, shared by the matcher, the clerk's own writer (`round_step`) and the warning, and the 14 forms above show the shared definition does what it says. It also says on screen when the round store cannot be read (`landing_commands.py:159-162`, `:188-193`) instead of dropping the line quietly.

---

## PR 773 — `reach open` also lists open pull requests

**Read:** head `46fe8bb037350386957e3995a6b27e807150dfc4`. `src/divineos/core/reach_open_prs.py` (whole), the four lines it adds to `src/divineos/cli/reach_commands.py`, the PR body. Matching exercised with the repo's own `matching_prs` and `format_open_pr_section` against the **real titles and branch names of the 30 newest open drafts** (page one of the list). I did not call `gh`.

### Findings, most serious first

1. **It misses the symptom words people actually type, because nothing is stemmed.** `reach_open_prs.py:23-25` compares whole words, and two shared words are needed (`MIN_SHARED = 2`, `:16`). Reproduced: `hook hangs` and `hooks hanging after tool calls` → no hits (the words are `hook`/`hooks`, `hangs`/`hanging`). `rest and dreaming prompts after compaction` → no hit on #753, whose title has `dream menu` (`dreaming` ≠ `dream`). `sleep cycle crashes`, `ci red on main` and `flaky` can never match anything (a symptom with one content word cannot reach two). The lines that do hit: `the landing clerk does not say why a round did not match` → #772; `reach check misses open pull requests` → #773; `the phase 2 menu never appears after compaction` → #753; `dream menu fails to show` → #753. So it finds a PR when the symptom is worded like the title and not otherwise, which the PR's "cannot see" section says in general and does not show how narrow.
2. **The cap is silent.** `:54` asks for 100 and `:81` then prints `none found among {len(prs)} open PR(s)`. With exactly 100 returned it prints `none found among 100 open PR(s)` (reproduced) with nothing to say that the list was cut. The number reads as the whole room. The header says "Never empty: a failed look says so", and that is true of failures, not of a truncated success. Fix shape: if `len(prs) == 100`, say "first 100 only".
3. **The PR's own list of what it cannot see is wrong about drafts.** The body says "Draft/closed/merged PRs ... are not looked at". `gh pr list --state open` lists drafts. (From reading and from how `gh` behaves; I could not run it here.) In a house where every one of the 30 newest open PRs is a draft (reproduced from the list: 30 of 30), this matters: the section is more useful than the PR says, and a reader who trusts the sentence will not believe a hit on a draft.
4. **Common house words make false hits, and there is no ranking or cap.** `push fails with 403` → #770 ("a note on what fails the first push of a new core module"), a draft about something else, on `fails` + `push`. Output order is the order `gh` returns, and every hit is printed (`:83`), so a symptom of generic words (`audit`, `round`, `landing`) will print a list of PRs. From reading plus the 30-PR run.
5. **Digits are dropped, so numbers in a symptom or title never help.** `re.split(r"[^a-z]+", ...)` (`:24`) means `403`, `v2`, `phase 2` and `sha256` contribute nothing. From reading; `phase 2 menu` matched #753 only through `menu` and `phase`.
6. **Which repository `gh` looks at is not pinned.** `gh_open_prs` (`:44-69`) passes no `--repo`, so it uses whatever the current directory's remote says. From a fork, a worktree with several remotes, or a directory outside the repo, the answer is about another repository or an interactive-prompt failure (reported as the not-a-clean-bill line, which is the right failure). From reading only.

### Could not check
- Live `gh` output (no way to run it here), including the draft behaviour in finding 3.
- Only 30 of the open PRs were read; the "hits" above are against that page, not the whole list.
- The tests (`tests/test_reach_open_prs.py`, 7 tests, and the `test_reach_check.py` run); read, not run.

### One thing it gets right
A failed look is never silent: gh missing, a non-zero exit and a timeout each print `Could not look at open PRs (...): this is not a clean bill.` and exit 0 (`:64`, `:66`, `:68`, `:78`), and an empty result prints a count and not nothing. The matcher is a pure function over data with the network call injected, so the tests can pin it without a network.

---

## PR 753 — auto-cycle phase 2, at the current head

**Read:** head `139f95ce98615d3327ecd88d3705fc73092d9302` on `aria/auto-cycle-phase-2-rest-and-dream-menu`. The diff from the head the first reader used (`9515a24ff`) to now (two commits: `74a609c7`, `139f95ce`): `src/divineos/core/auto_cycle_phase2.py`, `src/divineos/cli/auto_cycle_phase2_commands.py`, `tests/test_auto_cycle_phase2.py`, and the whole of `read_handshake`, `offer_cycle`, `close_cycle`, `compute_falsifier_ratio` and the audit command at that head. Everything below was run against that head with real marker files in an isolated house.

### The six earlier findings

| # | Earlier finding | Now |
|---|---|---|
| 1 | A marker that is valid JSON but no marker reads as "completed" | **Fixed.** `{}`, `{"steps":{}}`, `steps:"oops"` → `None` (`:197-199`). A non-dict step value (`{"x":"oops"}`) returns a result with `any_step_failed=True`, the safe direction. |
| 2 | Ratio cannot go red from skipping, and re-offers count as failures | **Half fixed, and the half that was fixed introduced a worse hole (new finding 1).** The first half (a seat closing every cycle `no-pull-honest` scores 100%: reproduced, 6 of 6 → `(6, 6, 1.0)`) is unchanged; the module docstring still says no-pull-forced counts against it. |
| 3 | Non-numbers raise instead of returning `None` | **Mostly fixed, not fully.** `"abc"`, `null`, `"12.5"`, `NaN` → `None`. A JSON `Infinity` still raises (new finding 2). |
| 4 | `mktime` on a UTC string | **Fixed.** `calendar.timegm` (`:504`); duration just after offering is ≈0.1–0.4 s under UTC, `TZ=Asia/Tokyo` and `TZ=America/Los_Angeles` (all three run). |
| 5 | "used Nx since last cycle" is not since the last cycle | **Not addressed.** The diff does not touch `_use_counts_since_last_cycle` (`:240`). Unverified whether phase 1's sleep step resets the rest session; still from reading. |
| 6 | Path text drift (`~/.divineos/...`) | **Half fixed.** The refusal message and the `offer` docstring now use `marker_path()`. The module docstring still says `~/.divineos/auto_cycle_phase1_done.json` at `auto_cycle_phase2.py:10` and `:44`, and so does `auto_cycle.py:37`. |

### Findings, most serious first

1. **The re-run fix hides exactly the abandoned offerings the ratio exists to count.** `offer_cycle` closes an unanswered pending offering as `SUPERSEDED` (`:400-404`), and `compute_falsifier_ratio` skips those rows (`:591-592`). But the handshake is **consumed** by an offer (`_handshake_marker().unlink()`, `:433`), so a second `offer` is only possible after a *new* phase 1 has written a *new* cycle id — it is never a "re-run of offer" on the same cycle. Reproduced: offer A, offer again with no marker → `None`; write marker B, offer B → A is logged as `superseded`. After one abandoned offering and then six more offers none of which was ever answered, the audit log holds 7 rows, all `superseded`, `compute_falsifier_ratio()` → `(0, 0, None)`, and `divineos auto-cycle audit` prints "No closed cycles yet. Falsifier undefined." (`cli:156`). So a seat that never answers can never fire the alarm; before this commit those were counted against it. The real "an `offer` re-run" case (same cycle id offered twice) cannot happen; a different-cycle-id case is an abandonment. Fix shape: only skip a superseded row when its cycle id equals the new one; count the rest as `timeout`.
2. **`Infinity` in the marker still raises, in the fix that was meant to stop raising.** `read_handshake` catches `(TypeError, ValueError)` (`:205`); `int(float('inf'))` is `OverflowError`. Reproduced: `"phase1_tokens_used": Infinity` and `"budget_remaining_est": -Infinity` (JSON allows these in Python's parser) → `OverflowError: cannot convert float infinity to integer`, which propagates out of `offer_cycle` and the CLI. Same invariant (`None` on a malformed marker), same fix (`OverflowError` in the tuple). The earlier `NaN`, `"abc"`, `null` cases are now correct. Low severity: it fails loud and does not fire.
3. **Booleans pass as numbers.** `float(True)` and `int(True)` succeed, so `"trigger_context_pct": true` and `"phase1_tokens_used": true` are read as `1.0` / `1` and return a good-looking result (reproduced). A hand-written or damaged marker with `true` where a number belongs reads as good. Small; same class as the original finding 1.
4. **`any_step_failed` is the only caution signal, and a marker with real-shaped steps but a `null` cycle id invents one silently.** `cycle_id=null` → `str(None)` = `"None"` is kept as the id (`:233`), so two such markers share the id `"None"` (reproduced: result accepted, `cycle_id` becomes the string). From reading of the id branch (`offer_cycle` falls back to a uuid only when the string is empty). Tiny, and it interacts with finding 1 if the id-equality fix is chosen.

### Could not check
- The six new tests (the diff adds 112 test lines): read, not run, so I cannot say they pass. I did check the behaviours they claim by hand (findings 1, 3, 4 and the table above).
- Whether anything else reads `auto_cycle_audit.jsonl` and trips on the new `superseded` outcome. I grepped `src/` for the filename; only `auto_cycle_phase2.py` reads it. Tests and `docs/` were not searched.
- A real phase 1 → phase 2 run (`auto-cycle fire` would commit, extract and sleep).

### One thing it gets right
The fixes were written with the cause named beside them and a regression test each, and the two that matter most for safety — a marker with no steps is not a completed phase 1, and the UTC duration — now hold under every timezone I tried. It also kept the rule that a machine outcome (`SUPERSEDED`) cannot be given by the CLI: the `_machine` flag is keyword-only and `_FIXED_OUTCOMES` does not list it (`:486`).

---

## Where I found nothing serious

None of the three came back clean. The closest is 772: it agrees with the matcher on every form of the line itself, and its findings are about who gets a warning (1, 2) and what the sentence says (3-5). The most serious in the set is 753 finding 1, because the change that fixed one of the earlier findings turns the falsifier into something that cannot fire from unanswered offerings.
